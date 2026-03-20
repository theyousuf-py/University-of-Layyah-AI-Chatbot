"""
rag_pipeline.py — University of Layyah RAG Indexer
.txt / .pdf files → Semantic Chunks → ChromaDB

Chunking Method: Semantic Chunking (OPTIMIZED for UL data)
  - Settings tuned based on actual file analysis:
      13 files | avg 2071 chars/file | avg sentence 90 chars
  - MIN_CHUNK_CHARS lowered to 50 (fee lines are short: "Semester-I: 41,800")
  - MAX_CHUNK_CHARS lowered to 700 (focused chunks = better retrieval)
  - BREAKPOINT_THRESHOLD lowered to 0.28 (keeps related info together)

Token budget per query:
  System prompt  : ~350 tokens
  8 chunks × 65t : ~520 tokens
  History (5 QA) : ~500 tokens
  User question  : ~20 tokens
  ─────────────────────────────
  Total input    : ~1390 tokens  (Groq limit: 128,000 — very comfortable)

Run:
    python rag_pipeline.py

After running, restart backend:
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import re
import uuid
import numpy as np
import pdfplumber
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
PDFS_DIR        = os.getenv("PDFS_DIR", "./pdfs")
CHROMA_PATH     = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "uni_chatbot"
EMBED_MODEL     = "all-MiniLM-L6-v2"

# ── Semantic Chunking Settings (OPTIMIZED) ─────────────────────────────────────
#
# BREAKPOINT_THRESHOLD = 0.28
#   Cosine DISTANCE threshold between consecutive sentences.
#   0.0 = identical topic | 1.0 = completely different topic
#   WHY 0.28: Our files are short (avg 2071 chars). Higher threshold (0.35)
#   was splitting too aggressively, separating related fee rows and contact
#   details that belong together. 0.28 keeps related sentences in one chunk.
#
# MIN_CHUNK_CHARS = 50
#   WHY 50 (not 80): Critical fee lines like "Semester-I: 41,800 PKR" are
#   only ~25-35 chars. Old MIN=80 was DROPPING these entirely → fee queries
#   returned wrong answers. Set to 50 to capture all structured data lines.
#   Lines smaller than 50 still get merged into adjacent chunks (see code).
#
# MAX_CHUNK_CHARS = 700
#   WHY 700 (not 2000): 
#   - Old MAX=2000 → only 17 chunks total for 13 files
#     → 1 chunk had fee table + admission info mixed = bad retrieval
#   - New MAX=700 → ~44 chunks → each chunk = 1 focused topic
#   - 700 chars ÷ 4 = ~175 tokens per chunk
#   - TOP_K=8 chunks × 175 tokens = 1400 tokens → clean, fast Groq response
#
# BATCH_SIZE = 100
#   ChromaDB insert batch size. Fine for our scale (~44 chunks).

BREAKPOINT_THRESHOLD = 0.28
MIN_CHUNK_CHARS      = 50
MAX_CHUNK_CHARS      = 700
BATCH_SIZE           = 100

print("\n" + "=" * 60)
print("  University of Layyah — RAG Pipeline (Semantic Chunking)")
print("=" * 60)
print(f"\n  Settings:")
print(f"  BREAKPOINT_THRESHOLD : {BREAKPOINT_THRESHOLD}")
print(f"  MIN_CHUNK_CHARS      : {MIN_CHUNK_CHARS}")
print(f"  MAX_CHUNK_CHARS      : {MAX_CHUNK_CHARS}")
print(f"  EMBED_MODEL          : {EMBED_MODEL}")


# ── Load Embedding Model ───────────────────────────────────────────────────────
print("\n📦 Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL)
print(f"✅ Embedding model ready: {EMBED_MODEL}")


# ── Semantic Chunker ───────────────────────────────────────────────────────────
def split_into_sentences(text: str) -> list:
    """
    Split text into sentences.
    Handles: full stops, bullet points, numbered lists, newlines.
    """
    # Split on sentence endings OR double newlines OR bullet/dash list items
    parts = re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=\s*[-•*\d])', text)
    result = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # If a part is still very long (e.g., a dense paragraph), split by newline too
        if len(p) > MAX_CHUNK_CHARS:
            sub_parts = p.split('\n')
            result.extend([sp.strip() for sp in sub_parts if sp.strip()])
        else:
            result.append(p)
    return result


def semantic_chunk(text: str, source: str, page: int = 1) -> list:
    """
    Split text into semantic chunks.

    Algorithm:
    1. Split text into sentences/lines
    2. Embed all sentences at once (batch)
    3. Cosine distance between consecutive sentence pairs
    4. Split where distance > BREAKPOINT_THRESHOLD (= topic change)
    5. Merge tiny fragments into adjacent chunks (prevents data loss)
    """
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    # Single sentence — return as-is if long enough
    if len(sentences) == 1:
        chunk_text = sentences[0]
        if len(chunk_text) >= MIN_CHUNK_CHARS:
            return [{"text": chunk_text, "source": source, "page": page}]
        return []

    # Embed all sentences at once
    embeddings = embedder.encode(
        sentences,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    # Cosine distance between consecutive sentences
    distances = []
    for i in range(len(embeddings) - 1):
        sim      = float(np.dot(embeddings[i], embeddings[i + 1]))
        distance = 1.0 - sim
        distances.append(distance)

    # Find split points (topic changes)
    split_indices = [i + 1 for i, d in enumerate(distances) if d > BREAKPOINT_THRESHOLD]

    # Build raw chunks from groups
    raw_chunks = []
    start = 0
    for split_idx in split_indices:
        group = " ".join(sentences[start:split_idx]).strip()
        raw_chunks.append(group)
        start = split_idx
    raw_chunks.append(" ".join(sentences[start:]).strip())

    # ── Post-process: merge tiny chunks, split giant ones ─────────────────────
    chunks = []
    pending = ""

    for raw in raw_chunks:
        if not raw:
            continue

        combined = (pending + " " + raw).strip() if pending else raw

        if len(combined) < MIN_CHUNK_CHARS:
            # Too small — carry forward (merge with next chunk)
            pending = combined
            continue

        if len(combined) > MAX_CHUNK_CHARS:
            # Save any pending first
            if pending and len(pending) >= MIN_CHUNK_CHARS:
                chunks.append({"text": pending, "source": source, "page": page})
            pending = ""
            # Split oversized chunk
            for sub in _split_long_chunk(raw):
                if len(sub) >= MIN_CHUNK_CHARS:
                    chunks.append({"text": sub, "source": source, "page": page})
        else:
            chunks.append({"text": combined, "source": source, "page": page})
            pending = ""

    # Flush any remaining pending
    if pending:
        if len(pending) >= MIN_CHUNK_CHARS:
            chunks.append({"text": pending, "source": source, "page": page})
        elif chunks:
            # Merge tiny tail into last chunk
            chunks[-1]["text"] = (chunks[-1]["text"] + " " + pending).strip()

    # Fallback: if nothing was produced, return whole text
    if not chunks:
        full = " ".join(sentences).strip()
        if full:
            chunks.append({"text": full[:MAX_CHUNK_CHARS], "source": source, "page": page})

    return chunks


def _split_long_chunk(text: str) -> list:
    """Split an oversized chunk by newlines, then by words if needed."""
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    result, current = [], ""
    for part in parts:
        if len(current) + len(part) + 1 < MAX_CHUNK_CHARS:
            current = (current + " " + part).strip()
        else:
            if current:
                result.append(current)
            current = part
    if current:
        result.append(current)
    return result if result else [text[:MAX_CHUNK_CHARS]]


# ── File Readers ───────────────────────────────────────────────────────────────
def read_txt(path: str) -> list:
    """
    Read .txt file.
    Split by ## section headers if present, otherwise treat as one section.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return []
    sections = re.split(r'\n(?=## )', text)
    pages = []
    for i, section in enumerate(sections):
        if section.strip():
            pages.append({"text": section.strip(), "page": i + 1})
    return pages if pages else [{"text": text, "page": 1}]


