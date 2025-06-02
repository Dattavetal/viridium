import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from aws_bedrock import chat
from vector_store import build_or_load, search

# Load FAISS index & corpus (PFAS names)
INDEX, NAMES = build_or_load(Path("pfas_names.faiss"), [])
DB_PATH = "pfas_lens.db"

st.header("1. Upload BOM & Scan for PFAS")
bom_file = st.file_uploader("Upload CSV BOM", type="csv")
if bom_file is not None:
    df_bom = pd.read_csv(bom_file)
    # Save to a temp table in SQLite (or just scan in-memory)
    conn = sqlite3.connect(DB_PATH)
    df_bom.to_sql("bomitem", conn, if_exists="replace", index=False)

    flagged = []
    # Exact CASRN matches
    pfas_cas_set = {row[0] for row in conn.execute("SELECT cas FROM substance")}
    for _, row in df_bom.iterrows():
        cas = row.get("cas", "")
        if cas in pfas_cas_set:
            flagged.append({"part": row.part_number, "cas": cas, "match": "exact"})
            continue
        # Semantic match on description
        desc = row.get("description", "")
        if pd.notna(desc) and desc.strip():
            results = search(INDEX, NAMES, desc, top_k=1)
            if results and results[0][1] > 0.8:
                flagged.append({
                    "part": row.part_number,
                    "cas": "unknown",
                    "match": "semantic",
                    "matched_name": results[0][0]
                })

    st.success(f"Found {len(flagged)} PFAS‐flagged items")
    st.table(pd.DataFrame(flagged))

st.header("2. Chat Co-Pilot: Ask about Alternatives")
if "history" not in st.session_state:
    st.session_state.history = []

# Display previous messages
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Bot:** {msg['content']}")

# Input box
prompt = st.text_input("Ask a question:")
if st.button("Send") and prompt:
    st.session_state.history.append({"role": "user", "content": prompt})

    # If the user asks for “alternatives for CAS X” or “alternatives for material Y”,
    # perform a simple DB lookup:
    reply = ""
    lowerp = prompt.lower()
    conn = sqlite3.connect(DB_PATH)

    if "alternative for cas" in lowerp:
        # Naively assume last token is CASRN
        cas_target = prompt.split()[-1]
        # Query PFAS name from substance table
        pfas_row = pd.read_sql(
            "SELECT name FROM substance WHERE cas = ?", conn, params=(cas_target,)
        )
        if pfas_row.empty:
            reply = f"No PFAS with CAS {cas_target} found."
        else:
            pfas_name = pfas_row.iloc[0]["name"]
            # Now find matching alternatives by CAS in the alternative table:
            df_alt = pd.read_sql(
                "SELECT alt_name, use_case FROM alternative WHERE cas = ?",
                conn, params=(cas_target,)
            )
            if df_alt.empty:
                reply = f"No alternatives found for CAS {cas_target}."
            else:
                lines = [
                    f"- {r.alt_name} (Use: {r.use_case})"
                    for r in df_alt.itertuples()
                ]
                reply = "Here are the PFAS‐free alternatives I found:\n" + "\n".join(lines)

    elif "alternative for" in lowerp:
        # “alternative for material” fallback: search by alt_name substring
        material = lowerp.replace("alternative for", "").strip()
        df_alt = pd.read_sql(
            "SELECT alt_name, use_case FROM alternative WHERE lower(alt_name) LIKE ?",
            conn, params=(f"%{material}%",)
        )
        if df_alt.empty:
            reply = f"No alternatives matched “{material}.”"
        else:
            lines = [
                f"- {r.alt_name} (Use: {r.use_case})"
                for r in df_alt.itertuples()
            ]
            reply = "I found these alternatives:\n" + "\n".join(lines)

    else:
        # Any other question → call the LLM
        bot_response = chat(prompt, st.session_state.history)
        reply = bot_response

    conn.close()
    st.session_state.history.append({"role": "assistant", "content": reply})
