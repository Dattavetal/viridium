# backend.py
import os
import pandas as pd
import pathlib
import re
import sqlite3
import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS

from aws_bedrock import chat
from vector_store import build_or_load, search, load_alternatives_index

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

DB = "pfas_lens.db"
INDEX, NAMES = build_or_load(pathlib.Path("pfas_names.faiss"), [])
ALT_INDEX, ALT_NAMES = load_alternatives_index()


# --- helpers ------------------------------------------------
def db():
    return sqlite3.connect(DB)


def exact_cas_set():
    with db() as conn:
        return {row[0] for row in conn.execute("SELECT cas FROM substance")}


PFAS_CAS = exact_cas_set()


# --- API routes --------------------------------------------
@app.post("/upload_bom")
def upload_bom():
    f = request.files["file"]
    tmp = tempfile.NamedTemporaryFile(delete=False)
    f.save(tmp.name)

    df = pd.read_csv(tmp.name)
    os.unlink(tmp.name)

    with db() as conn:
        df.to_sql("bomitem", conn, if_exists="replace", index=False)
    return jsonify({"rows": len(df)})


@app.get("/scan_bom")
def scan_bom():
    with db() as conn:
        df = pd.read_sql("SELECT * FROM bomitem", conn)

    flagged = []
    for _, row in df.iterrows():
        cas = row.get("cas")
        if cas and cas in PFAS_CAS:
            flagged.append({"part": row.part_number, "cas": cas, "match": "exact"})
            continue
        desc = row.get("description", "")
        if pd.notna(desc) and desc.strip():
            matches = search(INDEX, NAMES, desc, 1)
            if matches and matches[0][1] > 0.8:
                flagged.append({
                    "part": row.part_number,
                    "cas": "unknown",
                    "match": "semantic",
                    "matched_name": matches[0][0]
                })
    return jsonify(flagged)


@app.post("/chat")
def chat_route():
    data = request.get_json()
    prompt = data.get("prompt", "")
    history = data.get("history", [])

    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    conn = db()
    material_info = ""
    alt_block = ""

    # Detect CAS pattern (fixed regex)
    match = re.search(r'\b(\d{2,7}-\d{2}-\d)\b', prompt)
    if match:
        cas = match.group(1)
        df = pd.read_sql("SELECT name FROM substance WHERE cas = ?", conn, params=(cas,))
        if not df.empty:
            material_name = df.iloc[0]["name"]
            material_info = f"The material with CAS {cas} is **{material_name}**."

            # Search in alternatives.faiss
            alt_results = search(ALT_INDEX, ALT_NAMES, material_name, top_k=3)
            if alt_results:
                alt_block = "\n\nHere are some possible alternatives:\n\n| Material | Use Case |\n|----------|----------|\n"
                for alt in alt_results:
                    parts = alt[0].split("(")
                    name = parts[0].strip()
                    use = parts[1].replace(")", "").strip() if len(parts) > 1 else "-"
                    alt_block += f"| {name} | {use} |\n"

    enriched_prompt = f"{material_info}\n\n{alt_block}\n\n{prompt}"
    reply = chat(enriched_prompt.strip(), history)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(port=8000)