def read_pdf(path: str) -> list:
    """Extract text from PDF page by page."""
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"text": text, "page": i + 1})
    except Exception as e:
        print(f"     ⚠️  PDF read error: {e}")
    return pages


# ── ChromaDB Setup ─────────────────────────────────────────────────────────────
print("\n🗄️  Setting up ChromaDB...")
client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False)
)

try:
    client.delete_collection(name=COLLECTION_NAME)
    print("   ↳ Old collection deleted (fresh index)")
except Exception:
    pass

collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)
print(f"✅ ChromaDB ready: {CHROMA_PATH}")


# ── Process Files ──────────────────────────────────────────────────────────────
supported = (".txt", ".pdf")
all_files = sorted([
    f for f in os.listdir(PDFS_DIR)
    if f.lower().endswith(supported)
])

if not all_files:
    print(f"\n❌ No .txt or .pdf files found in '{PDFS_DIR}/'")
    print("   → Copy your 13 clean .txt files there and re-run.")
    exit(1)

print(f"\n📁 Found {len(all_files)} file(s) in '{PDFS_DIR}/'")

all_chunks  = []
total_pages = 0

for filename in all_files:
    filepath = os.path.join(PDFS_DIR, filename)
    print(f"\n📄 Processing: {filename}")

    pages = read_txt(filepath) if filename.lower().endswith(".txt") else read_pdf(filepath)

    if not pages:
        print("     ⚠️  No text extracted — skipping")
        continue

    total_pages += len(pages)
    file_chunks  = 0

    for page_data in pages:
        chunks = semantic_chunk(page_data["text"], source=filename, page=page_data["page"])
        all_chunks.extend(chunks)
        file_chunks += len(chunks)

    print(f"     ✅ {len(pages)} section(s) → {file_chunks} semantic chunks")

