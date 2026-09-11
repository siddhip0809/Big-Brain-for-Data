#!/usr/bin/env python3
"""Talent flows: who hires from whom, derived from each person's parsed career.

A "move" is a person's most recent change of employer: previous employer ->
current employer. Writes
  data/derived/talent_flows.csv   from_company, to_company, moves, people, functions, latest move
  data/derived/recent_moves.csv   everyone who started their current role in the last 6 months
and (when imported) exposes flows() for the atlas build.
"""
import json, glob, os, re, csv, collections
from datetime import date
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RECENT_MONTHS = 6

norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
STRIP = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|company|co|group|plc|holdings|the|us|usa|construction|contractors?|data ?cent(er|re)s?|engineering)\b\.?", re.I)
loose = lambda x: re.sub(r"[^a-z0-9]", "", STRIP.sub("", (x or "")).lower())

def ym(s):
    m = re.match(r"(?:(\d{1,2})/)?(\d{4})$", (s or "").strip())
    return (int(m.group(2)), int(m.group(1) or 6)) if m else None

# tier labels (mirror viewer/build_graph3d_data.py CATS) and how tiers group
TIER_LABEL = {"hyperscaler": "Hyperscaler", "neocloud": "NeoCloud / AI Infra", "cryptomining": "Cryptomining pivot",
              "developer_operator": "Data Center Developer / Operator", "energy_developer": "Energy developer / utility",
              "general_contractor": "General contractor", "civil_land_engineering": "Civil / land engineering",
              "real_estate_developer": "Real estate & industrial developer", "investor": "Investor"}
CORE = ("hyperscaler", "neocloud", "cryptomining", "developer_operator")
ROLE_PRIORITY = list(TIER_LABEL)
def primary_role(roles):
    for r in ROLE_PRIORITY:
        if r in roles: return r
    return roles[0] if roles else "developer_operator"
def group_of(tier):
    if tier is None: return "outside"
    if tier == "investor": return "investor"
    return "core" if tier in CORE else "adjacent"
# untracked previous employers, by kind (keyword buckets; "other" otherwise)
OUTSIDE_KINDS = [
    ("data centers (untracked operator)", r"\b(data ?cent(er|re)s?|datacenter|colocation|colo\b|evoque|dft\b|dupont fabros|vxchnge|cyxtera|digital fortress|peak 10|viawest|tierpoint|involta|365 main|servercentral|coresite|365 data)\b"),
    ("brokerage & advisory", r"\b(cbre|jll|jones lang|cushman|colliers|newmark|savills|avison|knight frank|cresa|marcus & millichap|transwestern)\b"),
    ("consultancy & engineering", r"\b(accenture|deloitte|ey|ernst|kpmg|pwc|mckinsey|bain|bcg|linesight|cumming|rider levett|rlb|arcadis|wsp|stantec|mott macdonald|ramboll|gleeds|currie|faithful|hdr|kimley|dewberry|black & veatch|burns & mcdonnell|jacobs|aecom|arup|atkins)\b"),
    ("telecom & network", r"\b(at&t|verizon|lumen|centurylink|qwest|global crossing|level 3|level3|zayo|crown castle|t-mobile|sprint|comcast|bt\b|vodafone|orange|telstra|cogent|windstream|frontier communications|mci|worldcom|xo communications|savvis|internap|terremark|telx|telecity|interxion|data return)\b"),
    ("technology", r"\b(intel|cisco|dell|hp\b|hewlett|ibm|salesforce|tesla|sap\b|vmware|nutanix|arista|juniper|akamai|cloudflare|rackspace|godaddy|yahoo|ebay|paypal|uber|lyft|airbnb|netflix|adobe|linkedin|twitter|snap\b|dropbox|box\b)\b"),
    ("energy & utilities (untracked)", r"\b(pg&e|pacific gas|dominion|duke energy|exelon|southern california edison|sce\b|con edison|coned|national grid|xcel|entergy|ameren|aep|american electric|first ?energy|pepco|georgia power|tva|tennessee valley|nrg|calpine|shell|bp\b|chevron|exxon|schlumberger|halliburton|siemens energy|ge power|general electric|schneider|eaton|abb\b|vertiv|caterpillar|cummins)\b"),
    ("construction (untracked)", r"\b(construction|builders|contracting|contractors|homes|constructors|engineering & construction|mechanical|electrical|plumbing)\b"),
    ("finance & investment", r"\b(bank|capital|partners|investments?|asset management|goldman|morgan stanley|jp ?morgan|citi|barclays|hsbc|ubs|credit suisse|wells fargo|deutsche bank|kkr|carlyle|apollo|tpg|equity|fund|ventures|securities|advisors|reit)\b"),
    ("government & military", r"\b(us army|u\.s\. army|army|navy|air force|usaf|marine corps|marines|coast guard|national guard|department of|dept of|county|city of|state of|federal|government|ministry|nasa|noaa|usace|corps of engineers|gsa\b|va\b|dod\b)\b"),
]
def outside_kind(name):
    n = (name or "").lower()
    for kind, rx in OUTSIDE_KINDS:
        if re.search(rx, n): return kind
    return "other"

