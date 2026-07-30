"""
Build the PUBLIC MiCA dashboard — register data only, no CRM overlay.
Safe to host publicly. No customer status, no AE names, no SF data.

Full-fat version with CRM: mica-dashboard-full.html
Output: mica-register-dashboard.html
"""
import pandas as pd, json, re
from datetime import datetime, date

master = pd.read_csv("master_register.csv").fillna("")
mica   = master[master["register_source"] == "ESMA_MICA"].copy()
ncasp  = master[master["register_source"] == "ESMA_MICA_NONCOMPLIANT"]

SVC_MAP = {
    "Custody & administration":("a","Custody"),
    "Trading platform operation":("b","Operating a trading platform"),
    "Exchange crypto-to-fiat":("c","Exchange (fiat)"),
    "Exchange crypto-to-crypto":("d","Exchange (crypto-to-crypto)"),
    "Order execution":("e","Order execution"),
    "Placing of crypto-assets":("f","Placing"),
    "Reception & transmission of orders":("g","Reception & transmission"),
    "Advice on crypto-assets":("h","Advice"),
    "Portfolio management":("i","Portfolio management"),
    "Transfer services":("j","Transfer services"),
    "EMT Issuer (Electronic money institution)":("emt","EMT Issuer"),
    "EMT Issuer (Electronic money Institution)":("emt","EMT Issuer"),
    "EMT Issuer (Credit Institution)":("emt_ci","EMT Issuer (Credit)"),
}

def parse_sk(d):
    if not d: return "9999-99-99"
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(str(d).strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return "9999-99-99"

# Register fields ONLY — no CRM
data = []
for _, r in mica.iterrows():
    svcs    = [s.strip() for s in str(r["services"]).split(";") if s.strip()]
    s_codes = [SVC_MAP[s][0] for s in svcs if s in SVC_MAP]
    s_labels= [SVC_MAP[s][1] for s in svcs if s in SVC_MAP]
    data.append({
        "n":r["legal_name"], "cn":r["commercial_name"], "co":r["home_country"],
        "cc":r["home_country_code"], "ca":r["regulator"], "w":r["website"],
        "d":r["registration_date"], "sk":parse_sk(r["registration_date"]),
        "s":s_codes, "sl":s_labels,
        "pc":int(r["passporting_count"]) if r["passporting_count"] else 0,
        "lei":r["lei"], "rt":r["licence_type"], "dr":str(r["dual_registered"]),
        "tw":r["town"], "st":r["registration_status"],
        "wd":r["registration_status"] == "Withdrawn",
        "pd":r["registration_status"] == "Pending",
        "et":r["entity_type"],
        "mj":int(r["multi_jurisdiction_count"]) if r["multi_jurisdiction_count"] else 1,
        "bc":r["home_country"],  # use home country not SF billing country
    })

n_data = [{"n":r["legal_name"], "co":r["home_country"], "ca":r["regulator"],
           "ws":str(r.get("website","")), "cn":r["commercial_name"]}
          for _, r in ncasp.iterrows()]

d_json = json.dumps(data, ensure_ascii=False, separators=(",",":"))
n_json = json.dumps(n_data, ensure_ascii=False, separators=(",",":"))

authorised = [r for r in data if r["st"] == "Authorised"]
emt        = [r for r in data if r["rt"] == "EMT Issuer"]
dual       = [r for r in data if "+" in r["rt"]]
countries  = sorted(set(r["co"] for r in data))
casps      = [r for r in data if "CASP" in r["rt"]]
cc_counts  = {}
for r in data:
    if not r["wd"]: cc_counts[r["co"]] = cc_counts.get(r["co"], 0) + 1
top3  = ", ".join(f"{c} ({n})" for c, n in sorted(cc_counts.items(), key=lambda x: -x[1])[:3])
today = date.today().isoformat()
multi = [r for r in data if r["mj"] > 1]

print(f"Public dashboard: {len(data)} entities, {len(authorised)} authorised, {len(countries)} countries")

with open("mica_public_template.html") as f:
    html = f.read()

def inject(html, varname, json_str):
    s = html.index(f"const {varname}=")
    b = html.index("[", s)
    depth, i = 0, b
    while i < len(html):
        if html[i] == "[": depth += 1
        elif html[i] == "]":
            depth -= 1
            if depth == 0: break
        i += 1
    return html[:s] + f"const {varname}={json_str}" + html[i+1:]

html = inject(html, "D", d_json)
html = inject(html, "N", n_json)

replacements = {
    "<!-- ENTITIES -->":  str(len(data)),
    "<!-- AUTHORISED -->":str(len(authorised)),
    "<!-- WITHDRAWN -->": str(len([r for r in data if r["wd"]])),
    "<!-- CASPS -->":     str(len(casps)),
    "<!-- EMT -->":       str(len(emt)),
    "<!-- DUAL -->":      str(len(dual)),
    "<!-- COUNTRIES -->": str(len(countries)),
    "<!-- NC -->":        str(len(n_data)),
    "<!-- TOP3 -->":      top3,
    "<!-- TODAY -->":     today,
    "<!-- MULTI -->":     str(len(multi)),
}
for k, v in replacements.items():
    html = html.replace(k, v)

with open("mica-register-dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Built: mica-register-dashboard.html ({len(html):,} chars)")
