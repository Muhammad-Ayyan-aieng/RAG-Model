# Chunking Strategy: Why 500 Characters with 100 Overlap

## What is Chunking?

Chunking is the process of splitting a large document into smaller, manageable pieces before converting them to embeddings and storing them in the vector database.

**File responsible:** `src/pipelines/ingestion.py` → `_split_into_chunks()`

## Why We Need Chunking

|      Problem      |           Without Chunking             |         With Chunking           |
|-------------------|----------------------------------------|---------------------------------|
| LLM context limits| Cannot send entire book to LLM         | Send only relevant pages        |
| Embedding quality | Long documents produce diluted vectors | Each chunk represents one idea  |
| Search precision  | Query matches entire document          | Query matches specific paragraph|
| Cost              | Processing giant documents is expensive| Process only what's needed      |

## Our Chunking Parameters

```python
CHUNK_SIZE = 500      # Characters per chunk
CHUNK_OVERLAP = 100   # Characters shared between adjacent chunks
Why 500 Characters?
Chunk Size	Word Count	            Use Case	               Pros	             Cons
100-200	    20-40 words	      Tweets, short messages	    Very precise	Misses context
300-500	    60-100 words	 RAG documents (our choice)	    Good balance	Medium cost
500-1000	100-200 words	 Technical docs, articles	    More context	Less precise
1000-2000	200-400 words	 Legal, academic papers	        Full context	Expensive, diluted
Why 500 works best:

Most paragraphs are 50-150 words (250-750 characters)

Embedding models perform best on 256-512 token inputs

Retrieval is fast (smaller vectors)

Multiple chunks can fit in LLM context window

Why 100 Overlap?
Without overlap:

text
Chunk 1: "...the company policy states that all employ-"
Chunk 2: "ees must complete safety training..."
Result: The word "employees" is split. Search for "employees" fails.

With overlap:

text
Chunk 1: "...the company policy states that all employees"
Chunk 2: "employees must complete safety training..."
Result: Both chunks contain "employees". Search works.

How Overlap Works
text
Document: [==================================================]
          |←─── 500 chars ───→|
          |←────────── 500 chars ──────────→|
          |←────────────────── 500 chars ──────────────────→|
          
Overlap:  |←100→|
          same text appears in two chunks
Visual calculation:

Step size = CHUNK_SIZE - CHUNK_OVERLAP = 500 - 100 = 400

New chunk starts 400 characters into previous chunk

Last 100 characters of each chunk are repeated in next chunk

Impact on Search Quality
Scenario	No Overlap	With Overlap (100)
Query at chunk boundary	May miss answer	Captured in both chunks
Sentence across boundary	Cut in half	Preserved
Paragraph split	Lost connection	Maintained
Repeated information	Not duplicated	Slightly duplicated
When to Adjust Parameters
Increase Chunk Size (800-1000)
Legal documents requiring full context

Technical specifications

Academic papers

Decrease Chunk Size (200-300)
Chat logs, conversations

Short social media posts

When precision > recall

Increase Overlap (150-200)
Highly interconnected content

Documents with long sentences

Poetry or creative writing

Decrease Overlap (0-50)
Very large documents (storage concerns)

Independent sections with clear boundaries

Cost optimization

Memory & Cost Implications
Parameter	                                 Effect
Larger chunks	Fewer total chunks, lower storage, cheaper retrieval, less precise
Smaller chunks	More total chunks, higher storage, more expensive retrieval, more precise
More overlap	More total chunks, higher storage, better recall
Less overlap	Fewer total chunks, lower storage, risk of missing boundary content
Example: Document Split
Original text (1200 characters):

text
"The company pet policy allows employees to bring their dogs to work on Fridays. 
Pets must remain leashed at all times. 
The pet area is located on the third floor. 
Employees must clean up after their pets. 
Violations may result in policy revocation."
Chunks with 500/100:

Chunk 1 (0-500):

text
"The company pet policy allows employees to bring their dogs to work on Fridays. 
Pets must remain leashed at all times. 
The pet area is located on"
Chunk 2 (400-900):

text
"the pet area is located on the third floor. 
Employees must clean up after their pets. 
Violations may result in policy revocation."
Notice: "the pet area is located on" appears in both chunks.

Related Files
src/pipelines/ingestion.py - Contains _split_into_chunks() function

src/pipelines/retrieval.py - Uses chunks for search

src/config.py - Could store CHUNK_SIZE and CHUNK_OVERLAP as settings

Key Takeaway
The 500/100 strategy balances:

Context preservation (overlap handles boundaries)

Storage efficiency (not too many chunks)

Search precision (chunks represent single ideas)

LLM compatibility (fits within context windows)

For production at billion-document scale, these parameters would be:

Made configurable per document type

Optimized based on retrieval metrics (recall@k)

Adjusted using A/B testing