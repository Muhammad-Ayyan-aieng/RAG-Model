# LLM Generation: Creating Answers from Context

## What is the Generation Step?

Generation is the final phase of RAG where the LLM produces a natural language answer based solely on the retrieved context chunks.

**File responsible:** `src/models/llm_factory.py` → `generate_answer()`

## The Generation Flow
Retrieved Chunks + User Question
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 1. BUILD CONTEXT                                            │
│ _build_context(chunks)                                      │
│ → Formats chunks with [Source 1], [Source 2] labels         │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 2. BUILD PROMPT                                             │
│ _build_prompt(question, context)                            │
│ → Assembles: Context + Question + Instruction               │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SYSTEM PROMPT                                            │
│ _system_prompt()                                            │
│ → Sets rules: "Only use context, never make up info"        │
└─────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM API CALL                                             │
│ client.chat.completions.create()                            │
│ → Sends to Groq (llama-3.3-70b-versatile)                   │
└─────────────────────────────────────────────────────────────┘
│
▼
Return Answer

text

## Our LLM Provider: Groq

**Why Groq instead of OpenAI?**

|    Factor    |    OpenAI    |              Groq               |
|--------------|--------------|---------------------------------|
| Free tier    | $5 trial only| 1,000 requests/day free         |
| Credit card  | Required     | Not required                    |
| Speed        | Fast         | Extremely fast (500+ tokens/sec)|
| Model        | GPT-4o-mini  | Llama-3.3-70b                   |

**Our configuration:**
```python
GROQ_API_KEY = "gsk_..."  # Get from console.groq.com
GROQ_MODEL = "llama-3.3-70b-versatile"
The System Prompt (Critical for RAG)
python
def _system_prompt() -> str:
    return (
        "You are a helpful assistant that answers questions "
        "strictly based on the provided context. "
        "If the answer is not found in the context, say: "
        "'I could not find relevant information in the uploaded documents.' "
        "Never make up information. Never use outside knowledge. "
        "Keep answers clear and concise."
    )
Why This Matters
Instruction	Purpose
"strictly based on provided context"	Prevents LLM from using its training data
"If not found, say 'I could not find'"	Explicit refusal pattern
"Never make up information"	Anti-hallucination
"Keep answers clear and concise"	User experience
Without this prompt, the LLM might:

Use external knowledge not in your documents

Hallucinate plausible-sounding answers

Provide overly verbose responses

Building the Context
python
def _build_context(chunks: list[str]) -> str:
    if not chunks:
        return "No relevant context found."
    
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"[Source {i + 1}]\n{chunk}")
    
    return "\n\n".join(parts)
Example output:

text
[Source 1]
Pets are allowed on Fridays only. Dogs must remain leashed.

[Source 2]
The pet area is located on the third floor. Employees must clean up after pets.
Why label sources?

Helps LLM understand multiple pieces of evidence

Enables answer to reference specific sources

Improves answer quality

Building the User Prompt
python
def _build_prompt(question: str, context: str) -> str:
    return (
        f"Context:\n"
        f"{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer based only on the context above:"
    )
Final prompt sent to LLM:

text
Context:
[Source 1]
Pets are allowed on Fridays only. Dogs must remain leashed.

[Source 2]
The pet area is located on the third floor.

Question: What is the pet policy?

Answer based only on the context above:
The API Call
python
response = client.chat.completions.create(
    model=settings.GROQ_MODEL,
    messages=[
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2,      # Low randomness for factual answers
    max_tokens=1000,      # Limit response length
)
Parameters Explained
Parameter	Value	Why
temperature	0.2	Low = more deterministic, factual
max_tokens	1000	Enough for detailed answer (~750 words)
Temperature guide:

Temperature	Behavior	Use Case
0.0	Deterministic (same answer every time)	Factual Q&A
0.2	Mostly focused	RAG (our choice)
0.7	Creative	Storytelling
1.0	Very creative	Brainstorming
Token Management
What are Tokens?
Tokens are pieces of text the LLM processes:

1 token ≈ 0.75 words in English

"Hello world" = 2 tokens

"Photosynthesis" = 1 token

Our Usage
Component	Typical Tokens
System prompt	~50 tokens
Context (3 chunks)	~500 tokens
Question	~10 tokens
Response	~300 tokens
Total per query	~860 tokens
Groq Free Tier Limits
Limit	Value	Our Usage
Requests per day	1,000	Plenty for demo
Tokens per minute	12,000	~14 queries/minute
Tokens per request	8,000 (context)	We use ~500
Answer Extraction
python
answer = response.choices[0].message.content.strip()
What we get:

text
Based on the provided context, the pet policy states that pets are allowed on Fridays only, dogs must remain leashed, and the pet area is located on the third floor. Employees are required to clean up after their pets.
Error Handling
python
try:
    response = client.chat.completions.create(...)
    return answer
except Exception as e:
    logger.error(f"Groq API error: {e}")
    raise RuntimeError(f"Failed to generate answer: {str(e)}")
Common errors:

Error	Cause	Solution
Rate limit	Too many requests	Wait or upgrade tier
Quota exceeded	Free tier exhausted	Get new API key
Invalid API key	Wrong key in .env	Check GROQ_API_KEY
The Singleton Pattern
python
_client = None

def get_llm_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client
Why singleton:

One connection reused across all requests

No overhead of re-initializing

Better performance

Complete Answer Flow Example
User question: "What is the pet policy?"

Retrieved chunks:

text
Chunk 1: "Pets are allowed on Fridays only"
Chunk 2: "Dogs must remain leashed at all times"
Built prompt:

text
Context:
[Source 1]
Pets are allowed on Fridays only
[Source 2]
Dogs must remain leashed at all times

Question: What is the pet policy?

Answer based only on the context above:
LLM response:

text
Based on the provided documents, the pet policy has two main rules:
1. Pets are allowed on Fridays only
2. Dogs must remain leashed at all times
Switching to Different LLM Providers
Our factory pattern supports easy switching:

python
def generate_answer(question: str, chunks: list[str]) -> str:
    provider = settings.LLM_PROVIDER  # "groq", "openai", "ollama"
    
    if provider == "groq":
        return _groq_generate(question, chunks)
    elif provider == "openai":
        return _openai_generate(question, chunks)
    elif provider == "ollama":
        return _ollama_generate(question, chunks)
To switch: Change one line in .env:

text
LLM_PROVIDER=ollama
Related Files
File	Function	Purpose
src/models/llm_factory.py	generate_answer()	Main generation function
src/models/llm_factory.py	_system_prompt()	Sets LLM behavior
src/models/llm_factory.py	_build_context()	Formats retrieved chunks
src/models/llm_factory.py	_build_prompt()	Assembles final prompt
src/config.py	GROQ_API_KEY, GROQ_MODEL	Configuration
Key Takeaway
The generation step is where RAG prevents hallucination:

System prompt forces use of provided context only

Context formatting helps LLM understand multiple sources

Low temperature ensures factual, consistent answers

Error handling manages API failures gracefully

Without proper prompt engineering, the LLM might ignore context and use its training data, defeating the purpose of RAG.