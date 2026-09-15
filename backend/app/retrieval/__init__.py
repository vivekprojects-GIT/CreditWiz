"""The retrieval every pillar agent runs, built the way Discover's is.

    index.py   one Chroma collection and one BM25 index per agent, over the
               same text per record, fed by each agent's sources
    agent.py   query -> embedding -> hybrid -> relevance gate -> rerank

Discover keeps its own (marketplace/semantic.py, keyword.py, search.py),
untouched. The Prompts & Skills agent (prompts/agent.py) and the Learning
agent (learning/agent.py) run this.
"""
