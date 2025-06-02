#!/usr/bin/env python3
"""
ingest.py  –  load EPA PFAS list + ZeroPM alternatives → SQLite + FAISS

Prerequisites
-------------
✓ data/pfas_master_list.csv               (exported from EPA PFASSTRUCT)
✓ data/ZeroPM_Alternative_Assessment_DB_v2.0.xlsx   (original Excel)

Run once:  python ingest.py
"""

from pathlib import Path
from typing import List
import sys, json, sqlite3

import pandas as pd
import faiss, numpy as np
from sentence_transformers import SentenceTransformer


# ── paths ────────────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data"
PFAS_CSV   = DATA_DIR / "pfas_master_list.csv"
ALT_XLSX   = DATA_DIR / "ZeroPM_Alternative_Assessment_DB_v2.0.xlsx"
# We no longer rely on zeropm_alternatives.csv
ALTS_CSV   = DATA_DIR / "zeropm_alternatives.csv"

DB_PATH     = Path("pfas_lens.db")
INDEX_PATH  = Path("pfas_names.faiss")
CORPUS_PATH = INDEX_PATH.with_suffix(".json")      # stores list of PFAS names


# ── helpers ──────────────────────────────────────────────────────────
def _exit(msg: str) -> None:
    print(f"❌  {msg}")
    sys.exit(1)


def check_files() -> None:
    missing = []
    if not PFAS_CSV.exists():
        missing.append(str(PFAS_CSV))
    if not ALT_XLSX.exists():
        missing.append(str(ALT_XLSX))
    if missing:
        _exit(f"Missing required file(s): {', '.join(missing)}")


# ── CSV loaders & column sanity-checks ───────────────────────────────
def load_pfas() -> pd.DataFrame:
    df = pd.read_csv(PFAS_CSV)

    # Accept either "NAME" or "PREFERRED NAME"
    if "NAME" in df.columns:
        name_col = "NAME"
    elif "PREFERRED NAME" in df.columns:
        name_col = "PREFERRED NAME"
    else:
        _exit("PFAS CSV lacks both 'NAME' and 'PREFERRED NAME' columns")

    required = {"CASRN", name_col}
    if not required.issubset(df.columns):
        _exit(f"PFAS CSV lacks columns: {required - set(df.columns)}")

    # Keep only CASRN + whichever name column, then rename to "NAME"
    df = df[["CASRN", name_col]].rename(columns={name_col: "NAME"})
    return df


def load_alts() -> pd.DataFrame:
    """
    Always read the "Alternatives" sheet from the original Excel.
    Then rename columns to our internal schema.
    """
    # If a stray CSV exists, remove it to avoid confusion
    if ALTS_CSV.exists():
        ALTS_CSV.unlink()

    if not ALT_XLSX.exists():
        _exit(f"Neither {ALTS_CSV} nor {ALT_XLSX} was found!")

    # Read the "Alternatives" sheet in one shot
    df = pd.read_excel(ALT_XLSX, sheet_name="Alternatives", dtype=str)

    # Lowercase column names for consistent matching
    df.columns = [c.lower() for c in df.columns]

    # Now map the actual sheet headers to our normalized names
    rename_map = {
        "substance name": "alt_name",
        "use categories": "use_case",
    }
    df = df.rename(columns=rename_map)

    required = {"alt_name", "use_case"}
    if not required.issubset(df.columns):
        _exit(f"Alternatives sheet lacks columns: {required - set(df.columns)}")

    # We only care about alt_name + use_case here
    return df[["alt_name", "use_case"]].reset_index(drop=True)


# ── SQLite helper ────────────────────────────────────────────────────
def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS substance (
            cas  TEXT PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE IF NOT EXISTS alternative (
            id        INTEGER PRIMARY KEY,
            alt_name  TEXT,
            use_case  TEXT
        );
        """
    )
    return conn


def fill_db(conn: sqlite3.Connection, pfas: pd.DataFrame, alts: pd.DataFrame) -> None:
    # PFAS: rename columns to ["cas","name"]
    pfas = pfas.rename(columns={"CASRN": "cas", "NAME": "name"})
    pfas.to_sql("substance", conn, if_exists="replace", index=False)

    # Alternatives: DataFrame already has columns ["alt_name","use_case"]
    alts.to_sql("alternative", conn, if_exists="replace", index=False)


# ── FAISS index on PFAS names ────────────────────────────────────────
def build_index(sentences: List[str]) -> None:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # normalize_embeddings=True so IndexFlatIP ≈ cosine similarity
    emb = model.encode(sentences, show_progress_bar=True, normalize_embeddings=True)
    emb = emb.astype("float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    faiss.write_index(index, str(INDEX_PATH))
    CORPUS_PATH.write_text(json.dumps(sentences, indent=2))
    print(f"🔧  FAISS index written → {INDEX_PATH}")


# ── main flow ────────────────────────────────────────────────────────
def main() -> None:
    check_files()

    print("🔄  Reading CSV + Excel files …")
    pfas_df = load_pfas()
    alt_df  = load_alts()

    print("🗄   Populating SQLite …")
    with init_db() as conn:
        fill_db(conn, pfas_df, alt_df)

    if not INDEX_PATH.exists():
        print("⚙️   Building FAISS index …")
        build_index(pfas_df["NAME"].tolist())

    print("✅  Ingestion complete")


if __name__ == "__main__":
    main()