print(f"\n{'─'*50}")
print(f"📊 Total: {len(all_files)} files | {total_pages} sections | {len(all_chunks)} chunks")

# Show chunk size distribution
if all_chunks:
    lengths = sorted([len(c["text"]) for c in all_chunks])
    avg = int(sum(lengths) / len(lengths))
    print(f"   Chunk sizes — min:{lengths[0]} | avg:{avg} | max:{lengths[-1]} chars")
    print(f"   Token estimate — avg:{avg//4} | 8 chunks: {avg*8//4} tokens to Groq")


# ── Embed & Insert ─────────────────────────────────────────────────────────────
print(f"\n🔢 Embedding {len(all_chunks)} chunks...")

texts     = [c["text"]   for c in all_chunks]
metadatas = [{"source": c["source"], "page": c["page"]} for c in all_chunks]
ids       = [str(uuid.uuid4()) for _ in all_chunks]

embeddings = embedder.encode(
    texts,
    batch_size=64,
    normalize_embeddings=True,
    show_progress_bar=True
).tolist()

print(f"\n💾 Inserting into ChromaDB in batches of {BATCH_SIZE}...")
for start in range(0, len(all_chunks), BATCH_SIZE):
    end = start + BATCH_SIZE
    collection.add(
        documents  = texts[start:end],
        embeddings = embeddings[start:end],
        metadatas  = metadatas[start:end],
        ids        = ids[start:end],
    )
    print(f"   ↳ {min(end, len(all_chunks))}/{len(all_chunks)} inserted")


# ── Summary ────────────────────────────────────────────────────────────────────
final_count = collection.count()
avg_len = int(sum(len(c["text"]) for c in all_chunks) / len(all_chunks)) if all_chunks else 0

print("\n" + "=" * 60)
print("  ✅  Indexing Complete!")
print("=" * 60)
print(f"  Files processed  : {len(all_files)}")
print(f"  Sections read    : {total_pages}")
print(f"  Semantic chunks  : {len(all_chunks)}")
print(f"  ChromaDB total   : {final_count}")
print(f"  Avg chunk size   : {avg_len} chars (~{avg_len//4} tokens)")
print(f"  8 chunks to Groq : ~{avg_len*8//4} tokens per query")
print(f"  ChromaDB path    : {CHROMA_PATH}")
print(f"  Collection name  : {COLLECTION_NAME}")
print("=" * 60)
print("\n🚀 Next step — restart your backend:")
print("   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload\n")