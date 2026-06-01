# Project Setup Guide

## Prerequisites

Before you start, ensure you have:

|      Requirement     | Version |           Check Command           |
|----------------------|---------|-----------------------------------|
| Python               | 3.11+   | `python --version`                |
| Git                  | Latest  | `git --version`                   |
| Docker (optional)    | Latest  | `docker --version`                |
| Hugging Face Account | -       | [Sign up](https://huggingface.co) |

## Step 1: Clone the Repository

```bash
git clone https://github.com/muhammad-ayyan-aieng/rag-model.git
cd rag-model
Step 2: Create Virtual Environment
Windows
bash
python -m venv venv
venv\Scripts\activate
Mac/Linux
bash
python -m venv venv
source venv/bin/activate
Step 3: Install Dependencies
bash
pip install -r requirements.txt
What Each Dependency Does
Package	Version	Purpose
fastapi	0.111.0	Web framework for API
uvicorn	0.29.0	ASGI server to run FastAPI
python-multipart	0.0.9	Handle file uploads
chromadb	0.5.0	Vector database
sentence-transformers	2.7.0	Generate embeddings
groq	0.11.0	Call Groq LLM API
pymupdf	1.24.5	Extract text from PDFs
python-dotenv	1.0.1	Load environment variables
pydantic	2.7.1	Data validation
pydantic-settings	2.2.1	Settings management
numpy	1.26.4	Numerical operations
Step 4: Environment Variables
Create a .env file in the project root:

env
# Groq API (Required)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Admin Authentication (Required)
ADMIN_PASSWORD=your_secure_password

# ChromaDB (Optional - has defaults)
CHROMA_PATH=./chroma_data
CHROMA_COLLECTION_NAME=documents

# Public Limits (Optional - has defaults)
PUBLIC_MAX_FILE_SIZE_MB=5
PUBLIC_MAX_FILES_COUNT=3
PUBLIC_ALLOWED_EXTENSIONS=pdf,txt

# App Settings (Optional - has defaults)
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
Getting Your Groq API Key
Go to console.groq.com

Sign up for free (no credit card required)

Navigate to API Keys

Click Create API Key

Copy the key (starts with gsk_)

Free Tier Limits:

1,000 requests per day

12,000 tokens per minute

Supports llama-3.3-70b-versatile, llama-3.1-8b-instant, etc.

Step 5: Verify Installation
Run this test script to ensure everything works:

python
# test_setup.py
from src.config import settings
from src.database.chroma_client import init_chroma
from src.pipelines.ingestion import get_embedding_model

print(f"✓ Config loaded: GROQ_MODEL={settings.GROQ_MODEL}")
print(f"✓ Admin password set: {'Yes' if settings.ADMIN_PASSWORD else 'No'}")

init_chroma()
print("✓ ChromaDB initialized")

model = get_embedding_model()
print("✓ Embedding model loaded")

print("✅ All systems ready!")
Run it:

bash
python test_setup.py
Expected output:

text
✓ Config loaded: GROQ_MODEL=llama-3.3-70b-versatile
✓ Admin password set: Yes
ChromaDB ready — collection: 'documents'
✓ ChromaDB initialized
Loading embedding model — this takes a moment on first run
Embedding model loaded successfully
✓ Embedding model loaded
   All systems ready!
Step 6: Run the Application
bash
python -m src.main
Or with auto-reload:

bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
Access the app:

Frontend: http://localhost:8000

Admin Panel: http://localhost:8000/admin.html

API Docs: http://localhost:8000/docs

Common Setup Issues
Issue: ModuleNotFoundError: No module named 'src'
Solution: Run from project root directory, not inside src/

Issue: GROQ_API_KEY is not set
Solution: Create .env file with your actual API key

Issue: Port 8000 already in use
Solution: Change port in .env:

text
APP_PORT=8001
Issue: Sentence transformers download slow
Solution: First download takes ~90MB. Be patient or use a download manager. 