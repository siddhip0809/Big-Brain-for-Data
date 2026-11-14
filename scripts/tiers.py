"""The tiers a company can sit in -- the one definition every script and the atlas read.

Order matters: it is the legend order, and the first tier a company holds in this order is
its primary tier (its colour and its place on the map). Adjacent tiers are the industries
around the data-center core; they start switched off on the map. Add a tier here and
nowhere else; docs/schema.md describes what each one means.

Colours: the first ten were validated as a colour-vision-safe set (see the builder's
history); the eight added on 2026-11-12 came from the published atlas and have not been
through that check.
"""
TIERS = {
    "hyperscaler":              {"name": "Hyperscaler",                                "color": "#d97706", "adjacent": False},
    "neocloud":                 {"name": "NeoCloud / AI Infra",                        "color": "#16a34a", "adjacent": False},
    "cryptomining":             {"name": "Cryptomining pivot",                         "color": "#db2777", "adjacent": False},
    "developer_operator":       {"name": "Data Center Developer / Operator",           "color": "#0891b2", "adjacent": False},
    "ai_lab":                   {"name": "AI labs (own compute)",                      "color": "#65a30d", "adjacent": False},
    "energy_developer":         {"name": "Energy developer / utility",                 "color": "#b45309", "adjacent": True},
    "general_contractor":       {"name": "General contractor",                         "color": "#2563eb", "adjacent": True},
    "civil_land_engineering":   {"name": "Civil / land engineering",                   "color": "#dc2626", "adjacent": True},
    "real_estate_developer":    {"name": "Real estate & industrial developer",         "color": "#4d7c0f", "adjacent": True},
    "consultancy":              {"name": "Consultancy (cost, PM, power, design)",      "color": "#7c2d12", "adjacent": True},
    "equipment_supply":         {"name": "Equipment & supply chain",                   "color": "#475569", "adjacent": True},
    "property_advisory":        {"name": "Brokers & property advisory",                "color": "#0f766e", "adjacent": True},
    "planning_grid":            {"name": "Planning, permitting & grid",                "color": "#ca8a04", "adjacent": True},
    "mission_critical_build":   {"name": "Fabs, gigafactories & pharma",               "color": "#6d28d9", "adjacent": True},
    "capital_projects":         {"name": "Capital-projects owners",                    "color": "#1e3a8a", "adjacent": True},
    "telecom_network":          {"name": "Telecom, fibre & towers",                    "color": "#0284c7", "adjacent": True},
    "dc_operations":            {"name": "DC operations & FM",                         "color": "#be123c", "adjacent": True},
    "investor":                 {"name": "Investor",                                   "color": "#9333ea", "adjacent": False},
}
ROLES = [t for t in TIERS if t != "investor"]          # what a company's roles may hold, in priority order
ADJACENT = {t for t, d in TIERS.items() if d["adjacent"]}
CORE = tuple(t for t in ROLES if t not in ADJACENT)
LABEL = {t: d["name"] for t, d in TIERS.items()}


def primary_role(roles):
    for r in ROLES:
        if r in roles: return r
    return roles[0] if roles else "developer_operator"
