import asyncio
from crawl4ai import AsyncWebCrawler

# This is one of the URLs from your screenshot that failed
TEST_URL = "https://govt.westlaw.com/calregs/Document/IEABE8A604A2311EDA5CD8FF14B5C4AE6?viewType=FullText&originationContext=documenttoc&transitionType=CategoryPageItem&contextData=(sc.Default)"

async def debug_one_link():
    print(f"🕵️ Inspecting: {TEST_URL}")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=TEST_URL,
            magic=True,
            bypass_cache=True,
            # We will wait extra long (10 seconds) to be sure
            js_code="await new Promise(r => setTimeout(r, 10000)); window.scrollTo(0, document.body.scrollHeight);" 
        )

        if result.success:
            print("✅ Fetch Success!")
            
            # 1. Save the raw HTML so we can look at it
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(result.html)
            print("📄 Saved HTML to 'debug_page.html'. Please open this file in VS Code!")

            # 2. Print what the text length is
            print(f"📊 Total HTML Length: {len(result.html)} characters")
        else:
            print("❌ Fetch Failed")

if __name__ == "__main__":
    asyncio.run(debug_one_link())