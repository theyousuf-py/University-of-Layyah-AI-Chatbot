# 🎓 University of Layyah — AI Chatbot

A full-stack RAG (Retrieval-Augmented Generation) chatbot for University of Layyah that answers student queries about admissions, fee structure, departments, and campus facilities in both **Urdu and English**.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6B35?style=flat)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat)
![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?style=flat&logo=redis&logoColor=white)

---

## ✨ Features

- 🔍 **Semantic Search** — ChromaDB vector store with custom semantic chunking
- 🧠 **Conversation Memory** — Remembers last 5 Q&A pairs for follow-up questions
- ⚡ **Semantic Cache** — Redis-based cache avoids redundant API calls
- 🌐 **Bilingual** — Responds in Urdu or English based on user's language
- 🛡️ **Rate Limiting** — Per-minute and per-day limits per user IP
- 💬 **Floating Widget** — Embeddable on any webpage as a chat bubble
- 📞 **Smart Fallback** — Professional response with contact info when answer not found

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API — LLaMA 3.3 70B Versatile |
| Vector DB | ChromaDB (persistent) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Cache | Redis (semantic similarity cache) |
| Backend | FastAPI + Python |
| Frontend | React (floating widget) |
| Chunking | Custom semantic chunking algorithm |

---

## 📁 Project Structure

```
ul-chatbot/
├── backend/
│   ├── chatbot.py          # Core RAG engine — Groq + ChromaDB + Redis
│   ├── main.py             # FastAPI server — REST endpoints
│   ├── rag_pipeline.py     # Data indexer — semantic chunking + ChromaDB ingestion
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment variables template
│
├── frontend/
│   ├── src/
│   │   └── App.jsx         # React floating chat widget
│   ├── public/
│   │   └── index.html
│   └── package.json
│
└── pdfs/                   # University data files (.txt / .pdf)
    ├── 01_admissions.txt
    ├── 02_faculty_computing.txt
    ├── 03_faculty_agriculture.txt
    ├── 04_faculty_management.txt
    ├── 05_faculty_natural_sciences.txt
    ├── 06_faculty_veterinary.txt
    ├── 07_campus_facilities.txt
    ├── 08_university_general_info.txt
    ├── 09_contact_info.txt
    ├── 10_administration_staff.txt
    ├── 11_scholarships_facilities.txt
    └── 12_fee_structure.txt
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis server
- Groq API key → [console.groq.com](https://console.groq.com)

### 1. Clone the repository
```bash
git clone https://github.com/theyousuf-py/ul-chatbot.git
cd ul-chatbot
```

### 2. Backend setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

### 3. Index the data
```bash
python rag_pipeline.py
```

### 4. Start the backend
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend setup
```bash
cd frontend
npm install
npm start
```

---

## 🔑 Environment Variables

```env
GROK_API_KEY=your_groq_api_key
REDIS_HOST=localhost
REDIS_PORT=6379
CHROMA_DB_PATH=./chroma_db
UNIVERSITY_NAME=University of Layyah
RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_PER_DAY=500
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a question and receive an answer |
| GET | `/api/health` | Server health check |
| GET | `/api/stats` | ChromaDB indexed chunk count |

### Example Request
```json
POST /api/chat
{
  "question": "What is the fee structure for BSCS?",
  "history": [
    { "role": "user", "content": "When do admissions open?" },
    { "role": "assistant", "content": "Admissions open in July and August each year." }
  ]
}
```

### Example Response
```json
{
  "answer": "The BSCS morning program fee for Semester I is PKR 41,800...",
  "cache_hit": false
}
```

---

## 🏗️ Architecture

```
User Message
     │
     ▼
Rate Limiter (Redis)
     │
     ▼
Semantic Cache (Redis) ──── HIT ──▶ Return cached answer
     │ MISS
     ▼
ChromaDB Vector Search (top-8 chunks)
     │
     ▼
Groq API — LLaMA 3.3 70B
(system prompt + context + conversation history)
     │
     ▼
Answer → Cache Store → Return to User
```

---

© 2025 University of Layyah. All rights reserved.

<p align="center">Built for <a href="https://ul.edu.pk">University of Layyah</a></p>
