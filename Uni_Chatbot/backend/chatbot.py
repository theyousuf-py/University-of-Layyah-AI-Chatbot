"""
chatbot.py — Core RAG Engine
Groq API + ChromaDB + Redis Semantic Cache + Rate Limiting
Features: Conversation History (last 5 Q&A) + Professional Not-Found Responses

Cache Logic:
  - HAMESHA cache check karo (history ho ya na ho)
  - Cache HIT  → cached answer return karo, API call nahi ⚡
  - Cache MISS → API call karo WITH history context
  - HAMESHA store karo API answer ke baad
"""

import os
import json
import time
import hashlib
import numpy as np
import redis as redis_lib
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
GROQ_API_KEY         = os.getenv("GROK_API_KEY", "")
REDIS_HOST           = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT           = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB             = int(os.getenv("REDIS_DB", 0))
CHROMA_PATH          = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME      = "uni_chatbot"
RATE_PER_MINUTE      = int(os.getenv("RATE_LIMIT_PER_MINUTE", 20))
RATE_PER_DAY         = int(os.getenv("RATE_LIMIT_PER_DAY", 500))
TOP_K                = 8
SEMANTIC_THRESHOLD   = 0.82   # 0.88 se kam kiya — better cache hits
CACHE_EXPIRY_SECONDS = 3 * 60 * 60
UNIVERSITY_NAME      = os.getenv("UNIVERSITY_NAME", "University of Layyah")
HISTORY_LENGTH       = 5      # Remember last 5 Q&A pairs


# ── Redis Connection ───────────────────────────────────────────────────────────
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        r = redis_lib.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=False,
            socket_connect_timeout=3, socket_timeout=3,
        )
        r.ping()
        print(f"✅ Redis connected at {REDIS_HOST}:{REDIS_PORT}")
        _redis_client = r
        return _redis_client
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        return None


# ── Singleton: Embedding Model ─────────────────────────────────────────────────
_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        print("Loading embedding model...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Embedding model ready!")
    return _embedder


# ── Singleton: ChromaDB ────────────────────────────────────────────────────────
_chroma_collection = None

def get_collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        _chroma_collection = client.get_collection(name=COLLECTION_NAME)
        print(f"✅ ChromaDB connected — {_chroma_collection.count()} chunks indexed")
    return _chroma_collection


# ── Semantic Cache ─────────────────────────────────────────────────────────────
class SemanticCache:
    PREFIX    = "semcache:"
    INDEX_KEY = "semcache:index"

    def __init__(self):
        self.embedder = get_embedder()

    def _embed(self, text):
        return self.embedder.encode(text, normalize_embeddings=True)

    def _cosine_sim(self, a, b):
        return float(np.dot(a, b))

    def search(self, question):
        r = get_redis()
        if r is None:
            return None
        try:
            q_emb = self._embed(question)
            keys  = r.lrange(self.INDEX_KEY, 0, -1)
            best_sim, best_entry = 0.0, None
            for key in keys:
                raw = r.get(key)
                if raw is None:
                    continue
                entry      = json.loads(raw)
                cached_emb = np.array(entry["embedding"], dtype=np.float32)
                sim        = self._cosine_sim(q_emb, cached_emb)
                if sim > best_sim:
                    best_sim, best_entry = sim, entry
            if best_sim >= SEMANTIC_THRESHOLD and best_entry:
                print(f"✅ Cache HIT — {round(best_sim*100,1)}% similarity")
                return {"answer": best_entry["answer"], "cache_hit": True}
        except Exception as e:
            print(f"Cache search error: {e}")
        return None

    def store(self, question, answer):
        r = get_redis()
        if r is None:
            return
        try:
            q_emb = self._embed(question)
            key   = self.PREFIX + hashlib.md5(question.encode()).hexdigest()
            entry = {"question": question, "answer": answer, "embedding": q_emb.tolist()}
            r.setex(key, CACHE_EXPIRY_SECONDS, json.dumps(entry))
            r.lpush(self.INDEX_KEY, key)
            r.expire(self.INDEX_KEY, CACHE_EXPIRY_SECONDS)
        except Exception as e:
            print(f"Cache store error: {e}")


# ── Rate Limiter ───────────────────────────────────────────────────────────────
class RateLimiter:
    def check(self, ip):
        r = get_redis()
        if r is None:
            return True, ""
        try:
            min_key   = f"rl:min:{ip}:{int(time.time() // 60)}"
            min_count = r.incr(min_key)
            r.expire(min_key, 60)
            if min_count > RATE_PER_MINUTE:
                return False, "Too many requests. Please wait a moment."

            day_key   = f"rl:day:{ip}:{int(time.time() // 86400)}"
            day_count = r.incr(day_key)
            r.expire(day_key, 86400)
            if day_count > RATE_PER_DAY:
                return False, "Daily limit reached. Please try again tomorrow."

            return True, ""
        except Exception as e:
            print(f"Rate limiter error: {e}")
            return True, ""


# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are the official AI assistant for {UNIVERSITY_NAME}.

Your job is to answer student questions accurately using ONLY the provided university document information.

