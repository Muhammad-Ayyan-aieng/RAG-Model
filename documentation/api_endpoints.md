# API Endpoints: Complete Reference

## Overview

The RAG Assistant provides five REST API endpoints organized into three routers.

**File responsible:** `src/api/` (health.py, documents.py, query.py)

## Complete Endpoint List

| Method |         Endpoint         |      Description     |          Authentication        |
|--------|--------------------------|----------------------|--------------------------------|
| GET    | `/health`                | Service health check | None                           |
| POST   | `/documents/upload`      | Upload a document    | Admin/Public (different limits)|
| GET    | `/documents/`            | List all documents   | Admin only                     |
| DELETE |`/documents/{document_id}`| Delete a document    | Admin only                     |
| POST   | `/query/ask`             | Ask a question       | None                           |     

---

## Endpoint 1: Health Check

**Method:** GET
**Endpoint:** `/health`
**Authentication:** None

### Purpose
- Verify service is running
- Check ChromaDB connectivity
- Report database statistics

### Response (200 OK)

|      Field     |   Type  |     Description     |    Example    |
|----------------|---------|---------------------|---------------|
| status         | string  | Service health      | "healthy"     |
| environment    | string  | dev/production      | "development" |
| chromadb       | string  | Connection status   | "connected"   |
| total_documents| integer | Number of documents | 5             |
| total_chunks   | integer | Total vector chunks | 47            |

### When to Use
- Deployment health checks
- Monitoring dashboard
- Debugging connectivity

---

## Endpoint 2: Upload Document

**Method:** POST
**Endpoint:** `/documents/upload`
**Authentication:** Admin/Public (role detected via header)

### Request

|    Parameter    | Type  | Required |          Description           |
|-----------------|-------|----------|--------------------------------|
| files           | file  | Yes      | PDF or TXT file (one at a time)|
| x-admin-password| header| No       | Required for admin privileges  |

### Role-Based Limits

|      Limit       |   Admin   |    Public    |
|------------------|-----------|--------------|
| File size        | Unlimited | 5 MB         |
| File type        | Any       | PDF, TXT only|
| Files per upload | 1         | 1            |
| Rate limit       | None      | Configurable |

### Success Response (200 OK)

|      Field       |  Type  |        Description        |
|------------------|--------|---------------------------|
| message          | string | Success confirmation      |
| filename         | string | Original file name        |
| chunks_created   | integer| Number of chunks generated|
| document_id      | string | Unique identifier (UUID)  |

### Error Responses

| Status |      Error     |                    Description                      |
|--------|----------------|-----------------------------------------------------|
| 400    | Bad Request    | Invalid file type, empty document, or size exceeded |
| 401    | Unauthorized   | Invalid admin password                              |
| 409    | Conflict       | Document with same filename already exists          |
| 500    | Internal Error | Processing failed                                   |

### File Processing Steps
1. Validate file extension and size
2. Extract text (PyMuPDF for PDF, UTF-8 for TXT)
3. Clean text (remove noise, fix line breaks)
4. Split into chunks (500 chars, 100 overlap)
5. Generate embeddings (384-dim vectors)
6. Store in ChromaDB with metadata
7. Return document ID and chunk count

---

## Endpoint 3: List Documents

**Method:** GET
**Endpoint:** `/documents/`
**Authentication:** Admin only

### Request Header

|      Header      | Required |        Description       |
|------------------|----------|--------------------------|
| x-admin-password | Yes      | Admin password from .env |

### Success Response (200 OK)

|   Field   | Type    |        Description       |
|-----------|---------|--------------------------|
| total     | integer | Number of documents      |
| documents | array   | List of document objects |

### Document Object Fields

|    Field    |  Type   |          Description             |
|-------------|---------|----------------------------------|
| document_id | string  | Unique identifier (UUID)         |
| filename    | string  | Original file name               |
| chunks_count| integer | Number of chunks in document     |
| uploaded_at | string  | Timestamp (YYYY-MM-DD HH:MM:SS)  |

### Error Responses

| Status |     Error     |           Description             |
|--------|---------------|-----------------------------------|
| 401    | Unauthorized  | Missing or invalid admin password |
| 403    | Forbidden     | Non-admin trying to access        |
| 500    | Internal Error| Failed to retrieve data           |

### Usage
- Admin panel document management
- Debugging and monitoring
- Preparing for deletion

---

## Endpoint 4: Delete Document

**Method:** DELETE
**Endpoint:** `/documents/{document_id}`
**Authentication:** Admin only

### Path Parameter

|  Parameter  |  Type  |             Description               |
|-------------|--------|---------------------------------------|
| document_id | string | Unique identifier returned from upload|

