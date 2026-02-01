import asyncio
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# --- CONFIGURATION ---
INPUT_FILE = "data/discovered_section_urls.jsonl"
OUTPUT_FILE = "data/extracted_data.jsonl"
CONCURRENCY = 3

# --- RESUME LOGIC ---
processed_urls = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Ensure we have content and at least a Title or Section to count as "Done"
                if data.get("content_markdown") and (data.get("title_number") or data.get("section_number")):
                    processed_urls.add(data["source_url"])
            except: pass
    print(f"🔄 Resuming... {len(processed_urls)} valid records already extracted.")

def parse_metadata_from_text(markdown_text, struct, current_section_num, current_section_head):
    """
    Scans the first 20 lines of text to find missing Hierarchy or Section info.
    """
    lines = markdown_text.split('\n')[:30] # Look at first 30 lines
    
    for line in lines:
        line = line.strip()
        if not line: continue

        # 1. Fallback for Hierarchy (Title, Div, Chap)
        if not struct["title_number"]:
            m = re.match(r"^Title\s+([0-9A-Za-z]+)\.?\s+(.*)", line, re.IGNORECASE)
            if m: 
                struct["title_number"] = m.group(1)
                struct["title_name"] = m.group(2)
        
        if not struct["division"]:
            m = re.match(r"^Division\s+([0-9A-Za-z]+)\.?\s+(.*)", line, re.IGNORECASE)
            if m: struct["division"] = f"{m.group(1)}. {m.group(2)}"

        if not struct["chapter"]:
            m = re.match(r"^Chapter\s+([0-9A-Za-z]+)\.?\s+(.*)", line, re.IGNORECASE)
            if m: struct["chapter"] = f"{m.group(1)}. {m.group(2)}"

        # 2. Fallback for Section Number (Crucial!)
        # Looks for: "§ 123. Heading" OR "Section 123. Heading"
        if not current_section_num:
            # Match "§ 1234. Text"
            sec_m = re.match(r"^§\s*([0-9A-Za-z\.]+)\.?\s*(.*)", line)
            if not sec_m:
                # Match "Section 1234. Text"
                sec_m = re.match(r"^Section\s+([0-9A-Za-z\.]+)\.?\s*(.*)", line, re.IGNORECASE)
            
            if sec_m:
                current_section_num = sec_m.group(1)
                current_section_head = sec_m.group(2)

    return struct, current_section_num, current_section_head

async def extract_content():
    urls_to_process = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if record["section_url"] not in processed_urls:
                            urls_to_process.append(record["section_url"])
                    except: pass
    except FileNotFoundError:
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    total = len(urls_to_process)
    print(f"🚀 Starting Extraction for {total} URLs...")

    # Wait for the main text box
    WAIT_CONDITION = """() => {
        return document.getElementById('co_document') !== null || 
               document.getElementById('co_docContent') !== null || 
               document.querySelector('.co_contentWrapper') !== null;
    }"""

    async with AsyncWebCrawler(verbose=False) as crawler:
        for i in range(0, total, CONCURRENCY):
            batch = urls_to_process[i : i + CONCURRENCY]
            print(f"   Processing batch {i}/{total}...")

            tasks = []
            for url in batch:
                tasks.append(crawler.arun(
                    url=url,
                    js_code="window.scrollTo(0, document.body.scrollHeight);",
                    wait_for=f"js:{WAIT_CONDITION}",
                    magic=True,
                    bypass_cache=True
                ))

            results = await asyncio.gather(*tasks)

            for result in results:
                if not result.success:
                    print(f"   ⚠️ Network Fail: {result.url}")
                    continue

                soup = BeautifulSoup(result.html, "html.parser")

                # 1. GET CONTENT
                content_div = soup.find("div", {"id": "co_document"}) or \
                              soup.find("div", {"id": "co_docContent"}) or \
                              soup.find("div", class_="co_contentWrapper")

                if not content_div:
                    print(f"   ⚠️ Content not found for {result.url}")
                    continue

                markdown_text = content_div.get_text(separator="\n\n", strip=True)

                # 2. GET BREADCRUMBS (Hierarchy)
                breadcrumbs = []
                bc_div = soup.find("div", {"id": "co_breadcrumb"}) or soup.find("div", class_="co_breadcrumb")
                if bc_div:
                    breadcrumbs = [li.get_text(strip=True) for li in bc_div.find_all("li")]
                
                # Parse Breadcrumbs first
                hierarchy_data = {
                    "title_number": None, "title_name": None, "division": None,
                    "chapter": None, "subchapter": None, "article": None
                }
                # (Simple parsing logic matches previous script)
                for item in breadcrumbs:
                    item = item.strip()
                    m = re.match(r"^(Title|Division|Chapter|Article)\s+([0-9A-Za-z\.]+)\.?\s*(.*)", item, re.IGNORECASE)
                    if m:
                        t = m.group(1).lower()
                        if t == "title": hierarchy_data["title_number"], hierarchy_data["title_name"] = m.group(2), m.group(3)
                        elif t == "division": hierarchy_data["division"] = f"{m.group(2)}. {m.group(3)}"
                        elif t == "chapter": hierarchy_data["chapter"] = f"{m.group(2)}. {m.group(3)}"
                        elif t == "article": hierarchy_data["article"] = f"{m.group(2)}. {m.group(3)}"

                # 3. GET METADATA (Title Tag)
                page_title = soup.find("title").get_text().split("|")[0].strip() if soup.find("title") else "Unknown"
                
                # Try to find Section in Title Tag
                sec_match = re.search(r"§\s*([0-9A-Za-z\.]+)\.\s*(.*)", page_title)
                section_number = sec_match.group(1) if sec_match else None
                section_heading = sec_match.group(2) if sec_match else page_title

                # 4. FALLBACK: Look inside the text if Breadcrumbs/Title failed
                hierarchy_data, section_number, section_heading = parse_metadata_from_text(
                    markdown_text, hierarchy_data, section_number, section_heading
                )

                # 5. SAVE
                extracted_record = {
                    "citation": f"{hierarchy_data['title_number']} CCR § {section_number}" if section_number else page_title,
                    "source_url": result.url,
                    "retrieved_at": datetime.utcnow().isoformat(),
                    **hierarchy_data, # Unpack hierarchy fields
                    "section_number": section_number,
                    "section_heading": section_heading,
                    "content_markdown": markdown_text
                }

                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(extracted_record) + "\n")

            await asyncio.sleep(1.0)

    print("✅ Extraction Complete!")

if __name__ == "__main__":
    asyncio.run(extract_content())