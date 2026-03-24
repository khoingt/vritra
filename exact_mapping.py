import re
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def extract_entry_ids(form_id):
    view_url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    })

    print(f"Fetching form: {view_url}")
    resp = session.get(view_url)
    print(f"Status: {resp.status_code}")

    if resp.status_code != 200:
        print("Failed to fetch form page.")
        return

    html = resp.text

    # Extract all entry IDs and their associated question titles
    # Google Forms embeds field data as FB_PUBLIC_LOAD_DATA_ in a script tag
    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*</script>', html, re.DOTALL)
    if not match:
        print("Could not find FB_PUBLIC_LOAD_DATA_ in page. Falling back to regex scan.")
        # Fallback: just find all entry.XXXXXXX patterns
        entry_ids = sorted(set(re.findall(r'entry\.(\d+)', html)))
        print(f"\nFound {len(entry_ids)} entry IDs (no question titles available):")
        for eid in entry_ids:
            print(f"  entry.{eid}")
        return

    try:
        data = json.loads(match.group(1))
        # Question data is nested in data[1][1]
        questions = data[1][1]
        print(f"\nFound {len(questions)} questions:\n")
        mapping_suggestion = {}
        for q in questions:
            try:
                title = q[1]           # Question title
                entry_id = f"entry.{q[4][0][0]}"  # entry ID
                print(f"  [{entry_id}]  {title}")
                mapping_suggestion[title] = entry_id
            except (IndexError, TypeError):
                continue

        # Save suggested mapping to file
        out_file = "mapping_extracted.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(mapping_suggestion, f, ensure_ascii=False, indent=2)
        print(f"\nSuggested mapping saved to '{out_file}'.")
        print("Review it, rename keys to match your CSV headers (e.g. 'Câu 1', 'Câu 2'...), then replace mapping.json.")

    except (json.JSONDecodeError, IndexError, TypeError) as e:
        print(f"Failed to parse form data: {e}")
        # Fallback
        entry_ids = sorted(set(re.findall(r'entry\.(\d+)', html)))
        print(f"\nFallback — raw entry IDs found: {entry_ids}")

if __name__ == "__main__":
    form_id = os.getenv("FORM_ID")
    if not form_id:
        print("Error: FORM_ID not found in .env file.")
    else:
        extract_entry_ids(form_id)