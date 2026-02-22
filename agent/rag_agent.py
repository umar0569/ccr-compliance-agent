import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq

# 1. Load Secrets
load_dotenv(override=True)
INDEX_NAME = "ccr-regulations"

print("🧠 Initializing AI Agent (Llama 3 on Groq + Local Embeddings)...")

try:
    # 2. MATCH THE DATABASE: Local MiniLM Embeddings (384 dimensions)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 3. Connect to Pinecone
    vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # 4. Initialize the "Brain" (Meta's Llama 3 running on Groq)
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)

    print("✅ Agent is online and ready! (Type 'quit' to exit)\n")

    # 5. Start the Chat Loop
    while True:
        user_input = input("User: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        print("Thinking...")
        
        # Step A: Search Pinecone
        relevant_docs = retriever.invoke(user_input)
        
        # Step B: Mash text together
        context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Step C: Build the Prompt
        prompt = f"""You are a highly accurate legal compliance assistant for the California Code of Regulations (CCR).
Use the following pieces of retrieved context to answer the user's question.
If you don't know the answer or if it is not clearly stated in the context, just say 'I don't know'. Do not try to make up an answer or hallucinate outside information.

Context:
{context_text}

Question: {user_input}
"""
        
        # Step D: Get the answer!
        response = llm.invoke(prompt)
        print(f"🤖 Agent: {response.content}\n")
        print("-" * 50)

except Exception as e:
    print(f"\n❌ Critical Error: {e}")