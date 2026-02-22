import os
import json
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document 
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Load Secrets
load_dotenv(override=True)
INDEX_NAME = "ccr-regulations"
PINECONE_KEY = os.getenv("PINECONE_API_KEY")

print("🚀 Starting Database Reset (Local MiniLM + 1K Chunks)...")

pc = Pinecone(api_key=PINECONE_KEY)

# 2. DELETE the Old Index
if INDEX_NAME in [i.name for i in pc.list_indexes()]:
    print(f"🗑️  Deleting old index '{INDEX_NAME}'...")
    pc.delete_index(INDEX_NAME)
    time.sleep(10) 
else:
    print("ℹ️  Index did not exist. Creating fresh.")

# 3. CREATE the New Index (384 dimensions for MiniLM)
print("🏗️  Creating new index with dimension=384...")
try:
    pc.create_index(
        name=INDEX_NAME,
        dimension=384, 
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1") 
    )
    time.sleep(5)
except Exception as e:
    pass 

# 4. Load ALL DATA
print("📂 Loading data from file...")
try:
    with open("data/extracted_data.jsonl", "r", encoding="utf-8") as f:
        raw_data = [json.loads(line) for line in f] 
    
    raw_documents = []
    for entry in raw_data:
        if not entry.get('content_markdown') or len(entry['content_markdown'].strip()) < 10:
            continue
            
        doc = Document(
            page_content=entry['content_markdown'],
            metadata={
                "source": entry.get('source_url', ''),
                "heading": entry.get('section_heading', '')
            }
        )
        raw_documents.append(doc)

    # 5. SPLIT DOCUMENTS
    print("✂️ Splitting documents into 1K chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100 
    )
    documents = text_splitter.split_documents(raw_documents)

    total_valid_docs = len(documents)
    print(f"✅ Created {total_valid_docs} document chunks.")

    # 6. UNLIMITED LOCAL EMBEDDINGS (No API Rate Limits!)
    print("🧠 Loading local MiniLM embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 7. UPLOAD LOGIC 
    BATCH_SIZE = 100 
    print(f"⚡ Uploading in batches of {BATCH_SIZE}...")
    
    for i in range(0, total_valid_docs, BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        PineconeVectorStore.from_documents(batch, embeddings, index_name=INDEX_NAME)
        print(f"   👉 Progress: {min(i + BATCH_SIZE, total_valid_docs)} / {total_valid_docs} uploaded...")

    print("\n✅ SUCCESS! All data uploaded safely.")
    
except Exception as e:
    print(f"❌ Critical Error: {e}")