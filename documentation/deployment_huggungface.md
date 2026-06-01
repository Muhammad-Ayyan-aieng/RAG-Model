# Deployment: Hugging Face Spaces

## Overview

The application is containerized with Docker and deployed to Hugging Face Spaces.

## Prerequisites

|      Requirement      |                 Check                   |
|-----------------------|-----------------------------------------|
| Hugging Face account  | [huggingface.co](https://huggingface.co)|
| Git installed         | `git --version`                         |
| Docker (local testing)| `docker --version`                      |

## Deployment Files

|       File        |              Purpose                   |
|-------------------|----------------------------------------|
| `Dockerfile`      | Defines container build                |
| `requirements.txt`| Python dependencies                    |
| `README.md`       | Space configuration (YAML front matter)|
| `src/`            | Backend code                           |
| `frontend/`       | HTML files                             |

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
Create Space: huggingface.co/new-space → Select "Docker" SDK

Clone Space locally:

bash
git clone https://huggingface.co/spaces/your-username/space-name
Copy code into cloned directory

Push to Hugging Face:

bash
git add .
git commit -m "Initial deployment"
git push
Add secrets in Space Settings → Repository secrets:

GROQ_API_KEY

ADMIN_PASSWORD

Environment Variables (Secrets)
Variable	Required	Where to Get
GROQ_API_KEY	Yes	console.groq.com
ADMIN_PASSWORD	Yes	Your chosen password
Important Limitations
Feature	Free Tier	Paid Tier
RAM	16 GB	More available
Storage	50 GB (ephemeral)	Persistent available
Data persistence	❌ Lost on restart	✅ Survives restarts
Cost	Free	Starts at $5/month
Data persistence warning: On free tier, all uploaded documents and ChromaDB data are deleted when the Space restarts.

Troubleshooting
Issue	Solution
Port error	Ensure Dockerfile uses port 7860
Missing API keys	Add secrets in Settings
Build fails	Check requirements.txt syntax
App won't start	View logs in Build & Deploy section
Related Files
File	Purpose in Deployment
Dockerfile	Container definition
requirements.txt	Dependencies
README.md	Space configuration
.env	Not committed (secrets managed separately)