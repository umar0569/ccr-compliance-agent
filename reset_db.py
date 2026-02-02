import os
import json
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document 

# 1. Load Secrets
load_dotenv(override=True)
INDEX_NAME = "ccr-regulations"
PINECONE_KEY = os.getenv("PINECONE_API_KEY")

print("🚀 Starting Database Reset (Upgrade to 768 dimensions)...")

# 2. Connect to Pinecone
pc = Pinecone(api_key=PINECONE_KEY)

# 3. DELETE the Old Index
if INDEX_NAME in [i.name for i in pc.list_indexes()]:
    print(f"🗑️  Deleting old index '{INDEX_NAME}'...")
    pc.delete_index(INDEX_NAME)
    print("⏳ Waiting 15 seconds for deletion to finish...")
    time.sleep(15) 
else:
    print("ℹ️  Index did not exist. Creating fresh.")

# 4. CREATE the New Index
print("🏗️  Creating new index with dimension=768...")
try:
    pc.create_index(
        name=INDEX_NAME,
        dimension=768, 
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1") 
    )
    print("⏳ Waiting 10 seconds for initialization...")
    time.sleep(10)
except Exception as e:
    print(f"⚠️ Index creation notice: {e}")

# 5. Load ALL Data
print("📂 Loading data from file...")
try:
    with open("data/extracted_data.jsonl", "r", encoding="utf-8") as f:
        all_data = [json.loads(line) for line in f]
    
    # LIMIT REMOVED: Now using len(all_data)
    total_docs = len(all_data)
    print(f"✅ Loaded {total_docs} documents. Preparing to upload...")

    documents = []
    for entry in all_data:
        doc = Document(
            page_content=entry['content_markdown'],
            metadata={
                "source": entry.get('source_url', ''),
                "citation": entry.get('citation', ''),
                "heading": entry.get('section_heading', '')
            }
        )
        documents.append(doc)

    # 6. Upload in Batches (with Progress Bar)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    
    BATCH_SIZE = 100
    print(f"⚡ Uploading in batches of {BATCH_SIZE}...")

    for i in range(0, total_docs, BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        
        try:
            PineconeVectorStore.from_documents(
                batch,
                embeddings,
                index_name=INDEX_NAME
            )
            print(f"   👉 Progress: {min(i + BATCH_SIZE, total_docs)} / {total_docs} docs uploaded...")
        except Exception as e:
            print(f"   ❌ Error on batch {i}: {e}")
            # Optional: wait a bit if rate limit hits
            time.sleep(5)

    print("\n✅ SUCCESS! All documents uploaded.")
    print("👉 Now run: python agent/rag_agent.py")
    
except FileNotFoundError:
    print("❌ Error: Could not find 'data/extracted_data.jsonl'.")
except KeyError as e:
    print(f"❌ Error: Your data is missing a key: {e}")