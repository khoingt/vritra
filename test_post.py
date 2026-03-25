import re
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FORM_ID = os.getenv("FORM_ID")
if not FORM_ID:
    print("Error: FORM_ID not found in .env file.")
    exit(1)

# --- Single test record ---
TEST_ROW = {
    "entry.3095189":  "Có, tôi chơi thường xuyên (ít nhất 1 lần mỗi tuần)",
    "entry.2069101950": "Chỉ mang giày đá bóng (giày đinh/turf)",
    "entry.1474574734": "Có, điều này xảy ra khá thường xuyên",
    "entry.1518800713": "Không tham gia chơi và chờ lần khác",
    "entry.829106081": "Không có lựa chọn nào khác vào lúc đó",  # single checkbox option
    "entry.1841526350": "Có, rõ rệt",
    "entry.308462639":  "Có, nhưng tôi vẫn chấp nhận rủi ro đó",
    "entry.2124783957": "Có, đây là một vấn đề thực sự cần được giải quyết",
    "entry.1092332564": "Không quan tâm",
}

# --- Step 1: GET the form to get cookies + fbzx ---
view_url = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"
post_url = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": view_url,
})

print(f"[1] GET {view_url}")
get_resp = session.get(view_url)
print(f"    Status : {get_resp.status_code}")
print(f"    Cookies: {dict(session.cookies)}")

# Extract fbzx
fbzx = None
match = re.search(r'"fbzx"\s*value="(-?\d+)"', get_resp.text)
if not match:
    match = re.search(r'\["(-\d{10,})"\]', get_resp.text)
if match:
    fbzx = match.group(1)
    print(f"    fbzx   : {fbzx}")
else:
    print("    fbzx   : NOT FOUND")

# Extract ALL hidden fields for reference
hidden = re.findall(r'<input[^>]+type="hidden"[^>]*>', get_resp.text)
print(f"\n[2] Hidden fields in form ({len(hidden)} total):")
for h in hidden:
    name  = re.search(r'name="([^"]*)"', h)
    value = re.search(r'value="([^"]*)"', h)
    print(f"    {name.group(1) if name else '?':30s} = {value.group(1)[:60] if value else '?'}")

# --- Step 2: POST ---
form_data = list(TEST_ROW.items()) + [
    ("fbzx", fbzx or ""),
    ("pageHistory", "0"),
    ("fvv", "1"),
    ("partialResponse", f'[null,null,"{fbzx or ""}"]'),
    ("submissionTimestamp", "-1"),
] + [(f"{k}_sentinel", "") for k in TEST_ROW]

print(f"\n[3] POST {post_url}")
print(f"    Payload:")
for k, v in form_data:
    print(f"      {k}: {v}")

post_resp = session.post(post_url, data=form_data)
print(f"\n[4] Response Status : {post_resp.status_code}")
print(f"    Response Headers: {json.dumps(dict(post_resp.headers), indent=6)}")

# --- Step 3: Diagnose response ---
print(f"\n[5] Diagnosis:")
if "freebirdFormviewerViewResponseConfirmationMessage" in post_resp.text:
    print("    ✓ SUCCESS — confirmation message detected in response body!")
elif post_resp.status_code == 200:
    print("    ? 200 OK but no confirmation message found — may still have worked.")
else:
    title = re.search(r'<title>(.*?)</title>', post_resp.text)
    print(f"    ✗ FAILED — page title: {title.group(1) if title else 'unknown'}")

# Save full response for inspection
with open("test_post_response.html", "w", encoding="utf-8") as f:
    f.write(post_resp.text)
print(f"\n[6] Full response body saved to: test_post_response.html")
