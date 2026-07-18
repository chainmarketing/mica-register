"""
Build a clean MiCA dashboard directly from master_register.csv.
Same architecture as the global dashboard — no diverging template.
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

def cs_clean(cs):
    if cs in ("Active Customer", "Customer (status unset)"): return "Customer"
    return cs or "Not in Salesforce"

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
        "wd":r["registration_status"]=="Withdrawn", "pd":r["registration_status"]=="Pending",
        "et":r["entity_type"],
        "mj":int(r["multi_jurisdiction_count"]) if r["multi_jurisdiction_count"] else 1,
        "cs":cs_clean(str(r.get("chainalysis_client_status",""))),
        "ao":str(r.get("sf_account_owner","")), "bc":str(r.get("sf_billing_country","")),
        "sfid":str(r.get("sf_account_id","")), "abs":str(r.get("abs_stage","")),
    })

n_data = [{"n":r["legal_name"],"co":r["home_country"],"ca":r["regulator"],
           "ws":str(r.get("website","")),"cn":r["commercial_name"]}
          for _, r in ncasp.iterrows()]

d_json = json.dumps(data, ensure_ascii=False, separators=(",",":"))
n_json = json.dumps(n_data, ensure_ascii=False, separators=(",",":"))

authorised = [r for r in data if r["st"]=="Authorised"]
customers  = [r for r in data if r["cs"]=="Customer"]
targets    = [r for r in data if r["cs"] in ("Not in Salesforce","Churned Customer")]
countries  = sorted(set(r["co"] for r in data))
cc_counts  = {}
for r in data:
    if not r["wd"]: cc_counts[r["co"]] = cc_counts.get(r["co"],0)+1
top3  = ", ".join(f"{c} ({n})" for c,n in sorted(cc_counts.items(),key=lambda x:-x[1])[:3])
pct   = f"{len(customers)/max(len(authorised),1)*100:.0f}"
today = date.today().isoformat()

print(f"D: {len(data)} | N: {len(n_data)} | Customers: {len(customers)} ({pct}%) | Targets: {len(targets)}")

# Read HTML template
with open("mica_clean_template.html") as f:
    html = f.read()

# Inject data
def inject_array(html, varname, json_str):
    start = html.index(f"const {varname}=")
    bracket = html.index("[", start)
    depth, i = 0, bracket
    while i < len(html):
        if html[i] == "[": depth += 1
        elif html[i] == "]":
            depth -= 1
            if depth == 0: break
        i += 1
    return html[:start] + f"const {varname}={json_str}" + html[i+1:]

html = inject_array(html, "D", d_json)
html = inject_array(html, "N", n_json)

# Update stats
html = re.sub(r"<!-- ENTITIES -->", str(len(data)), html)
html = re.sub(r"<!-- AUTHORISED -->", str(len(authorised)), html)
html = re.sub(r"<!-- CUSTOMERS -->", str(len(customers)), html)
html = re.sub(r"<!-- PCT -->", pct, html)
html = re.sub(r"<!-- TARGETS -->", str(len(targets)), html)
html = re.sub(r"<!-- COUNTRIES -->", str(len(countries)), html)
html = re.sub(r"<!-- NC -->", str(len(n_data)), html)
html = re.sub(r"<!-- TOP3 -->", top3, html)
html = re.sub(r"<!-- TODAY -->", today, html)
html = re.sub(r"<!-- EMT -->", str(len([r for r in data if r["rt"]=="EMT Issuer"])), html)

with open("mica-register-dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Built: mica-register-dashboard.html ({len(html):,} chars)")
