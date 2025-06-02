import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load the embedding model once
MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def build_or_load(index_path: Path, sentences: List[str]) -> Tuple[faiss.Index, List[str]]:
    """
    If a FAISS index already exists at index_path, load it and its JSON corpus.
    Otherwise, build a new IndexFlatIP index from `sentences`, write it to disk,
    and save the corpus as JSON (index_path.with_suffix(".json")).
    Returns (index, corpus).
    """
    sent_path = index_path.with_suffix(".json")

    if index_path.exists() and sent_path.exists():
        index = faiss.read_index(str(index_path))
        with sent_path.open("r", encoding="utf-8") as f:
            corpus = json.load(f)
        return index, corpus

    # Build a new index
    corpus = sentences
    # normalize_embeddings=True to treat dot product as cosine similarity
    embeddings = MODEL.encode(corpus, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(index_path))
    sent_path.write_text(json.dumps(corpus), encoding="utf-8")
    return index, corpus


def search(index: faiss.Index, corpus: List[str], query: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Encode the `query`, search against `index`, and return a list of
    (matched_sentence, score) for the top_k results.
    """
    # normalize_embeddings=True to be consistent with build_or_load
    q_vec = MODEL.encode([query], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q_vec, top_k)

    results = []
    for rank, idx in enumerate(ids[0]):
        results.append((corpus[idx], float(scores[0][rank])))
    return results
