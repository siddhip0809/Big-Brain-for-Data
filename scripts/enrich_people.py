#!/usr/bin/env python3
"""Derive, for every record in data/people/:
  - `function`        the company department the current title belongs to
  - `seniority_rank`  0 = C-suite/founder ... 5 = individual contributor
                      (Clockwork's own `seniority` wins when present)
  - `career`          the raw career_history string parsed into entries
See docs/schema.md ("person"). Re-run after importing new people:
    python3 scripts/enrich_people.py          # dry run: prints distributions
    python3 scripts/enrich_people.py --apply  # writes the records
"""
import json, glob, re, sys, os, collections
APPLY = '--apply' in sys.argv
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

SENIORITY = [  # (rank, label, regex on lowercased title)
    (0, 'C-suite / Founder', r"\bchief\b|\bc[a-z]o\b|\bceo\b|\bcfo\b|\bcoo\b|\bcto\b|\bcio\b|\bcro\b|\bfounder\b|\bco-founder\b|\bowner\b|\bmanaging partner\b|(?<!vice )(?<!vice-)\bpresident\b(?! of the)"),
    (1, 'EVP / SVP / MD',    r"\bexecutive vice president\b|\bsenior vice president\b|\bsvp\b|\bevp\b|\bmanaging director\b|\bpartner\b|\bgeneral manager\b|\bcountry manager\b"),
    (2, 'VP / Head of',      r"\bvice president\b|\bvice-president\b|\bvp\b|\bhead\b|\bglobal lead\b"),
    (4, 'Manager / Lead',    r"\baccount executive\b|\bsales executive\b|\bexecutive assistant\b"),
    (3, 'Director',          r"\bdirector\b|\bexecutive\b|\bprincipal\b|\bdirecteur\b|\bdirektør\b"),
    (4, 'Manager / Lead',    r"\bmanager\b|\blead\b|\bnegotiator\b|\bsuperintendent\b|\bsupervisor\b|\bleader\b"),
]
SENIORITY_FROM_CW = {'CXO': 0, 'Senior Vice President': 1, 'Vice President': 2, 'Director': 3, 'Manager': 4, 'Associate': 5}
IC = (5, 'Individual contributor')

FUNCTIONS = [  # first match wins, so order matters
    ('Pre-Construction & Cost',        r"pre-?construction|precon\b|estimat|cost\b|cost |quantity survey|commercial manager|bid\b|proposal"),
    ('Energy & Utilities',             r"energy|power\b|utilit|grid|substation|renewable|electrical infrastructure"),
    ('Development & Real Estate',      r"(?<!business )(?<!corporate )development|real estate|\bland\b|site selection|site acquisition|acquisition|entitlement|negotiator|origination|zoning|permitting|expansion"),
    ('Sales & Leasing',                r"sales|leasing|account|business development|commercial|revenue|customer|channel|partnership|go-to-market|marketing|client"),
    ('Strategy, Finance & Investment', r"corporate development|m&a|mergers|finance|financial|investment|investor|capital markets|asset management|treasury|fp&a|strategy|strategic planning|portfolio"),
    ('Design & Engineering',           r"design|engineer|architect|technical|\bmep\b|electrical|mechanical"),
    ('Construction & Delivery',        r"construction|project|program|delivery|superintendent|build|site\b|field|contracts?\b|scheduler|controls"),
    ('Operations & Facilities',        r"operation|facilit|maintenance|critical environment|data center manager|site reliability"),
    ('Procurement & Supply Chain',     r"procurement|supply chain|sourcing|purchasing|vendor"),
    ('Legal, People & Support',        r"legal|counsel|\bhr\b|human resources|people|talent|recruit|compliance|administration|communications|sustainability|esg|safety|ehs"),
]
EXEC_ONLY = re.compile(r"^(country managing director.*|chief (executive|operating|financial|strategy|revenue|commercial|development|investment|technology|information|growth|legal|people|business|product|marketing) officer.*|c[eoft]o|president|co-?founder.*|founder.*|managing director.*|general manager.*|country manager.*|owner.*|executive chairman.*|chairman.*)$")

def seniority_for(p):
    t = (p.get('current_title') or '').lower()
    cw = SENIORITY_FROM_CW.get(p.get('seniority'))
    if cw is not None: return cw, [l for r,l,_ in SENIORITY if r == cw][0] if cw < 5 else IC[1], 'clockwork'
    for rank, label, rx in SENIORITY:
        if re.search(rx, t): return rank, label, 'title'
    return IC[0], IC[1], 'title'

DEPT_FALLBACK = {'Sales': 'Sales & Leasing', 'Pre-Construction': 'Pre-Construction & Cost', 'Development': 'Development & Real Estate',
                 'Construction': 'Construction & Delivery', 'Energy & Utilities': 'Energy & Utilities'}
def function_for(p):
    """-> (function, source). Title first; a generic title ("Director") falls back
    to the Ward Search mapping list the person was filed under."""
    t = (p.get('current_title') or '').lower().replace('–','-').strip()
    if t:
        if EXEC_ONLY.match(t): return 'Executive leadership', 'title'
        for name, rx in FUNCTIONS:
            if re.search(rx, t): return name, 'title'
    fb = DEPT_FALLBACK.get(p.get('department'))
    return (fb, 'mapping list') if fb else ('Unclassified', 'title')

DATES = r"(?P<start>\d{1,2}/\d{4}|\d{4}|\?) to (?P<end>present|\d{1,2}/\d{4}|\d{4}|\?)"
ENTRY_PATTERNS = [
    re.compile(r"^(?P<title>.+?) (?:at|@) (?P<company>.+?), " + DATES + "$"),
    re.compile(r"^(?P<company>[^,]+), " + DATES + "$"),           # no title
    re.compile(r"^(?P<title>.+?) (?:at|@) (?P<company>.+?)$"),    # no dates
]
def parse_career(s):
    out = []
    for chunk in re.split(r";\s+|\s\|\s", s or ''):
        chunk = chunk.strip()
        if not chunk: continue
        for rx in ENTRY_PATTERNS:
            m = rx.match(chunk)
            if m:
                d = {k: v for k, v in m.groupdict().items() if v}
                d['current'] = d.get('end') == 'present'
                out.append(d); break
        else:
            out.append({'raw': chunk})
    return out

files = sorted(glob.glob(os.path.join(REPO, 'data/people/*.json')))
fn_c, sn_c, unparsed = collections.Counter(), collections.Counter(), 0
sample = collections.defaultdict(list)
for path in files:
    p = json.load(open(path))
    rank, label, src = seniority_for(p)
    fn, fn_src = function_for(p)
    career = parse_career(p.get('career_history'))
    unparsed += sum(1 for c in career if 'raw' in c)
    fn_c[fn] += 1; sn_c[label] += 1
    if len(sample[fn]) < 6: sample[fn].append(p.get('current_title'))
    if APPLY:
        p['function'] = fn
        p['function_source'] = fn_src
        p['seniority_rank'] = rank
        p['seniority_label'] = label
        if not p.get('seniority'): p['seniority_source'] = 'derived from title'
        p['career'] = career
        json.dump(p, open(path, 'w'), indent=2, ensure_ascii=False); open(path,'a').write('\n')

print('functions:', fn_c.most_common()); print('seniority:', sn_c.most_common()); print('unparsed career entries:', unparsed)
for fn, ts in sample.items(): print(f'  {fn}: {ts}')
print('APPLIED' if APPLY else 'dry run')