### Request Header

|      Header      | Required |        Description       |
|------------------|----------|--------------------------|
| x-admin-password | Yes      | Admin password from .env |

### Success Response (200 OK)

|    Field    |  Type  |          Description            |
|-------------|--------|---------------------------------|
| message     | string | "Document deleted successfully" |
| document_id | string | ID of deleted document          |

### Error Responses

| Status |     Error      |           Description            |
|--------|----------------|----------------------------------|
| 401    | Unauthorized   | Missing or invalid admin password|
| 403    | Forbidden      | Non-admin trying to delete       |
| 404    | Not Found      | Document ID does not exist       |
| 500    | Internal Error | Deletion failed                  |

### What Gets Deleted
- All chunks belonging to the document
- Associated embeddings
- Metadata references

The original uploaded file is NOT stored, so only ChromaDB entries are removed.

---

## Endpoint 5: Ask Question

**Method:** POST
**Endpoint:** `/query/ask`
**Authentication:** None (public access)

### Request Body

|  Field   |  Type   | Required | Default |            Description             |
|----------|---------|----------|---------|------------------------------------|
| question | string  | Yes      | -       | User's question (3-1000 chars)     |
| top_k    | integer | No       | 3       | Number of chunks to retrieve (1-10)|

### Validation Rules
- Question cannot be empty
- Question minimum length: 3 characters
- Question maximum length: 1000 characters
- top_k range: 1 to 10

### Success Response (200 OK)

|    Field   |  Type  |        Description        |
|------------|--------|---------------------------|
| question   | string | Original user question    |
| answer     | string | Generated answer from LLM |
| sources    | array  | Source chunks used        |
| model_used | string | LLM model name            |

### Source Object Fields

|    Field    |  Type  |          Description          |
|-------------|--------|-------------------------------|
| filename    | string | Source document name          |
| chunk_index | integer| Position in document          |
| text_preview| string | First 200 characters of chunk |

### Response Examples

**When answer found:**
```json
{
  "question": "What is the pet policy?",
  "answer": "Pets are allowed on Fridays only, and dogs must remain leashed.",
  "sources": [
    {"filename": "HR_Policy.pdf", "chunk_index": 3, "text_preview": "Pets are allowed on Fridays..."}
  ],
  "model_used": "llama-3.3-70b-versatile"
}
When no relevant context:

json
{
  "question": "What is the coffee policy?",
  "answer": "I could not find relevant information in the uploaded documents.",
  "sources": [],
  "model_used": "none"
}
Error Responses
Status	Error	Description
400	Bad Request	Invalid question format or empty
422	Unprocessable	Validation failed (question too short/long)
500	Internal Error	LLM or database failure
503	Service Unavailable	Groq API unavailable
Processing Flow
Validate question format and length

Convert question to embedding (same model as documents)

Search ChromaDB for similar chunks

Filter results by distance threshold (≤ 0.7)

If no chunks remain, return "not found"

Send chunks + question to Groq LLM

Return answer with source citations

Authentication Header
Header name: x-admin-password

Behavior
Scenario	Result
No header + public endpoint	Access granted as public user
No header + admin-only endpoint	401 Unauthorized
Wrong password	401 Unauthorized
Correct password	Access granted as admin
Where Required
Endpoint	Header Required
POST /documents/upload	No (but affects limits)
GET /documents/	Yes
DELETE /documents/{id}	Yes
POST /query/ask	No
GET /health	No
Rate Limiting (Public Users)
Limit	Value	Applied To
Max file size	5 MB	Upload endpoint
Max files per upload	1	Upload endpoint
Allowed extensions	PDF, TXT	Upload endpoint
Request rate	Configurable	All endpoints
Admin users bypass all limits.

Base URL
Local development: http://localhost:8000

Production (Hugging Face): https://muhammad-ayyan-aieng-rag-model.hf.space

All endpoints are relative to the base URL.

OpenAPI Documentation
FastAPI auto-generates interactive documentation at:

text
http://localhost:8000/docs
This provides:

List of all endpoints

Request/response schemas

Try-it-out functionality

Authentication testing

Related Files
File	Endpoints Defined
src/api/health.py	GET /health
src/api/documents.py	POST /upload, GET /, DELETE /{id}
src/api/query.py	POST /ask
src/core/auth.py	Authentication logic
src/core/limiter.py	Rate limiting
Key Takeaway
The API is organized with:

Clear separation of concerns (health, documents, query)

Role-based access (admin vs public with different permissions)

Consistent error responses (proper HTTP status codes)

Validation at multiple layers (Pydantic schemas, custom validators)

Auto-generated documentation (OpenAPI/Swagger UI)