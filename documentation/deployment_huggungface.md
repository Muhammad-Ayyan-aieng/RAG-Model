# Deployment: Hugging Face Spaces

## Overview

The application is containerized with Docker and deployed to Hugging Face Spaces. The vector database (Qdrant Cloud) runs externally, so your data persists across Space restarts.

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Hugging Face account | [huggingface.co](https://huggingface.co) |
| Qdrant Cloud account | [qdrant.tech](https://qdrant.tech) |
| Groq API account | [console.groq.com](https://console.groq.com) |
| Git installed | `git --version` |
| Docker (local testing) | `docker --version` |

## Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Defines container build |
| `requirements.txt` | Python dependencies |
| `README.md` | Space configuration (YAML front matter) |
| `src/` | Backend code |
| `frontend/` | HTML files |

## Dockerfile Essentials

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
COPY frontend/ ./frontend/
EXPOSE 7860
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
Critical: Hugging Face requires port 7860, not 8000.

README.md Configuration
The top of README.md must contain:

yaml
---
title: RAG Assistant
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---
Deployment Steps
1. Create Space
Go to huggingface.co/new-space → Select "Docker" SDK

2. Clone Space Locally
bash
git clone https://huggingface.co/spaces/your-username/space-name
3. Copy Code into Cloned Directory
Copy your entire project (src/, frontend/, requirements.txt, Dockerfile, README.md)

4. Push to Hugging Face
bash
git add .
git commit -m "Initial deployment"
git push
5. Add Secrets in Space Settings
Go to your Space → Settings → Repository secrets

Required Secrets
Secret	Required	Where to Get
GROQ_API_KEY	Yes	console.groq.com
ADMIN_PASSWORD	Yes	Your chosen password
QDRANT_URL	Yes	Qdrant Cloud dashboard (cluster URL)
QDRANT_API_KEY	Yes	Qdrant Cloud dashboard (API key)
Environment Variables (Optional)
Variable	Default	Purpose
QDRANT_COLLECTION_NAME	documents	Collection name in Qdrant
QDRANT_VECTOR_SIZE	384	Embedding dimension
APP_ENV	development	Set to production for deployment
Important: Data Persistence
Feature	Free Tier	Paid Tier
RAM	16 GB	More available
Storage (Space)	50 GB (ephemeral)	Persistent available
Qdrant Cloud Data	✅ Persistent	✅ Persistent
Cost	Free	Starts at $5/month
Key difference from ChromaDB: With Qdrant Cloud, your vector database runs externally. Even if your Space restarts, your uploaded documents and embeddings remain safe in Qdrant's cloud.

Architecture After Migration
text
┌─────────────────────────────────────────────────────────────┐
│                  HUGGING FACE SPACE                         │
│                  (Stateless - Code Only)                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  FastAPI    │  │  Frontend   │  │  Embedding  │         │
│  │  Backend    │  │  (HTML/CSS) │  │  Model      │         │
│  └──────┬──────┘  └─────────────┘  └─────────────┘         │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ HTTPS
          ▼
┌─────────────────────────────────────────────────────────────┐
│                     QDRANT CLOUD                            │
│                    (Stateful - Persistent)                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Collection: documents                              │   │
│  │  - All embeddings (384 dims)                        │   │
│  │  - All document chunks (text)                       │   │
│  │  - Metadata (filename, document_id, chunk_index)    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
Troubleshooting
Issue	Solution
Port error	Ensure Dockerfile uses port 7860
Missing API keys	Add all secrets in Settings
Qdrant connection failed	Check QDRANT_URL and QDRANT_API_KEY
Build fails	Check requirements.txt syntax
App won't start	View logs in Build & Deploy section
Data lost after restart	Normal with ChromaDB; fixed with Qdrant Cloud
Related Files
File	Purpose in Deployment
Dockerfile	Container definition
requirements.txt	Dependencies (qdrant-client, not chromadb)
README.md	Space configuration
.env	Not committed (secrets managed separately in HF)
src/database/vector_client.py	Qdrant Cloud connection
Key Takeaway
With Qdrant Cloud, your data is persistent:

✅ Uploaded documents survive Space restarts

✅ Embeddings never get deleted unexpectedly

✅ Free tier with no credit card required

✅ Production-ready architecture (separate database from app)