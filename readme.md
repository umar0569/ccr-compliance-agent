# CCR Compliance Agent ⚖️🤖

An AI-powered RAG (Retrieval-Augmented Generation) agent designed to answer questions about the **California Code of Regulations (CCR)**.

This project crawls official regulation websites, indexes the legal text into a vector database (Pinecone), and uses Google's Gemini AI to provide accurate, context-aware answers to compliance queries.

---

## 📋 Table of Contents
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [How to Run Each Stage](#-how-to-run-each-stage)
- [Design Decisions](#-design-decisions)
- [Known Limitations](#-known-limitations)
- [What I Would Improve Next](#-what-i-would-improve-next)
- [Troubleshooting](#-troubleshooting)

---

## 📂 Project Structure

```text
ccr-compliance-agent/
├── agent/
│   └── rag_agent.py          # The AI Chat Interface (Gemini + Pinecone)
├── crawler/
│   ├── discover_all_urls.py  # Stage 1: Finds all regulation links
│   └── extract_sections.py   # Stage 2: Scrapes text from links
├── data/
│   └── extracted_data.jsonl  # The raw legal text storage
├── .env                      # API Keys (Google & Pinecone)
├── reset_database.py         # Stage 3: Indexer (Uploads data to Vector DB)
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation


🛠️ Setup Instructions
    1. Prerequisites
        -Python 3.10+ installed.

        -A Google Cloud API Key (for Gemini models).

        -A Pinecone API Key (for Vector Database).

        -Git installed.

    2. Installation
        Clone the repository and install the dependencies:

        # Clone the repo
        git clone <https://github.com/umar0569/ccr-compliance-agent>
        cd ccr-compliance-agent

        # Create a virtual environment
        python -m venv venv
        source venv/bin/activate  # Windows: venv\Scripts\activate

        # Install requirements
        pip install -r requirements.txt

    3. Environment Configuration
        Create a .env file in the root directory
        GOOGLE_API_KEY="your_google_api_key_here"
        PINECONE_API_KEY="your_pinecone_api_key_here"

🚀 How to Run Each Stage

    The pipeline mimics a real-world ETL (Extract, Transform, Load) process.

    Stage 1: The Crawler (Data Acquisition)
    We scrape the target website to gather raw legal text.

    Run: python crawler/extract_sections.py

    Output: Saves clean JSON data to data/extracted_data.jsonl.

    Stage 2: The Indexer (Knowledge Base)
    We process the raw text, generate embeddings, and upload them to the vector database.

    Run: python reset_database.py

    Process: 1. Deletes old index (to prevent duplicates). 2. Creates a new Serverless Index (768 dimensions). 3. Embeds and uploads 5,000+ documents in batches.

    Stage 3: The Agent (AI Assistant)
    We run the interactive chat interface to query the data.

    Run: python agent/rag_agent.py

    Usage: Type a question like "What is the penalty for smog check violations?".


🧠 Design Decisions

    1. RAG Architecture
    Context: The CCR is too large to fit into a single prompt. Decision: I implemented Retrieval-Augmented Generation. The system retrieves only the top 3 relevant text chunks using Vector Similarity Search, then feeds them to the LLM. This reduces costs and hallucinations.

    2. Model Selection: gemini-flash-latest
    Decision: I initially used gemini-2.0-flash but encountered 429 Resource Exhausted errors. I switched to the gemini-flash-latest alias, which offers a more stable Free Tier quota for development.

    3. Embedding Model: text-embedding-004
    Decision: I upgraded from older models to text-embedding-004 (768 dimensions) to capture better semantic meaning in complex legal language.

    4. Robust Error Handling
    Decision: The agent includes a "Retry Loop" with exponential backoff. If the Google API hits a rate limit, the system waits and retries automatically instead of crashing.

⚠️ Known Limitations

    -Rate Limits: The project relies on the Google Gemini Free Tier. Heavy usage effectively pauses the agent for ~60 seconds (handled by retry logic).

    -Data Freshness: The database is a snapshot. It does not auto-update when the real California regulations change.

    -Citation Precision: The agent cites the source URL but does not always highlight the specific paragraph number in the final answer.



🔮 What I Would Improve Next

    -Web Interface: Replace the CLI with a Streamlit dashboard to make the tool accessible to non-technical legal professionals.

    -Hybrid Search: Combine Vector Search (semantic) with Keyword Search (BM25) to better handle specific queries like "Section 10101".

    -Source Highlighting: Improve the UI to show the exact snippet of legal text used to generate the answer.


🔧 Troubleshooting

    Error: 429 Resource Exhausted

    Cause: You hit the Google API rate limit.

    Fix: The agent handles this automatically. Just wait 10-20 seconds and it will retry

    Agent says "I don't know":

    Cause: The relevant document wasn't found in the top 3 search results.

    Fix: Try rephrasing the question or increasing k=5 in rag_agent.py.