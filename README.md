# NovaStream 24/7 — The Infinite Broadcast

Fully autonomous AI-powered television network. Without any human intervention, it continuously monitors the internet for trending news headlines, transforms them into short-form video episodes with cinematic structure, voiceover narration, and music — then broadcasts them live via a web player.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    NovaStream Pipeline                     │
│                                                           │
│  Headlines ──► Showrunner ──► Casting + Voice ──► Editor  │
│   (RSS/API)   (Nova 2 Lite)  (Embeddings) (Sonic) (FFmpeg)│
│                                                           │
│  ──► Broadcaster ──► WebSocket ──► Next.js Frontend       │
│       (FastAPI)       (Real-time)   (Live Player)         │
└──────────────────────────────────────────────────────────┘
```

### Agent Pipeline

| Agent | Role | Nova Model |
|-------|------|------------|
| **Showrunner** | Generates production blueprint JSON from headline | Nova 2 Lite |
| **Casting Director** | Matches scenes to stock video via embedding similarity | Nova Multimodal Embeddings |
| **Voice Actor** | Synthesizes voiceover narration per scene | Nova 2 Sonic |
| **Editor** | Stitches video + audio into final episode via FFmpeg | — |

## Tech Stack

- **Backend**: Python, FastAPI, asyncio, boto3
- **Frontend**: Next.js 14, Tailwind CSS, WebSocket
- **AI Models**: Amazon Nova 2 Lite, Nova Multimodal Embeddings, Nova 2 Sonic (via Bedrock)
- **Video**: FFmpeg, Pexels API (CC0 stock footage)
- **Deployment**: Docker, AWS EC2, S3, CloudFront

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- FFmpeg 6.0+
- AWS credentials with Bedrock access
- Pexels API key (free at pexels.com)

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Docker (Alternative)

```bash
docker-compose up --build
```

Open http://localhost:3000 to view the broadcast.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_DEFAULT_REGION` | AWS region (default: us-east-1) |
| `PEXELS_API_KEY` | Pexels stock video API key |
| `NEWSAPI_KEY` | NewsAPI key (optional, has RSS fallback) |
| `S3_BUCKET` | S3 bucket for episode storage |
| `CLOUDFRONT_DOMAIN` | CloudFront distribution domain |

## Project Structure

```
novastream/
├── backend/
│   ├── main.py              # FastAPI app + WebSocket server
│   ├── pipeline.py          # Master loop + agent orchestration
│   ├── agents/
│   │   ├── showrunner.py    # Agent 1: Nova 2 Lite blueprint gen
│   │   ├── casting.py       # Agent 2: Nova Embeddings + Pexels
│   │   ├── voice.py         # Agent 3: Nova 2 Sonic TTS
│   │   └── editor.py        # Agent 4: FFmpeg stitch + upload
│   ├── models.py            # Pydantic schemas
│   ├── news.py              # RSS/NewsAPI headline fetcher
│   └── broadcaster.py       # WebSocket push + S3 upload
├── frontend/                # Next.js 14 app
│   ├── src/app/page.tsx     # Main broadcast page
│   ├── src/components/      # UI components
│   └── src/hooks/           # WebSocket hook
└── docker-compose.yml
```

## Prize Categories

- **Primary**: Agentic AI — Multi-agent orchestration with visible state transitions
- **Secondary**: Multimodal Understanding — Nova Embeddings for scene-to-video semantic matching

## License

Built for Amazon Nova AI Hackathon — March 2026.
