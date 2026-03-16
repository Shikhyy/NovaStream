"""Agent 4: Editor — Stitches video clips with audio using FFmpeg."""

from __future__ import annotations

import asyncio
import json
import os
import logging
from pathlib import Path

import httpx
from dotenv import load_dotenv

from models import EpisodeJob, EpisodeStatus

load_dotenv()
logger = logging.getLogger("novastream.editor")

WORK_DIR = Path("/tmp/novastream/work")
OUTPUT_DIR = Path("/tmp/novastream/episodes")
S3_BUCKET = os.getenv("S3_BUCKET", "novastream-episodes")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "")
SUPABASE_PATH_PREFIX = os.getenv("SUPABASE_PATH_PREFIX", "episodes")


async def _download_video(url: str, dest: Path) -> bool:
    """Download a video file from URL."""
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code == 200:
                    with open(dest, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                    return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
    return False


async def _run_ffmpeg(args: list[str], broadcast_log, label: str = "") -> bool:
    """Run an FFmpeg command and return success status."""
    cmd = ["ffmpeg", "-y"] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_msg = stderr.decode()[-200:] if stderr else "Unknown error"
        await broadcast_log("EDITOR", "error", f"FFmpeg {label} failed: {error_msg}")
        return False
    return True


async def run_editor(job: EpisodeJob, broadcast_log) -> EpisodeJob:
    """Stitch video clips with audio voiceovers into a final episode MP4."""
    job.status = EpisodeStatus.EDITING
    await broadcast_log("EDITOR", "info", "Starting video assembly...")

    if not job.blueprint or not job.scene_assets:
        await broadcast_log("EDITOR", "error", "Missing blueprint or scene assets")
        job.error_log.append("Editor: missing data")
        job.status = EpisodeStatus.FAILED
        return job

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    episode_dir = WORK_DIR / job.episode_id
    episode_dir.mkdir(exist_ok=True)

    muxed_scenes = []

    for i, scene in enumerate(job.blueprint.scenes):
        scene_num = scene.scene_number
        await broadcast_log("EDITOR", "info", f"Processing scene {scene_num}/{len(job.blueprint.scenes)}...")

        # Get video source
        asset = next((a for a in job.scene_assets if a.scene_number == scene_num), None)
        video_path = episode_dir / f"clip_{scene_num}.mp4"

        if asset and asset.video_url:
            downloaded = await _download_video(asset.video_url, video_path)
            if not downloaded:
                await broadcast_log("EDITOR", "warn", f"Scene {scene_num}: download failed, generating color bar")
                await _generate_placeholder_video(video_path, scene.duration_seconds)
        else:
            await broadcast_log("EDITOR", "warn", f"Scene {scene_num}: no video URL, generating placeholder")
            await _generate_placeholder_video(video_path, scene.duration_seconds)

        if not video_path.exists():
            await broadcast_log("EDITOR", "error", f"Scene {scene_num}: clip file missing, skipping scene")
            continue

        # Re-encode clip to ensure consistent codec and trim to duration
        normalized_path = episode_dir / f"norm_{scene_num}.mp4"
        norm_ok = await _run_ffmpeg([
            "-i", str(video_path),
            "-t", str(scene.duration_seconds),
            "-vf", "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r", "24",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-an",  # strip original audio
            str(normalized_path),
        ], broadcast_log, f"normalize scene {scene_num}")

        if not norm_ok or not normalized_path.exists():
            await broadcast_log("EDITOR", "error", f"Scene {scene_num}: normalize failed, skipping scene")
            continue

        # Mux with voiceover audio
        audio_path = job.audio_files[i] if i < len(job.audio_files) else None
        muxed_path = episode_dir / f"muxed_{scene_num}.mp4"

        if audio_path and Path(audio_path).exists():
            success = await _run_ffmpeg([
                "-i", str(normalized_path),
                "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac",
                "-shortest",
                str(muxed_path),
            ], broadcast_log, f"mux scene {scene_num}")
            if success:
                muxed_scenes.append(muxed_path)
            else:
                muxed_scenes.append(normalized_path)
        else:
            muxed_scenes.append(normalized_path)

    # Filter to only scenes that were successfully assembled
    valid_scenes = [p for p in muxed_scenes if p.exists()]

    # Concatenate all scenes
    filelist_path = episode_dir / "filelist.txt"

    if not valid_scenes:
        await broadcast_log("EDITOR", "error", "No valid scenes assembled, cannot create episode")
        job.status = EpisodeStatus.FAILED
        job.error_log.append("Editor: no valid scenes")
        return job

    filelist_path.write_text("\n".join(f"file '{p}'" for p in valid_scenes))

    final_path = OUTPUT_DIR / f"episode_{job.episode_id}.mp4"

    await broadcast_log("EDITOR", "info", "Concatenating scenes into final episode...")
    success = await _run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(filelist_path),
        "-c", "copy",
        str(final_path),
    ], broadcast_log, "concat")

    if not success:
        # Retry with re-encode
        await broadcast_log("EDITOR", "warn", "Concat copy failed, re-encoding...")
        success = await _run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", str(filelist_path),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_path),
        ], broadcast_log, "concat re-encode")

    if success and final_path.exists():
        # Clean up old episode files to prevent disk fill (keep last 5)
        try:
            episode_files = sorted(OUTPUT_DIR.glob("episode_*.mp4"), key=lambda p: p.stat().st_mtime)
            for old_file in episode_files[:-5]:
                old_file.unlink(missing_ok=True)
        except Exception:
            pass

        # Upload to remote storage if configured
        video_url = await _upload_to_remote_storage(final_path, job.episode_id, broadcast_log)
        if video_url:
            job.video_url = video_url
        else:
            # Serve locally
            job.video_url = f"/episodes/episode_{job.episode_id}.mp4"

        await broadcast_log("EDITOR", "success", f"Episode assembled: {final_path.name} ({final_path.stat().st_size / 1024 / 1024:.1f}MB)")
    else:
        job.status = EpisodeStatus.FAILED
        job.error_log.append("Editor: final concat failed")
        await broadcast_log("EDITOR", "error", "Failed to assemble final episode")

    # Clean up work directory
    try:
        import shutil
        shutil.rmtree(episode_dir, ignore_errors=True)
    except Exception:
        pass

    return job


