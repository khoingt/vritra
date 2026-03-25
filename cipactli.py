import csv
import json
import re
import sys
import os
import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

PROGRESS_FILE = "progress.json"

def setup_logging(debug_mode, log_dir=None):
    """Set up logging to both console and a timestamped log file."""
    log_filename = datetime.now().strftime("cipactli_%Y-%m-%d_%H-%M-%S.log")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_filename = os.path.join(log_dir, log_filename)
    handlers = [
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers
    )
    return log_filename

def load_config(mapping_file):
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_progress(last_completed_index):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"last_completed": last_completed_index}, f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f).get("last_completed", -1)
    return -1

def clear_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

def create_session(form_id, debug=False):
    """GET the form page to obtain session cookies and the fbzx CSRF token."""
    view_url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": view_url,
    })

    fbzx = None
    try:
        resp = session.get(view_url)
        if debug:
            logging.debug(f"Session GET {view_url} -> {resp.status_code}")
            logging.debug(f"Cookies acquired: {dict(session.cookies)}")

        # Extract the fbzx CSRF token embedded in the form HTML
        match = re.search(r'"fbzx"\s*value="(-?\d+)"', resp.text)
        if not match:
            # Fallback: some versions use a JS variable
            match = re.search(r'FB_PUBLIC_LOAD_DATA_.*?"(-\d{15,})"', resp.text)
        if match:
            fbzx = match.group(1)
            logging.debug(f"fbzx token extracted: {fbzx}")
        else:
            logging.warning("Could not extract fbzx token — submissions may fail.")
    except Exception as e:
        logging.warning(f"Could not pre-fetch form page: {type(e).__name__}: {e}")

    return session, fbzx

def submit_form(form_id, field_mapping, row, session, fbzx, debug=False):
    form_url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"

    # Build as a list of (key, value) tuples to support repeated keys for checkboxes
    form_data = []
    for csv_header, entry_id in field_mapping.items():
        value = row.get(csv_header, "")

        # Câu 5 is a checkbox — Google Forms requires one key per selected option
        if "Câu 5" in csv_header and value:
            for option in value.split("; "):
                form_data.append((entry_id, option))
        else:
            form_data.append((entry_id, value))

    # Include all hidden fields Google Forms requires
    form_data.append(("fbzx", fbzx or ""))
    form_data.append(("pageHistory", "0"))
    form_data.append(("fvv", "1"))
    form_data.append(("partialResponse", f'[null,null,"{fbzx or ""}"]'))
    form_data.append(("submissionTimestamp", "-1"))
    # Sentinel fields — one per question entry, required by Google Forms validation
    for csv_header, entry_id in field_mapping.items():
        form_data.append((f"{entry_id}_sentinel", ""))

    if debug:
        logging.debug(f"Submitting to: {form_url}")
        # Show repeated-key payload in a readable format
        payload_display = {}
        for key, val in form_data:
            if key in payload_display:
                if isinstance(payload_display[key], list):
                    payload_display[key].append(val)
                else:
                    payload_display[key] = [payload_display[key], val]
            else:
                payload_display[key] = val
        logging.debug(f"Payload:\n{json.dumps(payload_display, indent=2, ensure_ascii=False)}")

    try:
        response = session.post(form_url, data=form_data)

        if debug:
            logging.debug(f"Status Code: {response.status_code}")
            logging.debug(f"Response Headers: {dict(response.headers)}")
            logging.debug(f"Response HTML Body (first 2000 chars):\n{'-'*30}\n{response.text[:2000]}\n{'-'*30}")

        is_success = (response.status_code == 200)
        return is_success, response.status_code
    except Exception as e:
        logging.error(f"Request Exception: {type(e).__name__}: {e}")
        return False, None

def main():
    debug_mode = "--debug" in sys.argv

    log_dir = None
    if "--log-dir" in sys.argv:
        idx = sys.argv.index("--log-dir")
        if idx + 1 < len(sys.argv):
            log_dir = sys.argv[idx + 1]

    log_filename = setup_logging(debug_mode, log_dir=log_dir)
    logging.info(f"Logging to: {log_filename}")

    form_id = os.getenv("FORM_ID")
    if not form_id:
        logging.error("FORM_ID not found in .env file.")
        sys.exit(1)

    mapping_file = "mapping.json"
    csv_file = "data.csv"

    try:
        field_mapping = load_config(mapping_file)
        with open(csv_file, mode='r', encoding='utf-8-sig') as file:
            all_rows = list(csv.DictReader(file))
    except FileNotFoundError as e:
        logging.error(f"Required file missing: {e.filename}")
        return

    logging.info(f"Loaded {len(all_rows)} records from {csv_file}")

    # Check for a saved progress file and offer to resume
    start_index = 0
    last_completed = load_progress()
    if last_completed >= 0:
        resume_from = last_completed + 1
        if resume_from >= len(all_rows):
            logging.info("Progress file found but all records already completed. Clearing and starting fresh.")
            clear_progress()
        else:
            answer = input(f"Progress file found. Resume from record {resume_from + 1}/{len(all_rows)}? (y/n): ").lower()
            if answer == 'y':
                start_index = resume_from
                logging.info(f"Resuming from record {start_index + 1}.")
            else:
                clear_progress()
                logging.info("Starting from the beginning.")

    if start_index == 0 and last_completed < 0:
        if input("Start submission for ALL entries? (y/n): ").lower() != 'y':
            logging.info("Aborted by user.")
            return

    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds between retries

    for i, row in enumerate(all_rows[start_index:], start=start_index):
        logging.info(f"Processing {i+1}/{len(all_rows)}: {row.get('Câu 1', 'Entry')[:30]}...")

        success, code = False, None
        for attempt in range(1, MAX_RETRIES + 1):
            # Re-initialize session and fbzx token on every attempt — Google
            # invalidates the session after a rejected POST, so reusing it causes
            # all subsequent retries to fail with the same 400.
            logging.info(f"  Initializing session (attempt {attempt})...")
            session, fbzx = create_session(form_id, debug=debug_mode)
            if fbzx:
                logging.debug(f"  fbzx token acquired: {fbzx}")
            else:
                logging.warning("  No fbzx token found — submission may be rejected.")

            success, code = submit_form(form_id, field_mapping, row, session, fbzx, debug=debug_mode)
            if success:
                logging.info(f"  Record {i+1} submitted successfully (attempt {attempt}).")
                break
            logging.warning(f"  Attempt {attempt}/{MAX_RETRIES} failed (status: {code if code else 'Unknown'}).")
            if attempt < MAX_RETRIES:
                logging.info(f"  Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                logging.warning("  No more retries.")

        if not success:
            logging.error(f"FAILURE on record {i+1} after {MAX_RETRIES} attempts. Stopping script.")
            logging.error(f"Progress saved. Re-run the script to resume from record {i+1}.")
            sys.exit(1)

        save_progress(i)

        if not debug_mode:
            for remaining in range(10, 0, -1):
                print(f"\r  Waiting... {remaining}s ", end="", flush=True)
                time.sleep(1)
            print("\r  Done.              ")

    clear_progress()
    logging.info(f"Success! All {len(all_rows)} responses were processed.")

if __name__ == "__main__":
    main()