def load():
    companies = {}
    for f in glob.glob(f"{REPO}/data/companies/*.json"):
        c = json.load(open(f)); c["_tier"] = primary_role(c.get("roles") or []); companies[c["id"]] = c
    for f in glob.glob(f"{REPO}/data/investors/*.json"):   # investors resolve too, as their own tier
        c = json.load(open(f)); c["_tier"] = "investor"; c["name"] = c["name"]; companies["investor:" + c["id"]] = c
    by_norm, by_loose = {}, collections.defaultdict(set)
    for cid, c in companies.items():
        for nm in [c["name"]] + (c.get("aliases") or []):
            by_norm[norm(nm)] = cid
            if loose(nm): by_loose[loose(nm)].add(cid)
    def resolve(name):
        n = norm(name)
        if n in by_norm: return by_norm[n]
        l = loose(name)
        if l and len(by_loose.get(l, ())) == 1: return next(iter(by_loose[l]))
        return None
    people = [json.load(open(f)) for f in glob.glob(f"{REPO}/data/people/*.json")]
    return companies, people, resolve

def flows():
    """-> (moves, recent). moves: list of dicts {person, from_name, from_id, to_id, to_name, function, title, start}."""
    companies, people, resolve = load()
    today = date.today(); cutoff = (today.year + (today.month - RECENT_MONTHS - 1) // 12, (today.month - RECENT_MONTHS - 1) % 12 + 1)
    moves, recent = [], []
    for p in people:
        cur_id = p.get("current_company_id")
        if not cur_id: continue
        career = [c for c in p.get("career", []) if c.get("company")]
        current = [c for c in career if c.get("current")]
        start = None
        if current:
            starts = [ym(c.get("start")) for c in current if ym(c.get("start"))]
            start = min(starts) if starts else None
        # previous employer = the most recent non-current entry at a different company
        here = norm(p.get("current_company"))
        prev = None
        for c in sorted([c for c in career if not c.get("current")], key=lambda c: ym(c.get("end")) or (0, 0), reverse=True):
            if norm(c["company"]) != here and not (here and (here in norm(c["company"]) or norm(c["company"]) in here)):
                prev = c; break
        from_id = resolve(prev["company"]) if prev else None
        from_tier = companies[from_id]["_tier"] if from_id else None
        to_tier = companies[cur_id]["_tier"]
        rec = {"person": p["name"], "person_id": p["id"], "to_id": cur_id, "to_name": companies[cur_id]["name"],
               "function": p.get("function"), "title": p.get("current_title"), "start": f"{start[1]}/{start[0]}" if start else None,
               "from_name": (companies[from_id]["name"] if from_id else prev["company"]) if prev else None, "from_id": from_id,
               "from_title": prev.get("title") if prev else None,
               # classification: where they came from, and the exact tier pair
               "from_tier": from_tier, "to_tier": to_tier,
               "from_label": TIER_LABEL.get(from_tier) if from_tier else ("Outside the industry · " + outside_kind(prev["company"]) if prev else None),
               "to_label": TIER_LABEL[to_tier],
               "flow_class": (f"{group_of(from_tier)} → {group_of(to_tier)}" if prev else None)}
        if prev and rec["from_id"] != cur_id: moves.append(rec)  # a rename/alias of the same employer is not a move
        if start and start >= cutoff: recent.append(rec)
    return moves, recent

if __name__ == "__main__":
    companies, _, _ = load()
    moves, recent = flows()
    agg = collections.defaultdict(list)
    for m in moves: agg[(m["from_id"] or m["from_name"], m["to_id"])].append(m)
    rows = []
    for (frm, to), ms in agg.items():
        rows.append({"from_company": companies[frm]["name"] if frm in companies else frm, "from_tracked": frm in companies,
                     "from_tier": ms[0]["from_label"], "to_company": companies[to]["name"], "to_tier": ms[0]["to_label"],
                     "flow_class": ms[0]["flow_class"], "moves": len(ms),
                     "people": "; ".join(sorted(m["person"] for m in ms)),
                     "functions": "; ".join(f"{k} {v}" for k, v in collections.Counter(m["function"] for m in ms).most_common()),
                     "latest_start": max((m["start"] or "" for m in ms), key=lambda s: ym(s) or (0, 0))})
    rows.sort(key=lambda r: (-r["moves"], r["to_company"], r["from_company"]))
    os.makedirs(f"{REPO}/data/derived", exist_ok=True)
    with open(f"{REPO}/data/derived/talent_flows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    # the tier-to-tier matrix
    matrix = collections.Counter((m["from_label"], m["to_label"]) for m in moves)
    with open(f"{REPO}/data/derived/talent_flow_matrix.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["from_tier", "to_tier", "moves"])
        for (a, b), n in sorted(matrix.items(), key=lambda kv: -kv[1]): w.writerow([a, b, n])
    by_fn = collections.Counter((m["function"] or "Unclassified", m["from_label"]) for m in moves)
    with open(f"{REPO}/data/derived/talent_flow_by_function.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["function", "from_tier", "moves"])
        for (fn, frm), n in sorted(by_fn.items(), key=lambda kv: (kv[0][0], -kv[1])): w.writerow([fn, frm, n])
    by_class = collections.Counter(m["flow_class"] for m in moves)
    print("by class:", dict(by_class))
    print("top tier pairs:", matrix.most_common(10))
    recent.sort(key=lambda m: ym(m["start"]), reverse=True)
    with open(f"{REPO}/data/derived/recent_moves.csv", "w", newline="") as f:
        cols = ["person", "title", "to_name", "to_tier", "function", "start", "from_name", "from_tier", "flow_class", "from_title"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(recent)
    tracked = sum(1 for r in rows if r["from_tracked"])
    print(f"moves: {len(moves)} | flow pairs: {len(rows)} ({tracked} between tracked companies) | recent joiners (<= {RECENT_MONTHS} months): {len(recent)}")
    print("top flows:", [(r['from_company'], r['to_company'], r['moves']) for r in rows[:12]])
