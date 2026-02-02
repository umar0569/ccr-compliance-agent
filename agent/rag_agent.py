import os
import sys
import time
from dotenv import load_dotenv

# --- IMPORTS ---
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document 

# 1. Load Secrets (FORCE RE-READ)
load_dotenv(override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# --- DEBUG CHECK ---
if GOOGLE_API_KEY:
    print(f"🔑 DEBUG: Using API Key ending in: ...{GOOGLE_API_KEY[-4:]}")
else:
    print("❌ Error: Keys are missing from .env file!")
    sys.exit(1)
# -------------------

INDEX_NAME = "ccr-regulations"
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

def main():
    print("🤖 Initializing AI Agent (Gemini Flash Latest + Text-Embedding-004)...")

    # 2. Connect to Database (Pinecone)
    # MUST match the model used in reset_database.py (768 dimensions)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    
    try:
        vectorstore = PineconeVectorStore.from_existing_index(
            index_name=INDEX_NAME,
            embedding=embeddings
        )
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return

    # 3. Connect to Brain (Gemini Flash Latest)
    # Using the 'latest' alias is usually safer for Rate Limits on free tiers
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-flash-latest", 
        temperature=0.3
    )

    print("\n💬 Agent is Ready! (Type 'exit' to quit)")
    print("------------------------------------------------")

    while True:
        query = input("\nUser: ")
        if query.lower() in ["exit", "quit"]:
            break
            
        try:
            print("Thinking...", end="", flush=True)
            
            # --- RETRY LOGIC ---
            retries = 3
            search_results = None
            
            for attempt in range(retries):
                try:
                    search_results = vectorstore.similarity_search(query, k=3)
                    break 
                except Exception as e:
                    # Catch Rate Limits
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(f"\n⏳ Rate limit hit. Waiting 10 seconds (Attempt {attempt+1}/{retries})...")
                        time.sleep(10)
                    else:
                        raise e 
            
            if not search_results:
                print("\n🤖 AI: I couldn't find any relevant documents.")
                continue

            context_text = "\n\n".join([doc.page_content for doc in search_results])

            # --- PROMPT ---
            final_prompt = f"""
            You are a Legal Compliance Assistant.
            
            - If the user greets you (hi/hello), reply politely.
            - Otherwise, use the context below to answer the question.
            - If the answer is not in the context, say "I don't know."

            CONTEXT:
            {context_text}

            QUESTION: 
            {query}
            """

            response = llm.invoke(final_prompt)
            
            # --- CLEANER: Remove weird JSON/List artifacts ---
            answer_text = response.content
            
            # If Google sends a list/box, extract the text inside
            if isinstance(answer_text, list) and len(answer_text) > 0:
                if 'text' in answer_text[0]:
                    answer_text = answer_text[0]['text']
            
            # Print the clean answer
            print(f"\n\n🤖 AI: {str(answer_text).strip()}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()