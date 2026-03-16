"""Agent 3: Voice Actor — Generates voiceover audio using Nova 2 Sonic bidirectional streaming."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import uuid
import logging
from pathlib import Path

from dotenv import load_dotenv

from models import EpisodeJob, EpisodeStatus

load_dotenv()
logger = logging.getLogger("novastream.voice")

NOVA_SONIC_MODEL_ID = os.getenv("NOVA_SONIC_MODEL_ID", "us.amazon.nova-2-sonic-v1:0")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
OUTPUT_DIR = Path("/tmp/novastream/audio")

# Voice persona mapping by tone
VOICE_CONFIG = {
    "documentary": {"voiceId": "Matthew", "style": "neutral, authoritative, calm news anchor"},
    "satirical": {"voiceId": "Ruth", "style": "dry, deadpan, subtly amused"},
    "dramatic": {"voiceId": "Matthew", "style": "heightened gravitas, urgent, cinematic"},
}


async def _generate_speech_with_sonic(
    text: str, voice_id: str, style_prompt: str, output_path: Path, broadcast_log
) -> bool:
    """Generate speech audio from text using Nova 2 Sonic's bidirectional streaming API.

    Nova 2 Sonic uses InvokeModelWithBidirectionalStream — we send text input
    (cross-modal) and collect audio output chunks.
    """
    try:
        from aws_sdk_bedrock_runtime.client import (
            BedrockRuntimeClient,
            InvokeModelWithBidirectionalStreamOperationInput,
        )
        from aws_sdk_bedrock_runtime.models import (
            InvokeModelWithBidirectionalStreamInputChunk,
            BidirectionalInputPayloadPart,
        )
        from aws_sdk_bedrock_runtime.config import Config
        from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver
    except ImportError:
        await broadcast_log("VOICE", "error",
            "aws_sdk_bedrock_runtime not installed. Run: pip install aws-sdk-bedrock-runtime")
        return False

    config = Config(
        endpoint_uri=f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com",
        region=AWS_REGION,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
    )
    client = BedrockRuntimeClient(config=config)

    prompt_name = str(uuid.uuid4())
    system_content_name = str(uuid.uuid4())
    text_content_name = str(uuid.uuid4())

    async def send_event(stream, event_json: str):
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
        )
        await stream.input_stream.send(event)

    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=NOVA_SONIC_MODEL_ID)
    )

    audio_chunks: list[bytes] = []
    done_event = asyncio.Event()

    async def collect_audio():
        """Read output events and collect audio chunks."""
        try:
            while True:
                output = await stream.await_output()
                result = await output[1].receive()
                if result.value and result.value.bytes_:
                    data = json.loads(result.value.bytes_.decode("utf-8"))
                    event = data.get("event", {})

                    if "audioOutput" in event:
                        audio_b64 = event["audioOutput"]["content"]
                        audio_chunks.append(base64.b64decode(audio_b64))
                    elif "contentEnd" in event:
                        role = event["contentEnd"].get("role", "")
                        if role == "ASSISTANT":
                            pass  # assistant content block ended
                    elif "promptEnd" in event or "sessionEnd" in event:
                        done_event.set()
                        return
        except Exception as e:
            logger.error(f"collect_audio error: {e}")
            done_event.set()

    reader_task = asyncio.create_task(collect_audio())

    # 1. Session start
    await send_event(stream, json.dumps({
        "event": {
            "sessionStart": {
                "inferenceConfiguration": {
                    "maxTokens": 1024,
                    "topP": 0.9,
                    "temperature": 0.7,
                }
            }
        }
    }))

    # 2. Prompt start with audio output config
    await send_event(stream, json.dumps({
        "event": {
            "promptStart": {
                "promptName": prompt_name,
                "textOutputConfiguration": {"mediaType": "text/plain"},
                "audioOutputConfiguration": {
                    "mediaType": "audio/lpcm",
                    "sampleRateHertz": 24000,
                    "sampleSizeBits": 16,
                    "channelCount": 1,
                    "voiceId": voice_id,
                    "encoding": "base64",
                    "audioType": "SPEECH",
                },
            }
        }
    }))

    # 3. System prompt
    await send_event(stream, json.dumps({
        "event": {
            "contentStart": {
                "promptName": prompt_name,
                "contentName": system_content_name,
                "type": "TEXT",
                "interactive": False,
                "role": "SYSTEM",
                "textInputConfiguration": {"mediaType": "text/plain"},
            }
        }
    }))

    system_prompt = (
        f"You are a professional news narrator. Read the following text aloud with a {style_prompt} delivery. "
        "Speak naturally and clearly. Do not add any commentary — just read the text exactly as given."
    )
    await send_event(stream, json.dumps({
        "event": {
            "textInput": {
                "promptName": prompt_name,
                "contentName": system_content_name,
                "content": system_prompt,
            }
        }
    }))

    await send_event(stream, json.dumps({
        "event": {
            "contentEnd": {
                "promptName": prompt_name,
                "contentName": system_content_name,
            }
        }
    }))

    # 4. User text input (cross-modal: text in → audio out)
    await send_event(stream, json.dumps({
        "event": {
            "contentStart": {
                "promptName": prompt_name,
                "contentName": text_content_name,
                "type": "TEXT",
                "interactive": True,
                "role": "USER",
                "textInputConfiguration": {"mediaType": "text/plain"},
            }
        }
    }))

    await send_event(stream, json.dumps({
        "event": {
            "textInput": {
                "promptName": prompt_name,
                "contentName": text_content_name,
                "content": text,
            }
        }
    }))

    await send_event(stream, json.dumps({
        "event": {
            "contentEnd": {
                "promptName": prompt_name,
                "contentName": text_content_name,
            }
        }
    }))

    # 5. End prompt and session
    await send_event(stream, json.dumps({
        "event": {"promptEnd": {"promptName": prompt_name}}
    }))

    await send_event(stream, json.dumps({
        "event": {"sessionEnd": {}}
    }))

    await stream.input_stream.close()

    # Wait for audio collection to complete
    try:
        await asyncio.wait_for(done_event.wait(), timeout=30)
    except asyncio.TimeoutError:
        pass

    reader_task.cancel()
    try:
        await reader_task
    except (asyncio.CancelledError, Exception):
        pass

    if audio_chunks:
        # Write raw PCM audio, then convert to MP3 with FFmpeg
        raw_path = output_path.with_suffix(".pcm")
        raw_path.write_bytes(b"".join(audio_chunks))
        audio_chunks.clear()  # Free memory immediately

        # Convert raw PCM (24kHz, 16-bit, mono) to MP3
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "s16le", "-ar", "24000", "-ac", "1",
            "-i", str(raw_path),
            "-c:a", "libmp3lame", "-q:a", "5",
            str(output_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        raw_path.unlink(missing_ok=True)
        return output_path.exists()

    return False


async def run_voice(job: EpisodeJob, broadcast_log) -> EpisodeJob:
    """Generate voiceover MP3 files for each scene using Nova 2 Sonic."""
    job.status = EpisodeStatus.VOICING
    await broadcast_log("VOICE", "info", "Starting voiceover generation with Nova 2 Sonic...")

    if not job.blueprint:
        await broadcast_log("VOICE", "error", "No blueprint available")
        job.error_log.append("Voice: no blueprint")
        return job

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = []
    tone = job.blueprint.tone
    voice_cfg = VOICE_CONFIG.get(tone, VOICE_CONFIG["documentary"])

    for scene in job.blueprint.scenes:
        output_path = OUTPUT_DIR / f"{job.episode_id}_scene_{scene.scene_number}.mp3"
        try:
            start_time = time.time()
            await broadcast_log(
                "VOICE", "info",
                f"Scene {scene.scene_number}: invoking Nova 2 Sonic ({len(scene.voiceover_script.split())} words, voice={voice_cfg['voiceId']})"
            )

            success = await _generate_speech_with_sonic(
                text=scene.voiceover_script,
                voice_id=voice_cfg["voiceId"],
                style_prompt=voice_cfg["style"],
                output_path=output_path,
                broadcast_log=broadcast_log,
            )

            ttfb = (time.time() - start_time) * 1000

            if success and output_path.exists():
                audio_files.append(str(output_path))
                await broadcast_log(
                    "VOICE", "success",
                    f"Scene {scene.scene_number}: audio generated ({ttfb:.0f}ms, {output_path.stat().st_size / 1024:.1f}KB)"
                )
            else:
                await broadcast_log("VOICE", "warn", f"Scene {scene.scene_number}: Sonic returned no audio, using silent placeholder")
                silent_path = await _create_silent_audio(output_path, scene.duration_seconds)
                audio_files.append(str(silent_path))
                job.error_log.append(f"Voice scene {scene.scene_number}: no audio returned")

        except Exception as e:
            await broadcast_log("VOICE", "warn", f"Scene {scene.scene_number} TTS failed: {e}")
            silent_path = await _create_silent_audio(output_path, scene.duration_seconds)
            audio_files.append(str(silent_path))
            job.error_log.append(f"Voice scene {scene.scene_number}: {e}")

    job.audio_files = audio_files
    await broadcast_log("VOICE", "success", f"All {len(audio_files)} voiceovers complete")
    return job


async def _create_silent_audio(path: Path, duration: int) -> Path:
    """Create a silent MP3 placeholder using FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"anullsrc=channel_layout=mono:sample_rate=24000",
        "-t", str(duration), "-c:a", "libmp3lame", "-q:a", "9",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()
    return path
