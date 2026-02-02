import json

try:
    with open("data/extracted_data.jsonl", "r", encoding="utf-8") as f:
        # Read just the first line
        first_line = f.readline()
        data = json.loads(first_line)
        
        print("\n🔍 --- DATA INSPECTION ---")
        print(f"✅ Keys found in your file: {list(data.keys())}")
        print("---------------------------")
        
        # specific check
        if "text" in data:
            print("Strange... 'text' key IS present.")
        else:
            print("❌ The key 'text' is MISSING.")
            print(f"👉 You likely need to change entry['text'] to entry['{list(data.keys())[0]}'] (or whichever contains the main content).")

except FileNotFoundError:
    print("❌ Error: File 'data/extracted_data.jsonl' not found.")