RULES:
1. Read ALL the context carefully before answering.
2. Give complete, detailed answers of specific topics — do not summarize or cut information short.
3. If specific numbers, dates, or fees are mentioned in context, always include them exactly.
4. If the answer spans multiple context chunks, combine them into one coherent answer.
5. NEVER mention "context", "documents", "sources", or "chunks" in your answer — just answer naturally.
6. If the student's CURRENT question is in English → reply in English ONLY, no Urdu words at all.
   - If the student's CURRENT question is in Urdu/Roman Urdu → reply in Urdu ONLY.
   - IGNORE the language of previous messages in history.
   - IGNORE the language of document context.
   - ONLY look at the current question's language to decide.
7. Format your answer clearly — use bullet points or numbered lists when listing multiple items.
8. Do not make up or guess any information.
9. You remember the recent conversation — use it for follow-up questions and pronouns like "us", "uski", "it", "that".

CRITICAL — When information is NOT available in the provided context:
Do NOT say "information not found in documents". Instead respond professionally like this:

[If student wrote in English]:
"I'm sorry, I don't have detailed information about [topic] at the moment. For accurate and up-to-date details, I'd recommend:
• 🌐 Official Website: https://ul.edu.pk
• 📧 Email: info@ul.edu.pk | admissions@ul.edu.pk
• 📞 Phone: +92-0606-920247
• 🏫 Visit: University Road, Layyah, Punjab, Pakistan
The university staff will be glad to assist you during office hours (Mon–Fri, 8am–4pm)."

[If student wrote in Urdu]:
"معذرت، اس وقت [موضوع] کے بارے میں میرے پاس مکمل تفصیل موجود نہیں۔ درست معلومات کے لیے:
• 🌐 ویب سائٹ: https://ul.edu.pk
• 📧 ای میل: info@ul.edu.pk | admissions@ul.edu.pk
• 📞 فون: 0606-920247
• 🏫 آفس: یونیورسٹی روڈ، لیہ، پنجاب
دفتری اوقات (پیر تا جمعہ، صبح 8 تا شام 4) میں یونیورسٹی عملہ آپ کی مدد کرے گا۔"
"""


# ── Main Chatbot ───────────────────────────────────────────────────────────────
class UniChatbot:
    def __init__(self):
        self.embedder     = get_embedder()
        self.cache        = SemanticCache()
        self.rate_limiter = RateLimiter()

        if not GROQ_API_KEY:
            raise ValueError("GROK_API_KEY is missing in .env file!")

        self.groq = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        print("✅ Groq client initialized (api.groq.com)")

    def _retrieve(self, question):
        """Retrieve top-K relevant chunks."""
        collection = get_collection()
        q_emb      = self.embedder.encode(question).tolist()

        results = collection.query(
            query_embeddings=[q_emb],
            n_results=min(TOP_K, collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        docs      = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        filtered = [
            (doc, meta, dist)
            for doc, meta, dist in zip(docs, metadatas, distances)
            if dist < 0.75
        ]

        if not filtered:
            filtered = list(zip(docs[:3], metadatas[:3], distances[:3]))

        return "\n\n".join(doc for doc, meta, dist in filtered)

    def _build_messages(self, question, context, history):
        """
        Build Groq messages with conversation history.
        history = list of {"role": "user"|"assistant", "content": "..."}
        Only last HISTORY_LENGTH (5) Q&A pairs are included.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            max_msgs = HISTORY_LENGTH * 2
            for msg in history[-max_msgs:]:
                role    = msg.get("role", "user")
                content = msg.get("content", "").strip()
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({
            "role": "user",
            "content": f"University Document Information:\n\n{context}\n\n---\n\nStudent Question: {question}"
        })

        return messages

    def ask(self, question: str, ip: str = "0.0.0.0", history: list = None) -> dict:
        """
        Full RAG pipeline — Cache + History dono saath kaam karte hain.

        Flow:
          1. Rate limit check
          2. Cache HAMESHA check karo (history ho ya na ho)
             → HIT  : cached answer return karo, API call nahi ⚡
             → MISS : age badho
          3. ChromaDB se context retrieve karo
          4. History ke saath Groq API call karo
          5. Answer HAMESHA cache mein store karo
        """
        if history is None:
            history = []

        # 1. Rate limit
        allowed, msg = self.rate_limiter.check(ip)
        if not allowed:
            return {"error": msg, "rate_limited": True}

        # 2. Cache HAMESHA check karo — history ho ya na ho
        #    Same question pehle kisi ne poocha? → API call nahi, seedha answer ⚡
        cached = self.cache.search(question)
        if cached:
            return cached

        # 3. Cache miss → context retrieve karo
        context = self._retrieve(question)

        # 4. History ke saath messages banao aur Groq call karo
        messages = self._build_messages(question, context, history)

        try:
            print(f"🤖 Groq API: {question[:60]}... (history: {len(history)} msgs)")
            response = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1500,
                temperature=0.1,
                messages=messages
            )
            answer = response.choices[0].message.content.strip()
            print(f"✅ Groq response: {len(answer)} chars")

        except Exception as e:
            print(f"❌ Groq error: {e}")
            return {"error": str(e), "rate_limited": False}

        # 5. HAMESHA cache mein store karo
        #    Agle baar same question aaye (history ho ya na ho) → API call nahi ⚡
        self.cache.store(question, answer)

        return {"answer": answer, "cache_hit": False}


# ── Singleton ──────────────────────────────────────────────────────────────────
_chatbot = None

def get_chatbot():
    global _chatbot
    if _chatbot is None:
        _chatbot = UniChatbot()
    return _chatbot