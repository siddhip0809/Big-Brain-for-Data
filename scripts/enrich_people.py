#!/usr/bin/env python3
"""Derive, for every record in data/people/:
  - `function`        the company department the current title belongs to
  - `seniority_rank`  0 = C-suite/founder ... 5 = individual contributor
                      (Clockwork's own `seniority` wins when present)
  - `career`          the raw career_history string parsed into entries
  - `location_norm`   {city, region, country, group} from the free-text location
                      (group = US state, or country elsewhere -- the org chart's
                      "By location" column)
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

# ---- locations: Clockwork free text -> {city, region, country, group} ----
US_STATES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware',
 'FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana',
 'ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska',
 'NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio',
 'OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas',
 'UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
STATE_NAMES = {v.lower(): v for v in US_STATES.values()}
DC_ALIASES = {'washington dc','dc','washington d.c','washington d.c.','district of columbia','washington, dc'}
# sub-national regions / aliases -> (region, country)
REGIONS = {
 'queensland':('Queensland','Australia'),'western australia':('Western Australia','Australia'),'lisbon':('Lisbon','Portugal'),
 'north rhine-westphalia':('North Rhine-Westphalia','Germany'),'county limerick':('County Limerick','Ireland'),'latium':('Lazio','Italy'),
 'community of madrid':('Madrid','Spain'),'maharashtra':('Maharashtra','India'),'texas metropolitan area':('Texas','United States'),
 'london':('England','United Kingdom'),
 # Clockwork typos
 'califfornia':('California','United States'),'virrginia':('Virginia','United States'),'ohia':('Ohio','United States'),
 'lowa':('Iowa','United States'),'winconsin':('Wisconsin','United States'),'arizon':('Arizona','United States'),
 'england':('England','United Kingdom'),'scotland':('Scotland','United Kingdom'),'wales':('Wales','United Kingdom'),
 'northern ireland':('Northern Ireland','United Kingdom'),'greater london':('England','United Kingdom'),'uk':(None,'United Kingdom'),
 'north holland':('North Holland','Netherlands'),'south holland':('South Holland','Netherlands'),'hessen':('Hesse','Germany'),'hesse':('Hesse','Germany'),
 'bavaria':('Bavaria','Germany'),'county dublin':('County Dublin','Ireland'),'leinster':('Leinster','Ireland'),'ontario':('Ontario','Canada'),
 'quebec':('Quebec','Canada'),'british columbia':('British Columbia','Canada'),'alberta':('Alberta','Canada'),'uae':(None,'United Arab Emirates'),
 'hong kong sar':(None,'Hong Kong'),'hong kong':(None,'Hong Kong'),'lombardy':('Lombardy','Italy'),'vestfold':('Vestfold','Norway'),
 'pirkanmaa':('Pirkanmaa','Finland'),'new south wales':('New South Wales','Australia'),'victoria':('Victoria','Australia'),
 'ile-de-france':('Île-de-France','France'),'île-de-france':('Île-de-France','France'),'catalonia':('Catalonia','Spain'),'madrid':('Madrid','Spain'),
}
COUNTRIES = {c.lower(): c for c in ['United States','United Kingdom','Ireland','Netherlands','France','Germany','Spain','Italy','Norway','Sweden',
 'Denmark','Finland','Switzerland','Austria','Belgium','Poland','Portugal','Romania','Singapore','Japan','India','Australia','Canada','Brazil',
 'Mexico','Indonesia','Malaysia','Thailand','Hong Kong','United Arab Emirates','Saudi Arabia','South Africa','China','Israel','Luxembourg','Greece',
 'Czech Republic','Hungary','Turkey','New Zealand','South Korea','Philippines','Vietnam','Chile','Colombia','Argentina','Nigeria','Kenya','Egypt']}
COUNTRY_ALIASES = {'usa':'United States','us':'United States','u.s.':'United States','uk':'United Kingdom','great britain':'United Kingdom',
 'holland':'Netherlands','the netherlands':'Netherlands','uae':'United Arab Emirates','hong kong sar':'Hong Kong','czechia':'Czech Republic',
 'republic of ireland':'Ireland','korea':'South Korea'}
# metro areas / lone cities -> (city, region, country)
PLACES = {
 'houston':('Houston','Texas','United States'),'phoenix':('Phoenix','Arizona','United States'),'san francisco':('San Francisco','California','United States'),
 'herndon':('Herndon','Virginia','United States'),'gold canyon':('Gold Canyon','Arizona','United States'),'seoul':('Seoul',None,'South Korea'),
 'taiwan':(None,None,'Taiwan'),'greater tokyo area':('Tokyo',None,'Japan'),'greater milwaukee':('Milwaukee','Wisconsin','United States'),
 'greater sacramento':('Sacramento','California','United States'),'las vegas metropolitan area':('Las Vegas','Nevada','United States'),
 'louisville metropolitan area':('Louisville','Kentucky','United States'),'mumbai':('Mumbai','Maharashtra','India'),
 'san francisco bay area':('San Francisco Bay Area','California','United States'),'new york city metropolitan area':('New York City','New York','United States'),
 'greater new york city area':('New York City','New York','United States'),'atlanta metropolitan area':('Atlanta','Georgia','United States'),
 'dallas-fort worth metroplex':('Dallas-Fort Worth','Texas','United States'),'greater chicago area':('Chicago','Illinois','United States'),
 'detroit metropolitan area':('Detroit','Michigan','United States'),'greater minneapolis-st. paul area':('Minneapolis-St. Paul','Minnesota','United States'),
 'greater richmond region':('Richmond','Virginia','United States'),'greater seattle area':('Seattle','Washington','United States'),
 'greater phoenix area':('Phoenix','Arizona','United States'),'denver metropolitan area':('Denver','Colorado','United States'),
 'greater boston':('Boston','Massachusetts','United States'),'washington dc-baltimore area':('Washington','Washington, DC','United States'),
 'greater houston':('Houston','Texas','United States'),'los angeles metropolitan area':('Los Angeles','California','United States'),
 'greater rio de janeiro':('Rio de Janeiro','Rio de Janeiro','Brazil'),'greater paris metropolitan region':('Paris','Île-de-France','France'),
 'greater london':('London','England','United Kingdom'),
 'seattle':('Seattle','Washington','United States'),'frisco':('Frisco','Texas','United States'),'lorton':('Lorton','Virginia','United States'),
 'london':('London','England','United Kingdom'),'oxford':('Oxford','England','United Kingdom'),'dublin':('Dublin','County Dublin','Ireland'),
 'milan':('Milan','Lombardy','Italy'),'nice':('Nice',None,'France'),'marseille':('Marseille',None,'France'),'paris':('Paris','Île-de-France','France'),
 'tokyo':('Tokyo',None,'Japan'),'dubai':('Dubai',None,'United Arab Emirates'),'oslo':('Oslo',None,'Norway'),'jakarta':('Jakarta',None,'Indonesia'),
 'singapore':('Singapore',None,'Singapore'),'hong kong':('Hong Kong',None,'Hong Kong'),'amsterdam':('Amsterdam','North Holland','Netherlands'),
 'frankfurt':('Frankfurt','Hesse','Germany'),'madrid':('Madrid','Madrid','Spain'),'sydney':('Sydney','New South Wales','Australia'),
}
def normalise_location(raw):
    toks = [t.strip() for t in (raw or '').replace(' ,', ',').split(',')]
    toks = [t for t in toks if t and any(ch.isalpha() for ch in t)]
    city = region = country = None
    if not toks: return None
    # whole string or first token is a known place / metro area
    key = ', '.join(toks).lower()
    if key in PLACES or (len(toks) == 1 and toks[0].lower() in PLACES):
        city, region, country = PLACES.get(key) or PLACES[toks[0].lower()]
    else:
        rest = []
        for t in toks:
            tl = t.lower().rstrip('.')
            if tl in DC_ALIASES or t in ('DC',): region = region or 'Washington, DC'; country = 'United States'
            elif t.upper() in US_STATES and (t.isupper() or len(t) == 2): region = region or US_STATES[t.upper()]; country = 'United States'
            elif tl in STATE_NAMES: region = region or STATE_NAMES[tl]; country = 'United States'
            elif tl in REGIONS: r, c = REGIONS[tl]; region = region or r; country = country or c
            elif tl in COUNTRY_ALIASES: country = COUNTRY_ALIASES[tl]
            elif tl in COUNTRIES: country = COUNTRIES[tl]
            else: rest.append(t)
        if rest:
            first = rest[0].lower()
            if first in PLACES:
                c2, r2, k2 = PLACES[first]; city = c2; region = region or r2; country = country or k2
            else:
                city = rest[0]
    if country == 'United States' and region and city and city.lower() == region.lower(): city = None
    if not country and not region and not city: return None
    group = region if country == 'United States' and region else (country or region or city)
    return {'city': city, 'region': region, 'country': country, 'group': group}

def main():
    files = sorted(glob.glob(os.path.join(REPO, 'data/people/*.json')))
    fn_c, sn_c, loc_c, unparsed = collections.Counter(), collections.Counter(), collections.Counter(), 0
    loc_nocountry = []
    sample = collections.defaultdict(list)
    for path in files:
        p = json.load(open(path))
        rank, label, src = seniority_for(p)
        fn, fn_src = function_for(p)
        career = parse_career(p.get('career_history'))
        unparsed += sum(1 for c in career if 'raw' in c)
        loc = normalise_location(p.get('location'))
        loc_c[(loc or {}).get('group')] += 1
        if loc and not loc.get('country'): loc_nocountry.append(p.get('location'))
        fn_c[fn] += 1; sn_c[label] += 1
        if len(sample[fn]) < 6: sample[fn].append(p.get('current_title'))
        if APPLY:
            p['function'] = fn
            p['function_source'] = fn_src
            p['seniority_rank'] = rank
            p['seniority_label'] = label
            if not p.get('seniority'): p['seniority_source'] = 'derived from title'
            p['career'] = career
            p['location_norm'] = loc
            json.dump(p, open(path, 'w'), indent=2, ensure_ascii=False); open(path,'a').write('\n')

    print('functions:', fn_c.most_common()); print('seniority:', sn_c.most_common()); print('unparsed career entries:', unparsed)
    for fn, ts in sample.items(): print(f'  {fn}: {ts}')
    print('location groups:', loc_c.most_common(45))
    print('locations without a country (%d):' % len(loc_nocountry), sorted(set(loc_nocountry))[:60])
    print('APPLIED' if APPLY else 'dry run')


if __name__ == "__main__":
    main()
