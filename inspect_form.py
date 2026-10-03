"""Inspect a live Google Form and generate a vritra YAML skeleton.

Discovers question entry IDs, types, options, and page breaks (sections)
automatically so you don't have to view-source the form by hand.

Usage:
    python inspect_form.py <FORM_ID_OR_URL> [-o config.yaml]

Examples:
    python inspect_form.py 1FAIpQLSdWLQ1Ka6bG2bAPd2mwXcdbWpWsJDhrQgniEZK_4VodjTYy8A
    python inspect_form.py "https://docs.google.com/forms/d/e/<ID>/viewform" -o myform.yaml
"""
import argparse
import html
import json
import re
import sys

import requests
import yaml


GOOGLE_TYPE_NAMES = {
    0: "TEXT (short answer)",
    1: "PARAGRAPH (long text)",
    2: "MULTIPLE_CHOICE (radio)",
    3: "DROPDOWN (list)",
    4: "CHECKBOX",
    5: "SCALE (linear)",
    6: "GRID",
    7: "DATE/TIME?",
    8: "SECTION_BREAK (page break)",
    9: "IMAGE?",
    10: "VIDEO?",
}

# Map Google numeric type -> vritra question type.
def map_type(gtype):
    if gtype in (2, 3, 5):
        return "radio"
    if gtype == 4:
        return "checkbox"
    if gtype in (0, 1):
        return "text"
    return None


