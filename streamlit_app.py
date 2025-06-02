# streamlit_app.py
import streamlit as st
import pandas as pd
import requests

BACKEND = "http://localhost:8000"

st.title("PFAS Detection & Material Replacement Assistant")

# --- Step 1: Upload BOM ---
st.header("1. Upload BOM & Scan for PFAS")
bom_file = st.file_uploader("Upload CSV BOM", type="csv")

if bom_file is not None:
    files = {"file": bom_file.getvalue()}
    res = requests.post(f"{BACKEND}/upload_bom", files={"file": ("bom.csv", bom_file)})
    if res.ok:
        st.success("BOM uploaded successfully!")
        scan = requests.get(f"{BACKEND}/scan_bom")
        flagged = scan.json()
        st.success(f"Found {len(flagged)} PFAS-flagged items")
        st.table(pd.DataFrame(flagged))
    else:
        st.error("Failed to upload BOM")

# --- Step 2: Chat Co-Pilot ---
st.header("2. Chat Co-Pilot: Ask about Alternatives")

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Bot:** {msg['content']}")

prompt = st.text_input("Ask a question:")
if st.button("Send") and prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    payload = {
        "prompt": prompt,
        "history": st.session_state.history
    }
    res = requests.post(f"{BACKEND}/chat", json=payload)
    if res.ok:
        reply = res.json()["reply"]
        st.session_state.history.append({"role": "assistant", "content": reply})
        st.markdown(f"**Bot:** {reply}")
    else:
        st.error("Error in getting response from backend.")
