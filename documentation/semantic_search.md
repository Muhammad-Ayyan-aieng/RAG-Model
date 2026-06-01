# Semantic Search: Finding Relevant Chunks

## What is Semantic Search?

Semantic search finds documents based on **meaning** rather than exact keywords. It understands that "dog" and "pets" are related concepts, even though the words are different.

**File responsible:** `src/pipelines/retrieval.py` → `_search_chromadb()`, `_filter_by_relevance()`

## Semantic Search vs Keyword Search

|   Feature   |   Keyword Search   |           Semantic Search            |
|-------------|--------------------|--------------------------------------|
| Method      | Exact word matching| Meaning matching                     |
| Query "dog" | Finds only "dog"   | Finds "dog", "puppy", "canine", "pet"|
| Misspellings| Fails              | Works (similar vectors)              |
| Synonyms    | Misses             | Catches automatically                |
| Language    | Exact only         | Understands context                  |

## The Search Flow
User Question: "What is the pet policy?"
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 1. EMBED THE QUESTION                                       │
│ model.encode(["What is the pet policy?"])                   │
│ → Vector: [0.12, -0.45, 0.78, ...] (384 numbers)            │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CHROMADB QUERY                                           │
│ collection.query(query_embeddings=[question_vector])        │
│ → Returns top_k most similar chunks                         │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DISTANCE FILTERING                                       │
│ Keep only chunks with distance ≤ 0.7                        │
│ → Remove irrelevant matches                                 │
└─────────────────────────────────────────────────────────────┘
│
▼
Return relevant chunks to LLM

text

## Step 1: Embedding the Question

**File:** `src/pipelines/retrieval.py` → `_search_chromadb()`

```python
# Get embedding model (same one used for documents)
model = get_embedding_model()

# Convert question to vector
question_embedding = model.encode([question]).tolist()[0]
Why the same model?

Documents and questions must be in the same vector space

Only then can we compare distances meaningfully

If models differ, comparisons are meaningless

Step 2: ChromaDB Query
python
results = collection.query(
    query_embeddings=[question_embedding],
    n_results=top_k,  # How many results to return
    include=["documents", "metadatas", "distances"]
)
Query Parameters
Parameter	Value	Purpose
query_embeddings	List of vectors	What to search for
n_results	3-10	How many results to fetch
include	documents, metadatas, distances	What data to return
Understanding the Results
python
{
    "documents": [["Chunk 1", "Chunk 2", "Chunk 3"]],
    "metadatas": [[{"filename": "policy.pdf"}, {...}, {...}]],
    "distances": [[0.12, 0.34, 0.56]]
}
Field	           Meaning	          Lower is Better
distances	How far from question	 Yes (0 = identical)
Step 3: Distance Filtering
File: src/pipelines/retrieval.py → _filter_by_relevance()

python
def _filter_by_relevance(
    chunks: list[str],
    metadatas: list[dict],
    distances: list[float],
    threshold: float = 0.7  # ← Critical safety parameter
) -> tuple[list[str], list[dict]]:
    
    filtered_chunks = []
    filtered_metadatas = []
    
    for chunk, metadata, distance in zip(chunks, metadatas, distances):
        if distance <= threshold:  # Only keep relevant chunks
            filtered_chunks.append(chunk)
            filtered_metadatas.append(metadata)
    
    return filtered_chunks, filtered_metadatas
Why a Threshold?
Scenario	           Without Threshold	                 With Threshold (0.7)
Question        matches document Returns chunks	              Returns chunks 
Question     doesn't match Forces irrelevant chunks	         Returns empty list 
LLM hallucination	High risk        Low risk (refuses to answer)
Distance          Interpretation
Distance	         Meaning            	Action
0.0 - 0.3	      Highly relevant	         Keep
0.3 - 0.5	         Relevant	             Keep
0.5 - 0.7	     Somewhat relevant	         Keep
0.7 - 0.9	      Loosely related	        Reject
0.9 - 2.0	        Unrelated	            Reject
Step 4: No Results Found
When all chunks are filtered out:

python
if not chunks:
    return {
        "question": question,
        "answer": "I could not find relevant information in the uploaded documents.",
        "sources": [],
        "model_used": "none"
    }
This prevents hallucination. The LLM never sees irrelevant context.

The top_k Parameter
Users can specify how many chunks to retrieve:

python
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3  # Default to 3
top_k Value	Effect	When to Use
1	Very focused, may miss context	Short answers
3	Default - best balance	Most queries
5	More context, more tokens	Complex questions
10	Maximum context, expensive	Long documents
Real Search Example
Document contains:

text
Chunk 1: "Pets are allowed on Fridays only"
Chunk 2: "Dogs must remain leashed at all times"
Chunk 3: "Office hours are 9 AM to 5 PM"
Question: "What is the pet policy?"

Results with distances:

Chunk  Distance	 Kept?
Chunk 1	0.12	 Yes
Chunk 2	0.34	 Yes
Chunk 3	0.89     No
Final answer uses only Chunks 1 and 2.

Performance Optimization
At Small Scale (<100K chunks)
Direct query is fine

No special optimization needed

At Large Scale (>1M chunks)
Use HNSW indexes (ChromaDB does this automatically)

Consider pre-filtering by metadata

Implement caching for frequent queries

Use approximate nearest neighbors (ANN)

At Billion Scale
Partition by document type or date

Use separate collections per category

Implement two-stage retrieval (keyword + vector)

GPU acceleration for similarity search

Adjusting the Threshold
Threshold	Recall	Precision	Use Case
0.5	Lower	Higher	High-stakes answers
0.7	Balanced	Balanced	Default - most use cases
0.9	Higher	Lower	Exploratory search
Our choice (0.7): Balances finding relevant content while avoiding hallucinations.

Related Files
File	Function	Purpose
src/pipelines/retrieval.py	_search_chromadb()	Main search function
src/pipelines/retrieval.py	_filter_by_relevance()	Distance filtering
src/pipelines/retrieval.py	retrieve_and_answer()	Orchestrates search + generation
src/models/schemas.py	QueryRequest	Defines top_k parameter
Key Takeaway
Semantic search finds meaning, not just keywords. Our three-step process:

Embed the question into vector space

Query ChromaDB for similar chunks

Filter by distance threshold to prevent hallucinations

The 0.7 threshold is critical safety: if no chunk is sufficiently relevant, the system says "I cannot find this information" rather than hallucinating.