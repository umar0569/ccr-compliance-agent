import json
import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
# 1. Load Secrets from .env file
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# 2. Validate Keys
if not PINECONE_API_KEY:
    raise ValueError("❌ PINECONE_API_KEY not found! Please check your .env file.")

# 3. Settings
INDEX_NAME = "ccr-regulations"
INPUT_FILE = "data/extracted_data.jsonl"
CHECKPOINT_FILE = "data/indexed_ids.txt"
BATCH_SIZE = 50

def main():
    print("🚀 Starting Indexing Pipeline...")

    # 1. Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Create Index if it doesn't exist
    existing_indexes = pc.list_indexes().names()
    if INDEX_NAME not in existing_indexes:
        print(f"Creating new index: {INDEX_NAME}...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384, # Matches 'all-MiniLM-L6-v2' model
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    
    index = pc.Index(INDEX_NAME)

    # 2. Load Embedding Model (Runs locally, Free)
    print("📥 Loading AI Model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Load Checkpoint (Resume logic)
    indexed_ids = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            for line in f:
                indexed_ids.add(line.strip())
    print(f"🔄 Resuming... {len(indexed_ids)} items already in database.")

    # 4. Process Data
    batch_vectors = []
    batch_ids = []
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found. Run the extractor first.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"📄 Processing {len(lines)} documents...")

    for i, line in enumerate(lines):
        try:
            record = json.loads(line)
        except:
            continue

        # Skip if empty or already indexed
        if not record.get("content_markdown") or record["source_url"] in indexed_ids:
            continue

        # Create Metadata (For filtering)
        metadata = {
            "citation": str(record.get("citation", "Unknown")),
            "title_number": str(record.get("title_number", "")),
            "chapter": str(record.get("chapter", "")),
            "section_number": str(record.get("section_number", "")),
            "url": record["source_url"],
            "text": record["content_markdown"][:20000] # Limit size
        }

        # Create Embedding
        text_to_embed = f"{record['citation']}: {record['content_markdown']}"
        embedding = model.encode(text_to_embed).tolist()

        # Add to Batch
        batch_vectors.append({
            "id": record["source_url"], 
            "values": embedding,
            "metadata": metadata
        })
        batch_ids.append(record["source_url"])

        # Upload Batch
        if len(batch_vectors) >= BATCH_SIZE or i == len(lines) - 1:
            if batch_vectors:
                try:
                    print(f"   📤 Uploading batch {i}...")
                    index.upsert(vectors=batch_vectors)
                    
                    # Update Checkpoint
                    with open(CHECKPOINT_FILE, "a") as cf:
                        for vid in batch_ids:
                            cf.write(vid + "\n")
                    
                    batch_vectors = []
                    batch_ids = []
                except Exception as e:
                    print(f"   ⚠️ Upload Error: {e}")

    print("✅ Indexing Complete! Your database is ready.")

if __name__ == "__main__":
    main()