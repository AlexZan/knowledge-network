# RAG Tech Stack Architecture Guide

> Source: Gemini research report (2025-01)
> Context: Reference material for knowledge-network storage decisions

---

## 1. Executive Summary

This document compares retrieval architectures for AI systems. It delineates the distinction between probabilistic retrieval (**Vector/Similarity**) and deterministic retrieval (**Graph/Understanding**), while also addressing high-performance non-semantic optimization techniques (**Binary Evaluation**).

## 2. Core Retrieval Paradigms: Vector vs. Graph

The primary architectural decision in RAG is defining how data is retrieved: by **mathematical proximity** or by **explicit relationship**.

### 2.1 Vector Database (The "Similarity" Engine)

* **Mechanism:** Converts text into high-dimensional vectors (embeddings). Retrieval is based on calculating distance (e.g., Cosine Similarity) in vector space.
* **Core Logic:** "Find data that 'looks' or 'feels' like this query."
* **Best For:** Unstructured text, fuzzy matching, semantic search, broad topic exploration.
* **Limitation:** "The Hallucination of Relevance." It may retrieve semantically similar but factually irrelevant data. It struggles with multi-step reasoning.

### 2.2 Graph Database / Knowledge Graph (The "Understanding" Engine)

* **Mechanism:** Stores data as **Nodes** (Entities) and **Edges** (Relationships). Retrieval is based on traversing explicit paths.
* **Core Logic:** "Traverse the specific path connecting Entity A to Entity B."
* **Best For:** Structured data, complex reasoning, supply chains, fraud detection, corporate hierarchies.
* **Limitation:** Rigid schema. If a relationship is not explicitly defined, it cannot be traversed.

### 2.3 Comparative Analysis

| Feature | Vector Database | Graph Database |
|---------|-----------------|----------------|
| **Search Basis** | Probabilistic (Similarity) | Deterministic (Connection) |
| **Data Structure** | Embeddings (Float Arrays) | Nodes & Edges (Adjacency Lists) |
| **Query Type** | "Find similar concepts" | "Find connected entities" |
| **Reasoning** | Single-hop / Contextual | Multi-hop / Logical |
| **Blind Spot** | Precision (Exact values) | Unstructured / Unknown connections |

## 3. Storage Layer: NoSQL Landscape

A Graph Database is a subset of the NoSQL family. Understanding the distinction is crucial for storage selection.

### 3.1 The "Aggregate" Family (Document & Key-Value)

* **Examples:** MongoDB, DynamoDB, Redis.
* **Philosophy:** Keep related data together in one blob.
* **Structure:** JSON Documents or Key-Value pairs.
* **Performance:** Fast for retrieving *single items* or *lists*. Slow for joining data.
* **RAG Role:** Storing the raw "chunks" of text that vectors point to.

### 3.2 The "Connection" Family (Graph)

* **Examples:** Neo4j, Amazon Neptune.
* **Philosophy:** Break data apart to link it. Relationships are "first-class citizens" stored physically on disk.
* **Structure:** Nodes and Pointers.
* **Performance:** Constant time for traversing relationships (index-free adjacency).
* **RAG Role:** Providing the "ground truth" or "skeleton" of facts to ground the AI.

## 4. High-Performance "Binary" Primitives

While Vector Search (Float32 math) is computationally expensive, modern stacks utilize binary logic for speed and precision.

### 4.1 Roaring Bitmaps (Logical Filtering)

* **Concept:** Represents sets of document IDs as compressed bitmaps.
* **Operation:** Uses CPU-level bitwise instructions (AND, OR, XOR) to filter millions of documents in microseconds.
* **Use Case:** Hard filtering *before* vector search (e.g., "Only search documents where Status=Active AND Region=US").
* **Speed:** Near-instant (Non-semantic).

### 4.2 Binary Quantization (Optimized Semantic Search)

* **Concept:** Compresses 1024-dimensional float vectors into binary strings (1s and 0s).
  * Positive float → 1
  * Negative float → 0
* **Operation:** Uses **Hamming Distance** (XOR + Popcount) instead of Cosine Similarity.
* **Benefit:** Reduces memory usage by ~32x and increases search speed by ~30x-100x.
* **Trade-off:** Slight loss in precision, often mitigated by re-ranking the top results.

### 4.3 Protocol Buffers (Compact Serialization)

* **Concept:** A language-neutral, platform-neutral extensible mechanism for serializing structured data.
* **Use Case:** Storing the actual retrieved data (Forward Index) efficiently. Far smaller and faster to parse than JSON.

## 5. Decision Matrix: Choosing the Stack

Use this matrix to determine the components of your RAG pipeline.

### Scenario A: The "chatbot for documentation"

* **Data:** Unstructured PDFs, Help Docs.
* **User Intent:** "How do I reset my password?"
* **Recommended Stack:**
  * **Vector DB:** Yes (Primary retrieval).
  * **Graph DB:** No (Overkill).
  * **Binary Filter:** Basic (e.g., filter by product version).

### Scenario B: The "Forensic Analyst"

* **Data:** Financial transactions, emails, corporate entities.
* **User Intent:** "Who authorized the payment to the vendor owned by the CEO's brother?"
* **Recommended Stack:**
  * **Graph DB:** Yes (Crucial for linking Person → Company → Transaction).
  * **Vector DB:** Secondary (For searching email text).
  * **Architecture:** **GraphRAG** (Hybrid).

### Scenario C: The "Scale-at-all-costs" System

* **Data:** Billions of log lines or user comments.
* **Constraint:** Must return results in <50ms.
* **Recommended Stack:**
  * **Binary Quantization:** Mandatory (Vectors converted to bits).
  * **Roaring Bitmaps:** Mandatory (For metadata filtering).
  * **Protocol Buffers:** Mandatory (For data transport).
  * **Graph:** Only if pre-computed.

## 6. Summary: The Modern Hybrid Stack

The most robust RAG systems currently deploy a **Hybrid Architecture**:

1. **Ingestion:** Text is chunked (Vectorized) AND entities are extracted (Graph).
2. **Query Processing:**
   * **Step 1 (Binary Filter):** Use **Roaring Bitmaps** to restrict search space (e.g., Date > 2023).
   * **Step 2 (Retrieval):** Run parallel searches:
     * **Lexical:** Keyword match for precision (IDs, Codes).
     * **Vector (Binary Quantized):** Semantic match for intent.
     * **Graph:** Traversal for related context.
3. **Synthesis:** Combine results and feed to LLM.

---

## Relevance to Knowledge Network

This aligns with our Thesis 2 (Dynamic Knowledge Network) and Thesis 5 (Emergent Confidence):

| Knowledge Network Need | RAG Component |
|------------------------|---------------|
| "What do I know about X?" | Vector (semantic search) |
| Support/contradiction edges | Graph (relationship traversal) |
| Confidence propagation | Graph (topology algorithms) |
| Abstraction hierarchy | Graph (multi-hop traversal) |

**Recommendation:** Hybrid approach - see tech-stack discussion.
