import json
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model once
MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def build_or_load(index_path: Path, sentences: List[str]) -> Tuple[faiss.Index, List[str]]:
    sent_path = index_path.with_suffix(".json")

    if index_path.exists() and sent_path.exists():
        index = faiss.read_index(str(index_path))
        with sent_path.open("r", encoding="utf-8") as f:
            corpus = json.load(f)
        return index, corpus

    embeddings = MODEL.encode(sentences, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(index_path))
    sent_path.write_text(json.dumps(sentences, indent=2))
    return index, sentences


def search(index: faiss.Index, corpus: List[str], query: str, top_k: int = 3) -> List[Tuple[str, float]]:
    q_vec = MODEL.encode([query], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q_vec, top_k)

    results = []
    for rank, idx in enumerate(ids[0]):
        results.append((corpus[idx], float(scores[0][rank])))
    return results


# ── Helpers to load specific indexes ──
def load_pfas_index() -> Tuple[faiss.Index, List[str]]:
    return build_or_load(Path("pfas_names.faiss"), [])


def load_alternatives_index() -> Tuple[faiss.Index, List[str]]:
    alt_path = Path("alternatives.faiss")
    alt_json = alt_path.with_suffix(".json")

    if not alt_path.exists() or not alt_json.exists():
        raise FileNotFoundError(
            "❌ alternatives.faiss or alternatives.json is missing. Please run build_alt_index.py first.")

    return build_or_load(alt_path, [])
