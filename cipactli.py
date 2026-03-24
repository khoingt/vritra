import csv
import json
import sys
import os
import requests
import time
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

def load_config(mapping_file):
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def submit_form(form_id, field_mapping, row, debug=False):
    form_url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
    form_data = {}
    
    for csv_header, entry_id in field_mapping.items():
        value = row.get(csv_header, "")
        
        # Clean the value if it accidentally contains brackets or extra quotes from the CSV
        clean_value = value.strip("[]'\"")
        
        # Multiple Choice logic for Câu 5 (Checkbox) [2, 3]
        if "Câu 5" in csv_header and clean_value:
            form_data[entry_id] = clean_value.split("; ")
        else:
            # Single Choice logic for all other questions [1-5]
            form_data[entry_id] = clean_value

    if debug:
        print(f"\n[DEBUG] Submitting to: {form_url}")
        print(f"[DEBUG] Payload: {json.dumps(form_data, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(form_url, data=form_data)
        
        if debug:
            print(f"[DEBUG] Status Code: {response.status_code}")
            print("[DEBUG] Response HTML Body Preview:")
            print("-" * 30)
            print(response.text[:1000]) 
            print("-" * 30)
        
        # Script continues if the Status Code is 200
        is_success = (response.status_code == 200)
        return is_success, response.status_code
    except Exception as e:
        if debug:
            print(f"[DEBUG] Request Error: {e}")
        return False, None

def main():
    debug_mode = "--debug" in sys.argv
    
    form_id = os.getenv("FORM_ID")
    if not form_id:
        print("Error: FORM_ID not found in .env file.")
        sys.exit(1)

    mapping_file = "mapping.json"
    csv_file = "data.csv"
    
    try:
        field_mapping = load_config(mapping_file)
        with open(csv_file, mode='r', encoding='utf-8-sig') as file:
            # We now use all_rows directly to ensure every entry is submitted
            all_rows = list(csv.DictReader(file))
    except FileNotFoundError as e:
        print(f"Error: Required file missing - {e.filename}")
        return

    print("=" * 50)
    print("       FOOTBALL SURVEY AUTOMATION TOOL")
    print("=" * 50)
    print(f"FILE: {csv_file} | DEBUG: {'ON' if debug_mode else 'OFF'}")
    print(f"Total Entries to Submit: {len(all_rows)}")
    print("-" * 50)

    if input("Start submission for ALL entries? (y/n): ").lower() != 'y':
        print("Aborted.")
        return

    for i, row in enumerate(all_rows):
        print(f"Processing {i+1}/{len(all_rows)}: {row.get('Câu 1', 'Entry')[:30]}...")
        success, code = submit_form(form_id, field_mapping, row, debug=debug_mode)
        
        if not success:
            print(f"\n[!] FAILURE DETECTED on record {i+1}. Stopping script.")
            print(f"Status Code: {code if code else 'Unknown'}")
            sys.exit(1)
        
        if not debug_mode: time.sleep(0.5)

    print(f"\nSuccess! All {len(all_rows)} responses were processed.")

if __name__ == "__main__":
    main()