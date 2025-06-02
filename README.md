Here’s a comprehensive `README.md` file for your **PFAS BOM Scanner + Bedrock Chatbot** application, covering setup, functionality, and implementation in clear steps:

---

# 🚀 PFAS BOM Scanner + Bedrock Chat Co-Pilot

This project is a **Streamlit-based web application** for scanning BOM (Bill of Materials) files and querying PFAS-flagged items using an **AWS Bedrock Claude model**. It allows users to upload a BOM CSV, detect PFAS-flagged parts, and ask natural language questions for part alternatives or details using **Anthropic Claude** via Bedrock.

---

## 📂 Project Structure

```
.
├── backend.db                     # SQLite DB storing PFAS part data
├── streamlit_app.py          # Main Streamlit UI logic
├── aws_bedrock.py            # Claude API integration with Bedrock
├── vector_store.py           # FAISS embedding + search functions
├── sample_bom.csv            # Sample input BOM for testing
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## ⚙️ Features

✅ Upload and scan BOM for PFAS-flagged parts
✅ Detect 32 PFAS parts from database
✅ Ask questions like *“Give me alternatives for P004”*
✅ Use Claude 3 Haiku via AWS Bedrock for Chat Co-Pilot
✅ Optionally search similar parts via vector embeddings

---

## 🔧 Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/yourname/pfas-bom-bedrock.git
cd pfas-bom-bedrock
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 📄 Usage

### 1. Start the App

```bash
streamlit run streamlit_app.py
```

Visit `http://localhost:8501` in your browser.

---

### 2. Upload a BOM CSV

Use the sample BOM file:

```
PartNumber,Description
P001,Valve
P002,Gasket
...
P004,PFAS Seal
...
```

App will flag any of the 32 PFAS parts.

---

### 3. Ask Chat Co-Pilot

Try:

* *"Give me alternative to P004"*
* *"What is the function of P004?"*
* *"Suggest a safer part than P003"*

The chatbot uses Claude 3 Haiku (via Bedrock) to respond.

---

## 🧠 Core Logic

### A. PFAS Detection

The list of 32 flagged part numbers is stored in a SQLite DB (`app.db`) via `sqlmodel`. On upload, the `PartNumber` column is scanned for matches.

### B. Embeddings + Vector Search

Uses `sentence-transformers` + `faiss-cpu` to embed part descriptions and allow semantic search for similar parts.

### C. Claude 3 Haiku via Bedrock

In `aws_bedrock.py`:

```python
payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{"role": "user", "content": 'prompt'}],
    "max_tokens": 600,
    "temperature": 0.2
}
```

This is passed to `client.invoke_model()` with `modelId = "anthropic.claude-3-haiku-20240307-v1:0"`.

---

## ✅ Sample Output

> **User**: give me alternative to P004
> **Bot**: You may consider P005, a generic version of P004 with the same specs but no PFAS components...

---

## 🛠 Troubleshooting

* **No module named `faiss`**: Install `faiss-cpu` explicitly.
* **modelId None error**: Ensure `modelId` is hardcoded and not from missing env vars.
* **Claude error about roles**: Ensure messages alternate like `user → assistant → user`.

---

## 📌 Technologies Used

* **Streamlit** – For frontend UI
* **FAISS + Sentence Transformers** – For vector similarity search
* **AWS Bedrock + Anthropic Claude** – For chat-based AI suggestions
* **SQLite + SQLModel** – Lightweight DB for PFAS tracking

---

## 📎 License

©Dattatray Vetal

---
