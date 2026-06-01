# Vector Database: ChromaDB Deep Dive

## What is ChromaDB?

ChromaDB is an open-source vector database designed specifically for AI applications. It stores embeddings (vectors) and enables fast similarity search.

**File responsible:** `src/database/chroma_client.py`

## Why a Vector Database?

|  Operation  |      Regular Database (SQL)     |     Vector Database (ChromaDB)     |
|-------------|---------------------------------|------------------------------------|
| Find "pets" | Exact word match only           | Semantic meaning match             |
| Find similar| Requires pre-defined categories | Finds by vector proximity          |
| Scale       | Linear scan                     | HNSW indexing for sub-linear search|
| Data type   | Strings, numbers                | Vectors (arrays of floats)         |

## ChromaDB Architecture
┌─────────────────────────────────────────────────────────────┐
│ YOUR APPLICATION                                            │
│ (src/main.py)                                               │
└─────────────────────────────┬───────────────────────────────┘
│
│ collection.add()
│ collection.query()
▼
┌─────────────────────────────────────────────────────────────┐
│ CHROMADB CLIENT                                             │
│ (chroma_client.py)                                          │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ Persistent  │ │ HNSW        │ │ Metadata    │             │
│ │ Client      │ │ Index       │ │ Store       │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ DISK STORAGE                                                │
│ ./chroma_data/                                              │
│                                                             │
│ ├── chroma.sqlite3 (Metadata & collection info)             │
│ ├── index/ (HNSW index files)                               │
│ └── embeddings/ (Vector data)                               │
└─────────────────────────────────────────────────────────────┘

text

## How We Initialize ChromaDB

**File:** `src/database/chroma_client.py` → `init_chroma()`

```python
def init_chroma() -> None:
    global _client, _collection
    
    _client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH  # "./chroma_data"
    )
    
    _collection = _client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,  # "documents"
        metadata={"hnsw:space": "cosine"}  # Distance metric
    )
Key Decisions
Setting	Value	Why
Client Type	PersistentClient	Data saved to disk, survives restarts
Collection Name	"documents"	All chunks stored together
Distance Metric	cosine	Best for semantic similarity
Telemetry	disabled	Prevents memory deadlocks on low-RAM
Understanding the Collection
A collection is like a table in SQL. Our documents collection stores:

Field	Type	Example	Purpose
ids	string	"abc123_chunk_0"	Unique identifier
embeddings	list[float]	[0.12, -0.45, ...]	384 numbers for search
documents	string	"Pets allowed Fridays"	Original text
metadatas	dict	{"filename": "policy.pdf"}	Source information
HNSW Indexing Explained
HNSW = Hierarchical Navigable Small World

This is the algorithm ChromaDB uses for fast similarity search.

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
File: src/pipelines/ingestion.py → _store_in_chromadb()

python
collection.add(
    ids=["abc123_chunk_0", "abc123_chunk_1"],
    embeddings=[[0.12, -0.45, ...], [0.33, 0.21, ...]],
    documents=["Chunk 1 text", "Chunk 2 text"],
    metadatas=[{"filename": "doc.pdf"}, {"filename": "doc.pdf"}]
)
READ (Search/Query)
File: src/pipelines/retrieval.py → _search_chromadb()

python
results = collection.query(
    query_embeddings=[[0.12, -0.45, ...]],  # Question embedding
    n_results=3,                             # Top 3 matches
    include=["documents", "metadatas", "distances"]
)
Response structure:

python
{
    "documents": [["chunk1", "chunk2", "chunk3"]],
    "metadatas": [[{...}, {...}, {...}]],
    "distances": [[0.12, 0.34, 0.56]]
}
UPDATE (Get by metadata)
File: src/api/documents.py → list_documents()

python
# Get all chunks for a specific document
results = collection.get(
    where={"document_id": "abc123"},
    include=["metadatas"]
)
DELETE
File: src/api/documents.py → delete_document()

python
# Delete all chunks for a document
collection.delete(
    where={"document_id": "abc123"}
)
Distance Metrics in ChromaDB
Metric	Formula	Best For	Our Choice
cosine	1 - similarity	Text embeddings	✅ Yes
l2	Euclidean distance	Image embeddings	No
ip	Inner product	Normalized vectors	No
Why cosine for text:

Measures angle, not magnitude

Ignores vector length (longer text = longer vector)

Focuses on meaning, not document length

Metadata Filtering
ChromaDB supports filtering by metadata during queries:

python
# Search only within specific document
results = collection.query(
    query_embeddings=[question_embedding],
    where={"filename": "policy.pdf"}  # Filter
)

# Complex filters
results = collection.query(
    query_embeddings=[question_embedding],
    where={
        "$and": [
            {"filename": {"$in": ["policy.pdf", "rules.pdf"]}},
            {"chunk_index": {"$gte": 0}}
        ]
    }
)
Persistent Storage Modes
  Mode	        Location	               Data Persistence	           Use Case
Persistent	   ./chroma_data/	          Survives restarts	          Production
Ephemeral	    Memory only	               Lost on restart	           Testing
HttpClient	    Remote server	          Depends on server	          Distributed

We use Persistent mode (embedded). For billion-scale, we would switch to HttpClient mode with a ChromaDB cluster.

Data Persistence on Hugging Face
Issue: On Hugging Face free tier, ./chroma_data/ is on ephemeral disk.

Solutions:

Solution	           Complexity	    Cost	                 Persistence
Accept ephemeral	      Low	        Free	                     No
Paid persistent storage	  Low	       $5/month	                     Yes
Backup to Dataset	      Medium	    Free	                     Yes
External ChromaDB	      High	        Free tier available	         Yes
Performance Characteristics
Operation	Time Complexity	Real-World (10K chunks)
Add chunk	O(log N)	~10ms
Query (k=3)	O(log N)	~20ms
Get by ID	O(1)	~5ms
Delete by filter	O(N)	~50ms
Count	O(1)	~1ms
Scaling Limits
Scale	           Feasibility	        Changes               Needed
10,000               chunks	              Easy	               None
100,000              chunks	              Fine	               None
1,000,000            chunks	            Possible	    More RAM, sharding
10,000,000           chunks	              Hard	        Distributed cluster
1,000,000,000        chunks	          Not possible	  Need specialized solution
Related Files
File	                            Function	              Purpose
src/database/chroma_client.py	  init_chroma()	             Initialize connection
src/database/chroma_client.py	  get_collection()	         Access collection
src/pipelines/ingestion.py	      _store_in_chromadb()	     Add embeddings
src/pipelines/retrieval.py	      _search_chromadb()	     Query embeddings
src/api/documents.py	          list_documents()	         Get by metadata
src/api/documents.py	          delete_document()	         Delete by filter
Key Takeaway
ChromaDB provides:

Fast similarity search via HNSW indexing

Metadata filtering for precise queries

Persistent storage (when configured correctly)

Simple API for CRUD operations

For billion-scale, we would:

Switch to HttpClient mode

Deploy ChromaDB cluster

Implement sharding by document type

Add read replicas for search queries