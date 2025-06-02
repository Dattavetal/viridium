"""
data_ingest.py — Load PFAS list and ZeroPM alternatives → build FAISS indexes + SQLite for CAS lookup

Run once:  python data_ingest.py
"""

from pathlib import Path
import pandas as pd
import faiss
import numpy as np
import json
import sqlite3
import sys
from sentence_transformers import SentenceTransformer

# ── Paths ─────────────────────────────────────────────
DATA_DIR = Path("data")
PFAS_CSV = DATA_DIR / "pfas_master_list.csv"
ALT_XLSX = DATA_DIR / "ZeroPM_Alternative_Assessment_DB_v2.0.xlsx"

PFAS_DB     = Path("pfas_lens.db")
PFAS_INDEX  = Path("pfas_names.faiss")
ALT_INDEX   = Path("alternatives.faiss")
PFAS_CORPUS = PFAS_INDEX.with_suffix(".json")
ALT_CORPUS  = ALT_INDEX.with_suffix(".json")

# ── Helpers ─────────────────────────────────────────────
def _exit(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)

def check_files():
    missing = []
    if not PFAS_CSV.exists(): missing.append(str(PFAS_CSV))
    if not ALT_XLSX.exists(): missing.append(str(ALT_XLSX))
    if missing:
        _exit(f"Missing required file(s): {', '.join(missing)}")

# ── PFAS CSV → SQLite + FAISS ─────────────────────────────
def load_pfas() -> pd.DataFrame:
    df = pd.read_csv(PFAS_CSV)
    if "NAME" in df.columns:
        name_col = "NAME"
    elif "PREFERRED NAME" in df.columns:
        name_col = "PREFERRED NAME"
    else:
        _exit("PFAS CSV missing 'NAME' or 'PREFERRED NAME'")
    if not {"CASRN", name_col}.issubset(df.columns):
        _exit("PFAS CSV missing required columns")

    return df[["CASRN", name_col]].rename(columns={name_col: "name"})

def build_pfas_index(df: pd.DataFrame):
    corpus = df["name"].tolist()
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    emb = model.encode(corpus, normalize_embeddings=True, show_progress_bar=True).astype("float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(PFAS_INDEX))
    PFAS_CORPUS.write_text(json.dumps(corpus, indent=2))
    print("✅ Built FAISS index → pfas_names.faiss")

def store_pfas_sqlite(df: pd.DataFrame):
    conn = sqlite3.connect(PFAS_DB)
    conn.executescript("""
        DROP TABLE IF EXISTS substance;
        CREATE TABLE substance (
            cas  TEXT PRIMARY KEY,
            name TEXT
        );
    """)
    df.rename(columns={"CASRN": "cas"}).to_sql("substance", conn, index=False, if_exists="replace")
    conn.close()
    print("✅ Stored CAS + name in SQLite → pfas_lens.db")

# ── Alternatives Excel → FAISS only ─────────────────────
def load_alternatives() -> pd.DataFrame:
    df = pd.read_excel(ALT_XLSX, sheet_name="Alternatives", dtype=str)
    df.columns = [c.lower() for c in df.columns]
    if not {"substance name", "use categories"}.issubset(df.columns):
        _exit("ZeroPM Excel missing required columns")

    df["full_text"] = df["substance name"] + " (" + df["use categories"] + ")"
    return df

def build_alt_index(df: pd.DataFrame):
    corpus = df["full_text"].tolist()
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    emb = model.encode(corpus, normalize_embeddings=True, show_progress_bar=True).astype("float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(ALT_INDEX))
    ALT_CORPUS.write_text(json.dumps(corpus, indent=2))
    print("✅ Built FAISS index → alternatives.faiss")

# ── Main ────────────────────────────────────────────────
def main():
    check_files()

    print("🔄 Loading data...")
    pfas_df = load_pfas()
    alt_df  = load_alternatives()

    print("📦 Ingesting PFAS...")
    build_pfas_index(pfas_df)
    store_pfas_sqlite(pfas_df)

    print("📦 Ingesting Alternatives...")
    build_alt_index(alt_df)

    print("✅ All done.")

if __name__ == "__main__":
    main()
