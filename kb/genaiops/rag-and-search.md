# RAG and Azure AI Search

Retrieval levers, chunking, search modes, and building a RAG flow. Concepts surfaced by practice questions (the labs and my production project don't cover GenAIOps), verified against Microsoft Learn where possible.

## RAG retrieval quality

From practice question [Q5](../../practice/genaiops/q005-rag-retrieval-accuracy.md).

When answers are incomplete because the **right content isn't retrieved
consistently**, fix retrieval, not generation:

| Lever | Fixes | Cost |
|---|---|---|
| **Chunk size + overlap** tuned to the content's structure | Context cut across chunk boundaries; chunks too broad or narrow | One-time re-index |
| **Re-ranking** (semantic ranker / cross-encoder) | Relevant chunks retrieved but ranked too low | Modest, per query |
| **Hybrid search** (keyword + vector) | Exact names, codes and IDs that vectors miss | Low |
| New embedding model or dimensions | Representation quality | Re-embed everything |
| Bigger token limits | Nothing retrieval-related | Higher cost on every call |

- "Without changing the embedding model" rules out changing vector
  dimensions, which is a property of the model.
- More context tokens can't fix a passage that was never retrieved.

## Chunk size, overlap and similarity threshold

From practice question [Q66](../../practice/genaiops/q066-chunk-overlap-threshold.md).

| Knob | Too high | Too low |
|---|---|---|
| **Chunk size** | *Semantic dilution*: one chunk mixes topics → blurry embedding → loose, off-topic matches | Fragments lose context; answers incomplete |
| **Overlap** | Neighbouring chunks repeat each other → **duplicate** results in top-k (e.g., 400 of 1,200 tokens) | Sentences split at boundaries lose context (10–15% is a common start) |
| **Similarity threshold** | Strict filter drops relevant but lower-scoring chunks | Admits weak matches (noise) |
| **Top-k** | Irrelevant chunks dilute the prompt | Misses needed chunks |

Fix dilution with **smaller chunks**, not a lower threshold. Keyword-only
search removes semantic matching altogether.

## Search modes in Azure AI Search

From practice question [Q25](../../practice/genaiops/q025-search-keyword-vs-semantic.md).

| Mode | Good at | Weak at |
|---|---|---|
| **Keyword / full-text (BM25)** | **Exact terms**: IDs, codes, names | Paraphrases and synonyms |
| **Vector** | Meaning: paraphrased natural-language questions | Exact IDs and rare tokens |
| **Hybrid** (keyword + vector, merged with RRF) | Both at once | — |
| **Semantic ranker** (on top) | Re-ranking the top results by meaning | Doesn't retrieve, only re-orders |

Exam cue: "exact identifiers must match" → keyword. "Natural-language
relevance" → vector + semantic ranking. Usually configured together as
**hybrid + semantic ranker**.

## Building a RAG flow from files

From practice question [Q61](../../practice/genaiops/q061-rag-flow-from-local-files.md), [Q76](../../practice/genaiops/q076-fabrikam-rag-serving-retrieval.md).

| Step | What it produces |
|---|---|
| 1. **Data asset** (upload local files) | The source content, versioned in the project |
| 2. **Vector index** | Chunks + embeddings, stored in Azure AI Search (or a FAISS file) |
| 3. **Connection** | Credentials/endpoint for the model (and search) the flow calls |
| 4. **Flow** | lookup (index) → prompt (context + question) → LLM |

To serve it: deploy the flow to a **managed online endpoint**. If curated
documents already live in **Azure AI Search**, reuse that index as the
retriever instead of building a new one.
