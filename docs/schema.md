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
- `type` — `company`, `person`, or `investor`
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

### `person` (in `data/people/`)
- `current_title`
- `current_company` — id of a company node, if known
- `past_companies` — list of company ids or names
- `location`
- `linkedin`
- `email` / `phone` — if known and appropriate to store
- `expertise_tags` — e.g. "power engineering," "site selection," "M&A"
- `clockwork_id` — cross-reference to the Clockwork CRM record, if pulled
  from there

### `investor` (in `data/investors/`)
- `investor_type` — e.g. "private equity," "venture capital,"
  "infrastructure fund," "sovereign wealth fund," "family office"
- `hq`
- `aum` — assets under management, if known
- `investments` — list of company ids they've backed
- `notable_deals` — free text on specific deals
- `contacts` — list of person ids (their people we know)

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
- `works_at` — person → company
- `invested_in` — investor → company
- `board_member_of` — person → company or investor
- `acquired` — company → company
- `partnered_with` — company → company
- `competitor_of` — company → company
- `contact_at` — person → investor (a person we know at a fund)

Keeping relationships in one file (instead of scattered inside each node)
makes it easy to answer questions like "show me everything connected to
Company X" or "which investors and people overlap across these three
companies" by scanning one place.
