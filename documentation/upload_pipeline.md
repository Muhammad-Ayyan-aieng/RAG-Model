# Upload Pipeline: From PDF to Database

## Overview

The upload pipeline converts a user's PDF or TXT file into searchable vector chunks stored in ChromaDB.

**File responsible:** `src/pipelines/ingestion.py`

## Complete Flow Diagram
User uploads file.pdf
│
▼
POST /documents/upload
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 1. AUTHENTICATION & VALIDATION                              │
│ - get_user_role() → admin or public                         │
│ - validate_upload() → check size, type, count               │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TEXT EXTRACTION (file_parser.py)                         │
│ - PDF: PyMuPDF extracts text page by page                   │
│ - TXT: Direct UTF-8/latin-1 decoding                        │
│ - Returns raw string                                        │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TEXT CLEANING (text_cleaner.py)                          │
│ - Remove null bytes                                         │
│ - Normalize whitespace (tabs → spaces)                      │
│ - Fix broken hyphenated lines ("pro-\ncess" → "process")    │
│ - Remove page numbers and decorative lines                  │
│ - Join mid-sentence line breaks                             │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CHUNKING (_split_into_chunks)                            │
│ - CHUNK_SIZE = 500 characters                               │
│ - CHUNK_OVERLAP = 100 characters                            │
│ - Preserve word boundaries (no mid-word cuts)               │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 5. EMBEDDING (_create_embeddings)                           │
│ - all-MiniLM-L6-v2 model                                    │
│ - Each chunk → 384-dimension vector                         │
│ - Returns list of lists: [[0.12, -0.45,...], ...]           │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 6. STORAGE (_store_in_qdrant)                             │
│ - Generate unique IDs: {doc_id}chunk{i}                     │
│ - Store: ids, embeddings, documents, metadatas              │
│ - Metadata includes: filename, chunk_index, timestamp,      │
│ document_id, content_hash                                   │
└─────────────────────────────────────────────────────────────┘
│
▼
Response: {document_id, filename, chunks_created}

text

## Detailed Step-by-Step

### Step 1: Authentication & Validation

**File:** `src/api/documents.py` → `upload_document()`

```python
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    files: list[UploadFile] = File(...),
    role: str = Depends(get_user_role)  # ← Auth first
):
    validate_upload(files, role)  # ← Check limits
What is validated:

Check	                      Admin              	Public
File size    	            Unlimited	           Max 5MB
File count per upload    	Unlimited	         Max 3 files
File type	                   Any	            Only PDF, TXT

Step 2: Text Extraction
File: src/utils/file_parser.py → extract_text()

python
def clean_text(text: str) -> str:
    text = _remove_null_bytes(text)      # Remove \x00
    text = _normalize_whitespace(text)   # tabs→spaces, collapse spaces
    text = _remove_repeated_special_chars(text)  # Remove ---- lines
    text = _fix_broken_lines(text)       # Fix hyphenated and mid-sentence breaks
    text = _remove_headers_footers(text) # Remove page numbers
    return text.strip()
Critical Cleaning Examples:

Before	After
"Hello\x00World"	"HelloWorld"
"This is a sen-\ntence"	"This is a sentence"
"Line one\nline two"	"Line one line two" (if mid-sentence)
"----\nPage 5\n===="	(removed)
Step 4: Chunking
File: src/pipelines/ingestion.py → _split_into_chunks()

python
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

Why 500/100?

Parameter           	Value	                         Reason
Chunk Size	        500 chars	         Fits well in LLM context windows (~125 words)
Overlap         	100 chars	         Preserves context across boundaries (20% overlap)

Visual Example:                  
text
Document: [==================================================]
Chunk 1:   [========500========]
Chunk 2:         [========500========]  (100 chars overlap)
Chunk 3:               [========500========]
Word Boundary Protection:

text
Without protection:           With protection:
"Photosynthesis is the proc"  "Photosynthesis is the"
"ess by which plants..."      "process by which plants..."
Step 5: Creating Embeddings
File: src/pipelines/ingestion.py → _create_embeddings()

What is an Embedding?

An embedding is a numerical representation of text. The model all-MiniLM-L6-v2 converts each chunk into 384 numbers:

text
Chunk: "Pets are allowed on Fridays"
         ↓
Embedding: [0.12, -0.45, 0.78, 0.23, ..., -0.56]
           ↑ 384 numbers ↑
Similar chunks have similar vectors:

text
"Pets allowed Fridays" → [0.12, -0.45, 0.78, ...]
"Dogs welcome Fridays" → [0.11, -0.44, 0.79, ...]  (very close)
"Office hours 9-5"    → [0.89, 0.23, -0.12, ...]  (far away)
Step 6: Storing in ChromaDB
File: src/pipelines/ingestion.py → _store_in_chromadb()

What Gets Stored:

Field	Example	Purpose
ids	"abc123_chunk_0"	Unique identifier
embeddings	[0.12, -0.45, ...]	Vector for similarity search
documents	"Pets allowed on Fridays"	Original text to return
metadatas.filename	"HR_Policy.pdf"	Source file name
metadatas.chunk_index	3	Position in document
metadatas.document_id	"abc123"	Group chunks by document
metadatas.uploaded_at	"2026-01-15 10:30:00"	Timestamp
metadatas.content_hash	"a3f5c9..."	Detect duplicates
API Response Example
Successful Upload:

json
{
    "message": "Document uploaded successfully",
    "filename": "HR_Policy.pdf",
    "chunks_created": 12,
    "document_id": "3f7a9b2c-1d4e-4f6a-8b3c-9e2f1a4d5c6b"
}
Duplicate File:

json
{
    "detail": "Document 'HR_Policy.pdf' already exists. Delete it first."
}
 
Error Handling :
Error	                           Cause	                 Response
File has no extension	    Filename without dot	        400 Bad Request
File type .xyz not allowed	Unsupported format	            400 Bad Request
Document appears empty	   PDF has no extractable text   	400 Bad Request
Document already exists 	Same filename uploaded before	409 Conflict
GROQ_API_KEY not set	   Missing environment variable  	500 Internal Error
Next Steps
After upload completes, documents are ready for querying. See:

semantic-search.md - How we find relevant chunks

llm-generation.md - How we generate answers