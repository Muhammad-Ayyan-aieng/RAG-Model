# Vector Database: Qdrant Cloud

## What is Qdrant?

Qdrant is an open-source vector database written in **Rust**, designed for production-scale AI applications. Unlike ChromaDB (embedded), Qdrant uses a **client-server architecture** with persistent cloud storage.

**File responsible:** `src/database/vector_client.py`

## Why a Vector Database?

| Operation | Regular Database (SQL) | Vector Database (Qdrant) |
|-----------|------------------------|---------------------------|
| Find "pets" | Exact word match only | Semantic meaning match |
| Find similar | Requires pre-defined categories | Finds by vector proximity |
| Scale | Linear scan | HNSW indexing for sub-linear search |
| Data type | Strings, numbers | Vectors (arrays of floats) |

## Why We Switched from ChromaDB to Qdrant

| Issue | ChromaDB (Old) | Qdrant Cloud (New) |
|-------|----------------|-------------------|
| Architecture | Embedded library | Client-server |
| Data persistence on HF free tier | ❌ Lost on restart | ✅ Persistent |
| Free tier model | Credit-based ($5 credits) | Free forever (1GB RAM, 4GB storage) |
| Production readiness | Prototyping | Enterprise-grade |

## Qdrant Architecture
┌─────────────────────────────────────────────────────────────┐
│ YOUR APPLICATION │
│ (src/main.py) │
└─────────────────────────────┬───────────────────────────────┘
│
│ client.upsert()
│ client.query_points()
▼
┌─────────────────────────────────────────────────────────────┐
│ QDRANT CLOUD │
│ (Remote Server) │
│ │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Collection │ │ HNSW │ │ Payload │ │
│ │ documents │ │ Index │ │ Store │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────┘

text

## How We Initialize Qdrant

**File:** `src/database/vector_client.py` → `init_vector_client()`