async def _generate_placeholder_video(path: Path, duration: int) -> None:
    """Generate a placeholder video with a solid color background."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x0D1117:size=854x480:rate=24:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(f"Placeholder video generation failed: {stderr.decode()[-200:]}")


async def _upload_to_remote_storage(file_path: Path, episode_id: str, broadcast_log) -> str:
    """Upload to Supabase first, then S3. Return a public URL on success."""
    # Prefer Supabase when configured
    supabase_url = await _upload_to_supabase(file_path, episode_id, broadcast_log)
    if supabase_url:
        return supabase_url

    # Fallback to S3 when configured
    return await _upload_to_s3(file_path, episode_id, broadcast_log)


async def _upload_to_supabase(file_path: Path, episode_id: str, broadcast_log) -> str:
    """Upload episode to Supabase Storage and return public URL."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not SUPABASE_BUCKET:
        return ""

    object_key = f"{SUPABASE_PATH_PREFIX}/episode_{episode_id}.mp4".strip("/")
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_key}"
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{object_key}"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "video/mp4",
        "x-upsert": "true",
    }

    try:
        file_size = file_path.stat().st_size
        upload_timeout = max(60, file_size // 100_000)  # Scale timeout with file size
        async with httpx.AsyncClient(timeout=upload_timeout) as client:
            file_bytes = file_path.read_bytes()
            resp = await client.post(upload_url, headers=headers, content=file_bytes)

        if resp.status_code in (200, 201):
            await broadcast_log("EDITOR", "success", f"Uploaded to Supabase: {object_key}")
            return public_url

        await broadcast_log("EDITOR", "warn", f"Supabase upload failed ({resp.status_code}): {resp.text[:120]}")
        return ""
    except Exception as e:
        await broadcast_log("EDITOR", "warn", f"Supabase upload failed: {e}")
        return ""


async def _upload_to_s3(file_path: Path, episode_id: str, broadcast_log) -> str:
    """Upload episode to S3 and return CloudFront URL."""
    if not S3_BUCKET or S3_BUCKET == "novastream-episodes":
        return ""

    try:
        import boto3
        s3 = boto3.client("s3")
        key = f"episodes/episode_{episode_id}.mp4"
        s3.upload_file(
            str(file_path), S3_BUCKET, key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        if CLOUDFRONT_DOMAIN:
            url = f"https://{CLOUDFRONT_DOMAIN}/{key}"
        else:
            url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
        await broadcast_log("EDITOR", "success", f"Uploaded to S3: {key}")
        return url
    except Exception as e:
        await broadcast_log("EDITOR", "warn", f"S3 upload failed: {e}")
        return ""
