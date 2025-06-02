from flask import Flask, request, jsonify
import sqlite3, pandas as pd, tempfile, pathlib, os
from vector_store import build_or_load, search
from aws_bedrock import chat

app = Flask(__name__)
DB = "pfas_lens.db"
INDEX, NAMES = build_or_load(pathlib.Path("pfas_names.faiss"), [])  # load existing

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

    with db() as conn:
        df.to_sql("bomitem", conn, if_exists="replace", index=False)
    return jsonify({"rows": len(df)})

@app.get("/scan_bom")
def scan_bom():
    with db() as conn:
        df = pd.read_sql("SELECT rowid, * FROM bomitem", conn)

    flagged = []
    for _, row in df.iterrows():
        cas = row.get("cas")
        if cas and cas in PFAS_CAS:
            flagged.append({"part": row.part_number, "cas": cas, "match": "exact"})
            continue
        # semantic on description
        matches = search(INDEX, NAMES, row.description, 1)
        if matches and matches[0][1] > 0.8:
            flagged.append({"part": row.part_number, "cas": "unknown", "match": "semantic"})
    return jsonify(flagged)

@app.post("/chat")
def chat_route():
    data = request.get_json()
    prompt   = data["prompt"]
    history  = data.get("history", [])
    reply = chat(prompt, history)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(port=8000)
