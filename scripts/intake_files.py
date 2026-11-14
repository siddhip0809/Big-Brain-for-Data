#!/usr/bin/env python3
"""Read emails saved as files -- Word documents (.docx), Outlook .eml, .txt or .md --
and print a redacted digest for Claude to turn into notes (see "Intake" in CLAUDE.md).

It never writes to the brain and never stores the text: the digest goes to stdout
or to a file you name OUTSIDE the repo. Every email address, phone number and pay
figure is removed before anything is printed (rule 1). For each file it lists the
companies and people already in the brain that the text names, so a note can be
linked without guessing.

    python3 scripts/intake_files.py <folder or file> [...]  [--out <digest.json>]

Outlook .msg files are not readable without an extra library: save them as .eml,
or let Claude read the mailbox directly through the Microsoft 365 connector.
"""
import json, glob, os, re, sys, zipfile, email, html
from email import policy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrub_people import scrub_text

# the people scrubber's phone pattern must tolerate figures in imported biographies; a digest
# is throwaway text, so any run of 9+ digits with separators is treated as a phone number here
PHONE_RUN = re.compile(r"\+?\d[\d ()\-.]{7,}\d")
def redact(text):
    text = scrub_text(text)[0]
    return PHONE_RUN.sub(lambda m: "[phone removed]" if sum(c.isdigit() for c in m.group(0)) >= 9 else m.group(0), text)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def read_eml(path):
    m = email.message_from_bytes(open(path, "rb").read(), policy=policy.default)
    body = m.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    if body and body.get_content_type() == "text/html": text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    head = {"subject": m.get("subject", ""), "date": m.get("date", ""), "from": m.get("from", "")}
    return head, text


def names_index():
    comps, ppl = {}, {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f))
        for n in [c["name"]] + (c.get("aliases") or []):
            if len(n) >= 4: comps[n.lower()] = c["id"]
    for f in glob.glob(f"{REPO}/data/people/*.json"):
        p = json.load(open(f))
        if p.get("name") and " " in p["name"]: ppl[p["name"].lower()] = p["id"]
    return comps, ppl


def mentions(text, index):
    low = text.lower()
    return sorted({v for k, v in index.items() if re.search(r"(?<![\w])" + re.escape(k) + r"(?![\w])", low)})


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    if out: args = [a for a in args if a != out]
    if not args: print(__doc__); sys.exit(2)
    if out and os.path.abspath(out).startswith(REPO): sys.exit("write the digest outside the repo -- it holds message text")
    files = []
    for a in args:
        files += sorted(glob.glob(os.path.join(a, "**", "*"), recursive=True)) if os.path.isdir(a) else [a]
    comps, ppl = names_index()
    digest = []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        try:
            if ext == ".docx": head, text = {"subject": os.path.basename(f)}, read_docx(f)
            elif ext == ".eml": head, text = read_eml(f)
            elif ext in (".txt", ".md"): head, text = {"subject": os.path.basename(f)}, open(f, errors="ignore").read()
            else: continue
        except Exception as e:
            print(f"could not read {f}: {e}", file=sys.stderr); continue
        text = redact(re.sub(r"[ \t]+", " ", text))
        head = {k: redact(str(v)) for k, v in head.items()}
        digest.append({"file": os.path.basename(f), **head, "companies_in_brain": mentions(text, comps),
                       "people_in_brain": mentions(text, ppl), "text": text.strip()})
    if out:
        json.dump(digest, open(out, "w"), indent=1, ensure_ascii=False); print(f"{len(digest)} files -> {out}")
    else:
        print(json.dumps(digest, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
