A production-ready RAG (Retrieval-Augmented Generation) system that answers questions based on your uploaded documents.

## Tech Stack

- **Backend:** FastAPI, Qdrant Cloud (vector database), Sentence Transformers
- **LLM:** Groq (llama-3.3-70b-versatile) - Free tier
- **Frontend:** HTML/CSS/JS
- **Deployment:** Hugging Face Spaces (Docker)
- **Database Persistence:** Qdrant Cloud (free tier, persistent storage)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/muhammad-ayyan-aieng/rag-model.git
cd rag-model
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add GROQ_API_KEY, ADMIN_PASSWORD, QDRANT_URL, QDRANT_API_KEY to .env

# Run
python -m src.main
Open http://localhost:8000

Environment Variables
Variable	Required	Purpose
GROQ_API_KEY	Yes	Groq LLM API
ADMIN_PASSWORD	Yes	Admin panel access
QDRANT_URL	Yes	Qdrant Cloud cluster URL
QDRANT_API_KEY	Yes	Qdrant Cloud API key
API Endpoints
Method	Endpoint	Description	Auth
POST	/documents/upload	Upload PDF/TXT	Public (limited)
GET	/documents/	List documents	Admin only
DELETE	/documents/{id}	Delete document	Admin only
POST	/query/ask	Ask question	Public
GET	/health	Health check	Public
Deployment
Built with Docker, deployed to Hugging Face Spaces:

Port: 7860 (required by HF)

Add secrets: GROQ_API_KEY, ADMIN_PASSWORD, QDRANT_URL, QDRANT_API_KEY

Data Persistence
Unlike ChromaDB (which loses data on Space restarts), Qdrant Cloud runs externally. Your uploaded documents and embeddings remain safe even if your Hugging Face Space restarts.

Documentation
Complete technical docs in /documentation/ folder:

Architecture overview

Chunking strategy (500 chars, 100 overlap)

Embeddings (all-MiniLM-L6-v2, 384 dims)

Semantic search with distance threshold (0.7)

Qdrant Cloud vector database

Production scaling for billion documents

Live Demo
https://muhammad-ayyan-aieng-rag-model.hf.space

License
MIT