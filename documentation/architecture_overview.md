# RAG Assistant: Architecture Overview

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that combines:
1. **Retrieval**: Finding relevant documents from a database
2. **Augmentation**: Injecting those documents into a prompt
3. **Generation**: Having an LLM answer based ONLY on those documents

## Why RAG?

|             Problem              |                RAG Solution               |
|----------------------------------|-------------------------------------------|
| LLMs don't know your private data| Retrieve documents first                  |
| LLMs hallucinate                 | Force answers from retrieved context      |
| Retraining is expensive          | No fine-tuning needed, just add documents |
| Keyword search misses meaning    | Semantic search finds meaning             |

## High-Level Flow
User Uploads Document
│
▼
Extract Text
│
▼
Split into Chunks (500 chars, 100 overlap)
│
▼
Convert to Embeddings (all-MiniLM-L6-v2)
│
▼
Store in ChromaDB (Vector Database)
│
▼
User Asks Question
│
▼
Convert Question to Embedding
│
▼
Search ChromaDB (Semantic Similarity)
│
▼
Filter by Threshold (distance ≤ 0.7)
│
▼
Build Prompt with Retrieved Context
│
▼
Send to LLM (Groq - llama-3.3-70b)
│
▼
Return Answer with Sources

text

## Component Responsibilities

|         Component       |                Responsibility                  |                   Key Files                  |
|-------------------------|------------------------------------------------|----------------------------------------------|
| **Frontend**            | User interface for uploads & questions         | `frontend/index.html`, `frontend/admin.html` |
| **API Layer**           | Handle HTTP requests, authentication           | `src/api/*.py`                               |
| **Auth Layer**          | Admin/Public role separation                   | `src/core/auth.py`, `src/core/limiter.py`    |
| **Ingestion Pipeline**  | Process documents → chunks → embeddings → store| `src/pipelines/ingestion.py`                 |
| **Retrieval Pipeline**  | Search → filter → answer                       | `src/pipelines/retrieval.py`                 |
| **Vector DB**           | Store and search embeddings                    | `src/database/chroma_client.py`              |
| **LLM Factory**         | Generate answers via API                       | `src/models/llm_factory.py`                  | 
| **Config**              | Environment & settings management              | `src/config.py`                              |

## Technology Stack

|       Layer      |                 Technology               |          Purpose          |
|------------------|------------------------------------------|---------------------------|
| Backend Framework| FastAPI                                  | API endpoints, routing    |
| Vector Database  | ChromaDB                                 | Embedding storage & search|
| Embeddings       | Sentence Transformers (all-MiniLM-L6-v2) | Convert text to vectors   |
| LLM              | Groq (llama-3.3-70b-versatile)           | Answer generation         |
| Frontend         | HTML/CSS/JS                              | User interface            |
| Deployment       | Hugging Face Spaces                      | Container hosting         |
| Containerization | Docker                                   | Consistent environment    |

## File Structure
rag-assistant/
├── src/
│ ├── api/ # REST endpoints
│ │ ├── health.py # Health check
│ │ ├── documents.py # Upload, list, delete
│ │ └── query.py # Question answering
│ ├── core/ # Business logic
│ │ ├── auth.py # Role-based access
│ │ └── limiter.py # Upload limits
│ ├── database/ # ChromaDB client
│ │ └── chroma_client.py
│ ├── models/ # Data schemas & LLM
│ │ ├── schemas.py # Pydantic models
│ │ └── llm_factory.py
│ ├── pipelines/ # RAG core logic
│ │ ├── ingestion.py # Document processing
│ │ └── retrieval.py # Search & answer
│ ├── utils/ # Helpers
│ │ ├── file_parser.py
│ │ ├── text_cleaner.py
│ │ └── logger.py
│ ├── config.py # Settings
│ └── main.py # FastAPI entry
├── frontend/
│ ├── index.html # Public chat
│ └── admin.html # Admin panel
├── Dockerfile # Container build
├── requirements.txt # Python dependencies
└── README.md # Project overview

text

## Data Flow: Upload
User selects file → POST /documents/upload

Auth checks role (admin/public)

Limiter validates file size/type

extract_text() reads PDF/TXT

clean_text() removes noise

_split_into_chunks() creates 500-char chunks with 100 overlap

_create_embeddings() converts chunks to vectors

_store_in_chromadb() saves vectors + metadata

Response returns document_id + chunk count

text

## Data Flow: Query
User types question → POST /query/ask

QueryRequest validates input (non-empty, 3-1000 chars)

retrieve_and_answer() orchestrates:
a. _search_chromadb() gets question embedding
b. ChromaDB semantic search returns top_k chunks
c. _filter_by_relevance() keeps only distance ≤ 0.7
d. generate_answer() sends to LLM with context
e. _build_sources() creates citations

Response returns answer + sources