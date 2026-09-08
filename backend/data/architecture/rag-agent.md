# RAG agent pattern

Retrieval-augmented question answering grounded on an approved document library, with citations on every answer.

## How it works

```text
Question received
    ↓
Retriever finds the most relevant passages from the indexed library
    ↓
Model answers using only the retrieved passages
    ↓
Answer returned with citations to the exact sections
    ↓
If retrieval confidence is low, the agent declines to answer
```

## Design principles

- Index only approved, versioned documents.
- Answers without a citation are not returned.
- Re-index within an hour of a document update.

## Used by

- Policy Q&A Agent

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