def extract_form_id(user_input):
    s = user_input.strip()
    m = re.search(r"/d/e/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1), "e"
    m = re.search(r"/d/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1), "d"
    m = re.search(r"([A-Za-z0-9_-]{20,})", s)
    if m:
        return m.group(1), "e"
    raise ValueError(f"Could not parse a form ID from: {user_input!r}")


def fetch_viewform(form_id, kind="e"):
    if kind == "d":
        url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    else:
        url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        raise RuntimeError(f"GET {url} -> HTTP {r.status_code}")
    if "FB_PUBLIC_LOAD_DATA_" not in r.text:
        # Retry with the other URL style before giving up.
        alt = (
            f"https://docs.google.com/forms/d/e/{form_id}/viewform"
            if kind == "d"
            else f"https://docs.google.com/forms/d/{form_id}/viewform"
        )
        r2 = requests.get(alt, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r2.status_code == 200 and "FB_PUBLIC_LOAD_DATA_" in r2.text:
            return r2.text, alt
        raise RuntimeError(
            "Could not find FB_PUBLIC_LOAD_DATA_ in the form HTML. "
            "Is the form public / does it require sign-in?"
        )
    return r.text, url


def parse_items(viewform_html):
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", viewform_html, re.S)
    if not m:
        raise RuntimeError("FB_PUBLIC_LOAD_DATA_ block not found.")
    data = json.loads(m.group(1))
    items = data[1][1]
    return items


def split_pages(items):
    """Split the flat item list into pages on type-8 section breaks.

    Returns (pages, section_index_by_item_id, warnings).
    pages is a list of lists of item dicts.
    section_index_by_item_id maps a Google section-break item ID to the
    0-based page index it starts, so a positive option nav can be resolved
    to vritra's section_N label. Page 0 has no preceding break.
    vritra section ids are arbitrary labels; page_history is derived
    from the page index: "0", "0,1", "0,1,2", ...
    """
    pages = [[]]
    break_ids = []
    warnings = []
    for it in items:
        gtype = it[3] if len(it) > 3 else None
        if gtype == 8:
            break_ids.append(it[0])
            pages.append([])
            continue
        title = html.unescape(str(it[1]).strip()) if len(it) > 1 and it[1] else "(no title)"
        entry_block = it[4] if len(it) > 4 else None
        if not entry_block:
            warnings.append(f"Skipped non-question item id={it[0]} type={gtype} title={title!r}")
            continue
        vtype = map_type(gtype)
        try:
            entry_id = entry_block[0][0]
            raw_options = entry_block[0][1]
        except (IndexError, TypeError):
            warnings.append(f"Unparseable entry block id={it[0]} title={title!r}")
            continue
        if vtype is None:
            warnings.append(
                f"Unsupported Google type {gtype} ({GOOGLE_TYPE_NAMES.get(gtype, '?')}) "
                f"for '{title}' (entry.{entry_id}) — emitting as text placeholder."
            )
            vtype = "text"
            raw_options = []
        options = []
        navs = []
        if vtype in ("radio", "checkbox"):
            for opt in raw_options or []:
                text = html.unescape(str(opt[0])) if opt and opt[0] else ""
                nav = opt[2] if len(opt) > 2 else None
                navs.append(nav)
                # Skip the empty "add option" row Google sometimes appends
                # (text == "" with a flag at index 4 == 1).
                is_add_row = (text == "" and len(opt) > 4 and opt[4] == 1)
                if not is_add_row and text != "":
                    options.append({"text": text, "nav": nav})
        pages[-1].append(
            {
                "item_id": it[0],
                "title": title,
                "gtype": gtype,
                "vtype": vtype,
                "entry_id": entry_id,
                "options": options,
                "navs": navs,
            }
        )
    # Drop a trailing empty page (form ending with a section break).
    if pages and not pages[-1]:
        pages.pop()
    # Map each section-break item ID to the page index it starts.
    # break_ids[k] starts page k+1 (page 0 has no preceding break).
    section_index_by_item_id = {bid: k + 1 for k, bid in enumerate(break_ids)}
    if len(break_ids) > len(pages) - 1:
        # Trailing break with no page after it was popped; drop its mapping.
        section_index_by_item_id = {
            bid: idx for bid, idx in section_index_by_item_id.items() if idx < len(pages)
        }
    return pages, section_index_by_item_id, warnings


def resolve_routing(nav, section_index_by_item_id):
    """Map a Google per-option nav value to a vritra routing string.

    Rules (per user-confirmed semantics):
      None / 0 / -2  -> "continue" (next section)
      -3             -> "submit" (end the form now)
      <section item> -> "goto:section_N" via the break-ID map
    Returns (routing, is_resolved). Unknown navs return ("continue", False)
    so the caller can flag them for manual review.
    """
    if nav in (None, 0, -2):
        return "continue", True
    if nav == -3:
        return "submit", True
    if isinstance(nav, int) and nav in section_index_by_item_id:
        return f"goto:section_{section_index_by_item_id[nav]}", True
    return "continue", False


def build_config(form_id, pages, section_index_by_item_id=None):
    section_index_by_item_id = section_index_by_item_id or {}
    sections = []
    for i, page in enumerate(pages):
        history = ",".join(str(j) for j in range(i + 1))
        questions = []
        for q in page:
            qid = f"entry.{q['entry_id']}"
            if q["vtype"] == "radio":
                opts = []
                for o in q["options"]:
                    routing, _ = resolve_routing(o["nav"], section_index_by_item_id)
                    opts.append({"text": o["text"], "weight": 1.0, "routing": routing})
                questions.append({"id": qid, "type": "radio", "options": opts})
            elif q["vtype"] == "checkbox":
                questions.append(
                    {
                        "id": qid,
                        "type": "checkbox",
                        "options": [
                            {"text": o["text"], "probability": 0.5}
                            for o in q["options"]
                        ],
                    }
                )
            else:
                questions.append(
                    {"id": qid, "type": "text",
                     "text_pool": ["Sample answer — replace me"]}
                )
        sections.append(
            {"id": f"section_{i}", "page_history": history, "questions": questions}
        )
    return {"form_id": form_id, "sections": sections}


def _q(s):
    """YAML-escape a scalar as a double-quoted string."""
    return yaml.safe_dump(s, allow_unicode=True, default_style='"').strip()


def dump_config_yaml(form_id, pages, section_index_by_item_id=None):
    """Render the skeleton as YAML text with TODO placeholders.

    Uses explicit placeholder values (weight 1.0 / probability 0.5 /
    sample text_pool) plus inline TODO comments, since the real
    distribution must be set by hand. Comments are emitted manually
    because yaml.safe_dump cannot preserve them.
    Routing is auto-mapped (-2/None/0 -> continue, -3 -> submit,
    section item ID -> goto:section_N); only weights/probabilities/text
    need manual editing.
    """
    section_index_by_item_id = section_index_by_item_id or {}
    out = []
    out.append("# Auto-generated by inspect_form.py — TODO: edit placeholders below.")
    out.append("#   radio:     weight = relative likelihood (e.g. 85.5 / 10.5 / 4.0)")
    out.append("#   checkbox:  probability = independent 0.0-1.0 chance per option")
    out.append("#   text:      replace text_pool with realistic sample answers")
    out.append("#   routing:   continue | submit | terminate:<history> | goto:<section_id>")
    out.append(f"form_id: {_q(form_id)}")
    out.append("sections:")
    for i, page in enumerate(pages):
        history = ",".join(str(j) for j in range(i + 1))
        out.append(f"  - id: section_{i}")
        out.append(f"    page_history: {_q(history)}")
        out.append("    questions:")
        for q in page:
            qid = f"entry.{q['entry_id']}"
            title = q["title"].replace("\n", " / ")
            out.append(f"      # Q: {title} (google_type={q['gtype']} -> {q['vtype']})")
            out.append(f"      - id: {_q(qid)}")
            out.append(f"        type: {q['vtype']}")
            if q["vtype"] == "radio":
                out.append("        options:")
                for o in q["options"]:
                    routing, resolved = resolve_routing(o["nav"], section_index_by_item_id)
                    out.append(f"          - text: {_q(o['text'])}")
                    out.append("            weight: 1.0  # TODO: set relative weight")
                    if resolved:
                        out.append(f"            routing: {routing}")
                    else:
                        out.append(
                            f"            routing: continue  # TODO: unknown google_nav={o['nav']}, set manually"
                        )
            elif q["vtype"] == "checkbox":
                out.append("        options:")
                for o in q["options"]:
                    out.append(f"          - text: {_q(o['text'])}")
                    out.append("            probability: 0.5  # TODO: set 0.0-1.0")
            else:
                out.append("        text_pool:  # TODO: replace with realistic answers")
                out.append('          - "Sample answer — replace me"')
    out.append("")
    return "\n".join(out)


def print_report(pages, section_index_by_item_id, warnings):
    print(f"Found {len(pages)} page(s) (sections).")
    for i, page in enumerate(pages):
        history = ",".join(str(j) for j in range(i + 1))
        print(f"\n[section_{i}] page_history=\"{history}\" — {len(page)} question(s)")
        for q in page:
            gname = GOOGLE_TYPE_NAMES.get(q["gtype"], "?")
            print(f"  - {q['title']!r}")
            print(f"    id=entry.{q['entry_id']}  google_type={q['gtype']} ({gname}) -> vritra type={q['vtype']}")
            if q["vtype"] in ("radio", "checkbox"):
                for o in q["options"]:
                    routing, resolved = resolve_routing(o["nav"], section_index_by_item_id)
                    if q["vtype"] == "checkbox" or o["nav"] in (None, 0):
                        extra = ""
                    elif resolved:
                        extra = f"  [google_nav={o['nav']} -> {routing}]"
                    else:
                        extra = f"  [google_nav={o['nav']} UNKNOWN -> set routing manually]"
                    print(f"      option: {o['text']!r}{extra}")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ! {w}")
    print(
        "\nNotes:\n"
        "  * vritra section `id` is YOUR label (section_0, ...). Only `page_history`\n"
        "    must match Google's page order: \"0\", \"0,1\", \"0,1,2\", ...\n"
        "  * Routing auto-mapped: google_nav -2/None/0 -> continue, -3 -> submit,\n"
        "    section item ID -> goto:section_N. `terminate:<history>` (screen-out\n"
        "    counting) is still a manual edit if you need fail vs pass stats."
    )


def main():
    ap = argparse.ArgumentParser(description="Inspect a Google Form and emit a vritra config skeleton.")
    ap.add_argument("form", help="Form ID or full /viewform URL")
    ap.add_argument("-o", "--output", default=None, help="Write YAML skeleton here (default: print to stdout)")
    ap.add_argument("--raw", action="store_true", help="Also dump raw item list as JSON to stderr for debugging")
    args = ap.parse_args()

    try:
        form_id, kind = extract_form_id(args.form)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"Fetching form {form_id} ...", file=sys.stderr)
    viewform_html, url = fetch_viewform(form_id, kind)
    print(f"Source: {url}", file=sys.stderr)
    items = parse_items(viewform_html)
    pages, section_index_by_item_id, warnings = split_pages(items)
    print_report(pages, section_index_by_item_id, warnings)

    config = build_config(form_id, pages, section_index_by_item_id)
    text = dump_config_yaml(form_id, pages, section_index_by_item_id)
    # Sanity check: rendered YAML must still load and match the dict form.
    assert yaml.safe_load(text) == config, "rendered YAML round-trip mismatch"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nWrote skeleton to {args.output} — edit weights/probabilities/routing, then run:")
        print(f"  python vritra.py -c {args.output} -n 5 -d 3.0")
    else:
        print("\n--- generated YAML (edit weights/routing, save as config.yaml) ---\n")
        print(text)


if __name__ == "__main__":
    main()
