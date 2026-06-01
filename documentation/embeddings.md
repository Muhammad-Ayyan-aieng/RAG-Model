# Embeddings: Converting Text to Vectors

## What is an Embedding?

An embedding is a numerical representation of text. Words, sentences, or entire documents are converted into lists of numbers (vectors) where similar meanings have similar numbers.

**File responsible:** `src/pipelines/ingestion.py` → `get_embedding_model()`, `_create_embeddings()`

**Embedding model used:** `all-MiniLM-L6-v2` from Sentence Transformers

## Simple Analogy

Think of coordinates on a map:

|   Text   |    Would Map To    |           Why         |
|----------|--------------------|-----------------------|
| "Happy"  | [0.8, 0.1, 0.9]    | Close to "joyful"     |
| "Joyful" | [0.79, 0.12, 0.88] | Very close to "happy" |
| "Car"    | [0.2, 0.9, 0.1]    | Far from "happy"      |

Similar meanings → close together in vector space. Different meanings → far apart.

## Our Embedding Model: all-MiniLM-L6-v2

|     Property     |    Value     |          Why It Matters          |
|------------------|--------------|----------------------------------|
| Model Size       | 90 MB        | Fits in memory                   |
| Output Dimensions| 384          | Rich enough for semantic meaning |
| Speed            | Very Fast    | Real-time queries                |
| Quality          | Good         | 99% accuracy on benchmarks       |
| License          | Apache 2.0   | Free for commercial use          |
| Training Data    | 1B+ sentences| Broad understanding              |

**Name breakdown:**
- `all` - Trained on diverse domains (not specialized)
- `MiniLM` - Small, efficient architecture
- `L6` - 6 transformer layers (lighter than 12-layer models)
- `v2` - Version 2 (improved)

## How Embeddings Are Created

### Behind the Scenes (Simplified)
Input text: "Pets allowed on Fridays"
↓
[Tokenization] → ["Pets", "allowed", "on", "Fridays"]
↓
[Embedding Layer] → Each token → 384 numbers
↓
[6 Transformer Layers] → Process relationships between tokens
Layer 1: Understands "Pets" + "allowed"
Layer 2: Understands "Pets allowed" + "Fridays"
Layers 3-6: Build complete meaning
↓
[Pooling Layer] → Combine tokens → single 384-number vector
↓
Output: [0.12, -0.45, 0.78, 0.23, ..., -0.56]
↑ 384 numbers representing meaning ↑

text

## Why 384 Dimensions?

| Dimensions | Memory per Chunk |            Use Case           |
|------------|------------------|-------------------------------|
| 128        | 0.5 KB           | Very fast, less accurate      |
| 384        | 1.5 KB           | **Our choice - best balance** |
| 768        | 3 KB             | More accurate, slower         |
| 1536       | 6 KB             | Most accurate, expensive      |

384 provides excellent semantic understanding while keeping storage and search fast.

## How Embeddings Enable Semantic Search

### Keyword Search (Traditional)
Query: "Can I bring my dog?"
Document: "Pets permitted every Friday"

Keywords: "dog" vs "pets" → No match 
Result: Search fails

text

### Semantic Search (With Embeddings)
Query: "Can I bring my dog?"
↓
Query Embedding: [0.45, -0.23, 0.89, ...]

Document: "Pets permitted every Friday"
↓
Document Embedding: [0.43, -0.21, 0.91, ...]

Calculate Cosine Similarity: 0.94 (very close!)
Result: Match found 

text

## Cosine Similarity Explained

**What it measures:** The angle between two vectors

| Similarity Score |      Meaning      |
|------------------|-------------------|
| 1.0              | Identical meaning |
| 0.8 - 0.99       | Very similar      |
| 0.5 - 0.79       | Somewhat related  |
| 0.0 - 0.49       | Unrelated         |
| Negative         | Opposite meanings |

**In ChromaDB:** Distance = 1 - Similarity
- Distance 0.0 = Perfect match
- Distance 0.5 = 50% similar
- Distance 1.0 = Completely different

## Loading the Model (First Time)

```python
# This happens once on server startup
model = SentenceTransformer("all-MiniLM-L6-v2")
What happens:

Checks local cache for model files

If not found, downloads from Hugging Face (~90 MB)

Loads model into RAM

Caches for future runs

Timing:

First load: 10-30 seconds (download + load)

Subsequent loads: 3-5 seconds (from cache)

Creating Embeddings for Chunks
python
def _create_embeddings(chunks: list[str]) -> list[list[float]]:
    model = get_embedding_model()  # Singleton - loaded once
    embeddings = model.encode(chunks, show_progress_bar=False)
    return embeddings.tolist()  # Convert numpy array to Python list
Batch processing:

All chunks in a document are embedded together

More efficient than one-by-one

Uses model's batching capability

Storage in ChromaDB
python
collection.add(
    ids=ids,                    # Unique chunk identifiers
    embeddings=embeddings,      # 384 numbers per chunk
    documents=chunks,           # Original text (for retrieval)
    metadatas=metadatas         # Filename, page, timestamp
)
Memory calculation:

Each embedding: 384 numbers × 4 bytes = 1,536 bytes

1,000 chunks = ~1.5 MB for embeddings

With HNSW index overhead: ~3-5 MB total

Embedding Quality Checklist
Factor	Impact
Chunk size	Too small = missing context; too large = diluted meaning
Language	Model works best on English
Domain	General model; specialized domains may need fine-tuning
Noise	Clean text = better embeddings
Scaling Considerations
Scale	Issue	Solution
1M chunks	~1.5 GB embeddings	Still fine
10M chunks	~15 GB embeddings	Needs memory optimization
100M chunks	~150 GB embeddings	Use quantization (int8)
1B chunks	~1.5 TB embeddings	Distributed cluster required
Related Files
File	Function	Purpose
src/pipelines/ingestion.py	get_embedding_model()	Loads the model (singleton)
src/pipelines/ingestion.py	_create_embeddings()	Converts chunks to vectors
src/pipelines/retrieval.py	_search_chromadb()	Embeds user questions
requirements.txt	sentence-transformers	Library dependency
Key Takeaway
Embeddings turn human language into mathematical vectors where:

Similar meaning = close together

Different meaning = far apart

This enables semantic search, allowing "dog" to match "pets" even though the words are different, because their meanings are similar.