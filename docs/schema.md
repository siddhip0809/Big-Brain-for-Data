# Schema (plain-English data dictionary)

This describes the "shape" of every entry in the brain. You will never need
to write this format by hand — this is a reference for what information
Claude captures for each type of thing, so you can sanity-check it's
capturing what matters to you.

## Node types (the "things")

Every node lives in its own file, named `<id>.json`, where `<id>` is a
short lowercase, hyphenated slug (e.g. `equinix`, `jane-doe`,
`blackstone-infrastructure-partners`). This id is how relationships refer
to it.

Every node also carries these common fields, regardless of type:
- `id` — the slug used to refer to this node elsewhere
- `type` — `company`, `person`, `investor`, or `search`
- `name` — the display name
- `notes` — free-text notes
- `sources` — list of where this info came from (a URL, "told by Siddhi
  on 2026-09-04," a filename in `sources/`, etc.)
- `last_updated` — date this entry was last changed

### `company` (in `data/companies/`)
- `aliases` — other names it's known by
- `industry_role` — e.g. "colocation operator," "hyperscale builder,"
  "cooling technology vendor," "power infrastructure provider"
- `headquarters`
- `founded` — year
- `website`
- `description` — short summary of what they do
- `facilities` — list of known data center sites (name, location, size)
- `financials` — anything known (revenue, valuation, funding raised)
- `tags` — free-form labels for filtering (e.g. "hyperscale," "colocation,"
  "liquid-cooling")
- `roles` — the list of industry roles the company plays, and the single
  source of truth for how the 3D atlas colours it. One or more of:
  `hyperscaler`, `neocloud`, `cryptomining`, `developer_operator` (the
  data-center tiers), and `energy_developer`, `general_contractor`,
  `civil_land_engineering`, `real_estate_developer` (label "Real estate & industrial developer" — one tier for Siddhi's Cold Storage & Industrial Developers and Real Estate Development USA lists; the two were merged 2026-09-09) (adjacent
  industries, imported from Siddhi's curated lists 2026-09-05). A company
  on several lists holds several roles — AECOM is a civil/land engineer, an
  industrial developer *and* a general contractor — and the atlas draws it
  as a multi-colour node. The first role in tier order is its primary one.
- `parent_industry` — WHY the company is in the data-center business:
  `pure_play` (data centers are its own dedicated business — the
  direct-tap recruiting pool) or `real_estate` / `energy_utilities` /
  `telecom` / `construction_engineering` / `diversified_conglomerate`
  (data centers are one arm of a bigger business — check what a
  candidate there actually works on)
- `linkedin`, `headcount` — from Siddhi's lists where available
  (headcount is the LinkedIn band, e.g. "1,001-5,000")
- `hyperscale_focus` — "Primary Focus" / "Secondary Focus" from the Data
  Centre Developer list, when set
- `capacity_mw` — known MW by region from the Data Centre Developer list,
  e.g. `{"north_america": {"total_mw": 4615, "early_stage_mw": 784}, ...}`
  (regions: `north_america`, `emea`, `apac`, `south_america`)
- `dc_exposure_level` — for adjacent-industry companies: Siddhi's own
  read of how much data-center work they actually do ("High" / "Medium" /
  "Low", or "Relevant" / "Not relevant" for energy developers)
- `ownership` — public / private / PE or infra-fund owned / subsidiary of a
  listed group / joint venture / state-owned. **Not yet populated on any
  record**: the brain has never held it. `scripts/build_gap_list.py` produces
  the sheet that collects it, so the field is defined here first and fills up
  as that sheet comes back. `owned_by` carries the ticker, parent or fund
  alongside it, and `ownership_source` the URL or "told by Siddhi on <date>".
- `source_lists` — which of Siddhi's curated lists the company came from
- `list_attributes` — every other column from those lists, kept verbatim
  per list (scope, noise category, energy mix, has-internal-dev-team, …) so
  nothing typed into the sheets is lost

### `person` (in `data/people/`)
- `current_title`
- `current_company` — employer name as plain text (always present when known)
- `current_company_id` — id of a `company` node for that employer, **only
  set when that employer is itself tracked as a company node** (e.g. a
  classified data-center operator/developer/hyperscaler); `null` otherwise
  even though `current_company` still names them
- `department` — the Ward Search lens: which Long Term Mapping list or
  search sourced them (`Sales`, `Pre-Construction`, `Development`,
  `Construction`, `Energy & Utilities`). Not the company's own org.
- `function` — the **company department their current title belongs to**,
  derived 2026-09-08 from title keywords: `Executive leadership`,
  `Development & Real Estate`, `Sales & Leasing`, `Pre-Construction & Cost`,
  `Construction & Delivery`, `Energy & Utilities`, `Design & Engineering`,
  `Strategy, Finance & Investment`, `Operations & Facilities`,
  `Procurement & Supply Chain`, `Legal, People & Support`, or
  `Unclassified`. `function_source` says whether it came from the `title`
  or fell back to the `mapping list` (generic titles like "Director").
  This is what the atlas org chart groups by.
- `seniority` — Clockwork's own level where it had one (`CXO`, `Senior
  Vice President`, `Vice President`, `Director`, `Manager`, `Associate`);
  `seniority_rank` (0 = C-suite/founder … 5 = individual contributor) and
  `seniority_label` are always filled, from Clockwork's value when present
  and otherwise from the title (`seniority_source: "derived from title"`).
  "Most senior" in the org chart means most senior *among the people we
  have mapped*, not necessarily the real head of that department.
- `career_history` — the raw Clockwork string ("Title at Company, 1/2020
  to present; …"); `career` is the same parsed into a list of
  `{title, company, start, end, current}` entries (a fragment that could
  not be parsed is kept as `{raw}`). Past employers in the org chart come
  from the non-current entries.
- `location` — Clockwork's free text, kept verbatim. `location_norm` is
  the cleaned version: `{city, region, country, group}`, where `group` is
  the US state for US locations and the country elsewhere (so "London,
  England" and "London, England, United Kingdom" both land under United
  Kingdom). Typos and metro-area strings are mapped in
  `scripts/enrich_people.py`.
- `linkedin`
- `do_not_contact`, `pipeline` (search/stage/rank/date per Clockwork
  candidacy), `industry_segment`
- `assessment` — **Ward Search's own judgement, imported from Clockwork
  2026-09-09, not a researched fact.** Holds `skills` (twelve named
  specialisms — development site acquisition, permitting & entitlements,
  financial modelling, pre-con estimating & cost control, project
  scheduling, sales selling and leasing, energy ESA negotiation,
  interconnection & transmission negotiation, transmission engineering,
  water WSA negotiation and engineering — each `"High Confidence"` or
  `"Low Confidence"`), `top_tier` (the functions Ward rates this person
  top tier in), `tenure` (Good / Average / Poor / Recent Move),
  `rating` (1-4; Clockwork's 0 means unrated and is dropped),
  `spoken_with_before`, `hyperscaler_equivalent_seniority` (Ward's
  title-equivalence assumption between hyperscalers and developers),
  plus `source` and a `note` restating that it is judgement.
- `education`, `biography` — from the same exports.
- `assessment.under_represented_group` — Clockwork's column, imported
  2026-09-09 at Siddhi's instruction for diverse-slate reporting (Yes 488,
  No 1,156, Not Apparent 52). **It is Ward's own observation, not
  self-declared by the candidate** — Clockwork's own "Not Apparent" value
  makes that explicit — so treat it as slate-composition data for internal
  use, not as a fact about a person and not for anything shown to a client
  or the candidate. The atlas shows it as an aggregate per company and org
  chart, with a per-person marker.
- `record_grade` — `"directory"` on profiles from the 2026-09-09 bulk
  export (name, title, employer, LinkedIn only; unverified). Absent on the
  Clockwork-sourced records, which carry career history, location and
  pipeline. The atlas badges directory profiles and counts them separately.
- **Never stored:** email, phone, or compensation — those stay in
  Clockwork only.

### `investor` (in `data/investors/`)
- `investor_type` — e.g. "private equity," "venture capital,"
  "infrastructure fund," "sovereign wealth fund," "family office"
- `hq`
- `aum` — assets under management, if known
- `investments` — list of company ids they've backed
- `notable_deals` — free text on specific deals
- `contacts` — list of person ids (their people we know)

Most investor records were populated from web research (not Clockwork),
so treat `investments` here as a research finding, not a verified fact.
The `invested_in` relationship for each one (see below) carries the real
detail: a `confidence` (`high`/`medium`/`medium-high`/`n/a`), a `detail`
summarizing the deal, and `sources` (URLs). Anything below `high` came
from a single source or secondary reporting rather than an official
announcement — worth independent confirmation before relying on it.

### `search` (in `data/searches/`)

One file per Ward Search assignment, pulled from Clockwork (the firm's
search database) rather than hand-typed. This is the record of work Ward
has actually done: who the client was, what the role was, who was in the
pipeline and how far each person got.

- `id` — the Clockwork project id (a UUID). The **filename** is the slug
  used in relationships, e.g. `data/searches/2412c-svp-operations.json`
  is referred to as `search:2412c-svp-operations`.
- `name` — the search name as Ward writes it, usually a job code plus the
  role, e.g. "2412C SVP Operations"
- `client_company` — the client's name as Clockwork holds it
- `client_company_id` — the matching company node in this brain, or
  `null` where the client isn't tracked here yet (8 of 90)
- `status` — `active`, `on_hold`, `pitch`, or `closed`
- `project_type` — Retained, Long Term Mapping, etc.
- `started_at`, `closed_at` — dates
- `closing_reason` — why it ended (Placement, Client Cancelled …)
- `strategy`, `job_description`, `job_requirements` — the brief as
  written in Clockwork, or `null` where none was recorded
- `placement` — the person who got the job (`person`, `person_id`,
  `title`, `start_date`), or `null`
- `pipeline` — the candidates, each with `person`,
  `clockwork_person_id`, `brain_person_id` (or `null` if that person
  isn't a node here), `status` (the Clockwork status name),
  `category` (a coarse grouping: `active`, `placed`, `out-withdrew`,
  `out-client_rejected` …), `rank` (Clockwork's own ordering of how far
  along a status is) and `updated_at`
- `counts` — `pipeline`, `placed`, `active`, `out`
- `pipeline_not_pulled` — present on 38 searches whose pipelines are large
  mapping pools, carrying `clockwork_candidacy_total` (10,855 candidacies
  in total) and the reason they were not paged through on the first pull

**What is deliberately not here.** Compensation and fee data exist in
Clockwork and were not pulled. One confidential search was skipped
entirely — no file, no client name, no candidates — because this
repository syncs to GitHub. Only pipeline entries whose status rank is
100 or above (i.e. a real candidacy, not a raw long-list touch) were
written.

## Relationships (the "connections")

All relationships live together in one file: `data/relationships.json`.
Each entry looks like:

```json
{
  "from": "person:jane-doe",
  "to": "company:example-datacentral",
  "type": "works_at",
  "detail": "VP of Engineering",
  "since": "2021",
  "sources": ["told by Siddhi on 2026-09-04"],
  "last_updated": "2026-09-04"
}
```

Common relationship `type` values (not a fixed list — new ones can be
added any time):
- `works_at` — person → company (their actual current employer; only
  created when that employer is itself a tracked company node)
- `candidate_for` — person → the search they're a candidate for (a
  recruiting relationship, separate from `works_at`). Two generations of
  these exist side by side: the 1,063 older edges point at a **company**
  (`to: "company:goodman"`) because they were imported from Siddhi's
  spreadsheets before searches were nodes; the 556 added on 2026-09-10
  point at a **search** (`to: "search:2412c-svp-operations"`) and carry
  the candidate's Clockwork status in `detail`, so you can see not just
  that someone was considered but how far they got.
- `invested_in` — investor → company
- `board_member_of` — person → company or investor
- `acquired` — acquirer → target (company → company, or investor →
  investor, e.g. Blue Owl Capital → IPI Partners). Carries a `status`
  ("completed", "announced", "announced; reportedly rejected", "minority
  stake") and the deal detail/value in `detail`. A company being acquired
  is a hiring — or layoff — signal, which is why these are tracked.
- `tenant_of` — tenant → host/landlord (company → company): who leases
  data-center capacity from whom, e.g. AWS → Cipher Mining (300MW, 15 yr),
  CoreWeave → Galaxy Digital (Helios, ~526MW). `detail` holds MW, term,
  and value where known. Shows real demand-side relationships, separate
  from who *owns* a company.
- `jv_partner` — company ↔ company joint venture on a specific campus or
  platform (direction is not meaningful), e.g. Crusoe ↔ Lancium (Abilene).
- `contractor_for` — builder/engineer → data-center client (company →
  company): a general contractor, EPC, civil/land engineer, MEP engineer
  of record or commissioning firm working on a named campus for an
  operator or hyperscaler, e.g. Holder Construction → Google. `detail`
  names the projects; `status` is completed / under construction /
  announced / ongoing programme. Added 2026-09-08 to connect the
  adjacent-industry zone to the data-center core.
- `supplies_power_to` — energy company → data-center company: PPAs,
  behind-the-meter or co-located generation, nuclear restarts contracted
  to a hyperscaler, utility large-load agreements. `detail` carries MW /
  GW, technology, term and year; `status` is operating / contracted /
  announced / MOU. For a headhunter this is the energy-negotiation and
  utilities hiring map.
- `site_partner` — industrial / real-estate developer ↔ data-center
  company: powered-land sales, build-to-suit development, campus JVs.
- `partnered_with` — company → company (looser commercial partnership)
- `competitor_of` — company → company

`acquired`, `tenant_of`, `jv_partner`, `contractor_for`,
`supplies_power_to` and `site_partner` edges are drawn in the 3D atlas as
their own line colours (amber, white, green, sky blue, red, pink)
alongside violet investor backing, and appear in a node's focus ring and
detail panel. The dash pattern within a colour encodes status/confidence
(solid = done or confirmed, dashed = announced or single-source, dotted =
terminated). The three adjacent-industry types run between the two
zones of the atlas and deliberately carry no layout spring, so the zones
stay apart and the line alone shows the connection. Each carries a
`confidence` (`high` / `medium`) like `invested_in` does — anything below
`high` came from press reporting rather than an official announcement.
- `contact_at` — person → investor (a person we know at a fund)

Every researched relationship can also carry **`verified_by`** — `{research_team, siddhi, ward}`
with a date for each check that has been made. The flags are set by clicking in the atlas
(stored in the page's shared database) and pulled back into this file with
`scripts/pull_verifications.py`; "ward" means confirmed by Ward Search as a firm.

Keeping relationships in one file (instead of scattered inside each node)
makes it easy to answer questions like "show me everything connected to
Company X" or "which investors and people overlap across these three
companies" by scanning one place.