```python
def init_vector_client() -> None:
    global _client
    
    _client = QdrantClient(
        url=settings.QDRANT_URL,      # Cloud endpoint
        api_key=settings.QDRANT_API_KEY,
    )
    
    _client.create_collection(
        collection_name="documents",
        vectors_config=VectorParams(
            size=384,                  # Embedding dimension
            distance=Distance.COSINE   # Similarity metric
        )
    )
    
    # Create index for fast deletion
    _client.create_payload_index(
        collection_name="documents",
        field_name="document_id",
        field_type="keyword"
    )
Key Decisions
Setting	Value	Why
Client Type	QdrantClient (cloud)	Data persists in cloud, survives restarts
Collection Name	"documents"	All chunks stored together
Distance Metric	cosine	Best for semantic similarity
Vector Size	384	Matches all-MiniLM-L6-v2 output
Index Field	document_id	Enables fast document deletion
Understanding the Collection
A collection is like a table in SQL. Our documents collection stores:

Field	Type	Example	Purpose
id	string (UUID)	"f79a31fb-8432-..."	Unique point identifier
vector	list[float]	[0.12, -0.45, ...]	384 numbers for search
payload.text	string	"Pets allowed Fridays"	Original text
payload.filename	string	"policy.pdf"	Source file
payload.document_id	string (UUID)	"abc123"	Groups chunks by document
payload.chunk_index	int	3	Position in document
HNSW Indexing Explained
HNSW = Hierarchical Navigable Small World

This is the algorithm Qdrant uses for fast similarity search.

How It Works (Simplified)
text
Layer 3 (top):    ●─────●              (few nodes, long jumps)
                     │
Layer 2:          ●──●──●──●           (more nodes, medium jumps)
                   │  │  │
Layer 1:    ●─────●──●──●──●─────●      (most nodes, short jumps)
Search process:

Start at top layer (few nodes)

Find closest node, move to next layer

Refine search at each layer

Return nearest neighbors

Performance:

Search time: O(log N) instead of O(N)

Build time: O(N log N)

Memory: ~2-3x raw data size

CRUD Operations
CREATE (Add embeddings)
File: src/pipelines/ingestion.py → _store_in_qdrant()

python
from qdrant_client.models import PointStruct

points = []
for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    point = PointStruct(
        id=str(uuid.uuid4()),          # Unique UUID per chunk
        vector=embedding,
        payload={
            "document_id": document_id,
            "filename": filename,
            "chunk_index": i,
            "text": chunk,
            "uploaded_at": uploaded_at,
            "content_hash": content_hash
        }
    )
    points.append(point)

client.upsert(collection_name="documents", points=points)
READ (Search/Query)
File: src/pipelines/retrieval.py → _search_qdrant()

python
result = client.query_points(
    collection_name="documents",
    query=question_embedding,    # Vector to search for
    limit=top_k,                 # Number of results
    with_payload=True            # Return the text
)

results_list = result.points
Response structure:

python
[
    Point(
        id="f79a31fb-8432-...",
        score=0.88,
        payload={
            "text": "Chunk text",
            "filename": "doc.pdf",
            "chunk_index": 0
        }
    ),
    ...
]
READ (List all documents)
File: src/api/documents.py → list_documents()

python
# Scroll through all points (max 10,000 at a time)
result = client.scroll(
    collection_name="documents",
    limit=10000,
    with_payload=True
)
points = result[0]  # List of points
DELETE
File: src/api/documents.py → delete_document()

python
# Find all points with this document_id
search_result = client.scroll(
    collection_name="documents",
    scroll_filter={
        "must": [{"key": "document_id", "match": {"value": document_id}}]
    },
    limit=10000
)

point_ids = [point.id for point in search_result[0]]
client.delete(collection_name="documents", points_selector=point_ids)
Distance Metrics in Qdrant
Metric	Formula	Best For	Our Choice
cosine	1 - similarity	Text embeddings	✅ Yes
euclidean	Euclidean distance	Image embeddings	No
dot	Dot product	Normalized vectors	No
Why cosine for text:

Measures angle, not magnitude

Ignores vector length (longer text = longer vector)

Focuses on meaning, not document length

Payload Filtering
Qdrant supports filtering by payload fields during queries:

python
# Search only within specific document
result = client.query_points(
    collection_name="documents",
    query=question_embedding,
    query_filter={
        "must": [{"key": "filename", "match": {"value": "policy.pdf"}}]
    }
)
Free Tier Specifications (Qdrant Cloud)
Resource	Limit
RAM	1 GB
Storage	4 GB
vCPU	0.5
Vectors	~1-2 million (384 dims)
Cost	Free forever
Credit card	Not required
Data Persistence on Hugging Face
Issue solved: Qdrant Cloud is external to Hugging Face. Your data lives in Qdrant's cloud, not on Hugging Face's ephemeral disk.

Result: Data survives Space restarts, rebuilds, and even Space deletion.

Performance Characteristics (Qdrant Cloud)
Operation	Time Complexity	Real-World (40 chunks)
Add chunk (upsert)	O(log N)	~50-100ms
Query (k=3)	O(log N)	~100-200ms
Scroll (list all)	O(N)	~50ms
Delete by filter	O(N)	~100ms
Scaling Limits (Qdrant)
Scale	Feasibility	Changes Needed
10,000 points	✅ Easy	None
100,000 points	✅ Fine	None
1,000,000 points	✅ Possible	Upgrade Qdrant Cloud tier
10,000,000 points	✅ Possible	Larger cluster
1,000,000,000 points	✅ Possible	Distributed cluster
Related Files
File	Function	Purpose
src/database/vector_client.py	init_vector_client()	Initialize Qdrant connection
src/database/vector_client.py	get_vector_client()	Access client singleton
src/pipelines/ingestion.py	_store_in_qdrant()	Add embeddings to Qdrant
src/pipelines/retrieval.py	_search_qdrant()	Query embeddings from Qdrant
src/api/documents.py	list_documents()	List all documents
src/api/documents.py	delete_document()	Delete document by ID
Key Takeaway
Qdrant Cloud provides:

✅ Persistent storage (no data loss on Space restarts)

✅ Fast similarity search via HNSW indexing

✅ Payload filtering for precise queries

✅ Free forever tier (1GB RAM, 4GB storage)

✅ Production-ready architecture (client-server)

For billion-scale, we would:

Upgrade to larger Qdrant Cloud tier

Implement sharding by document type

Add read replicas for search queries

Use multiple collections for different document categories