#!/usr/bin/env python3
"""Beriger datasættet med felter EA's ratings-API ikke udfylder.

EA's drop-api leverer i FC 27-droppet tomme værdier for `height`, `weight` og
har slet ikke `accelerateType`. FUT.GG's definition-endpoint er åbent (ingen
nøgle, ingen login) og har alle tre:

    https://www.fut.gg/api/fut/players/v2/27/definitions/?overall__gte=85

Bemærk: FUT.GG's PRIS-endpoints ligger bevidst bag Cloudflares JS-challenge.
Dette script rører dem ikke — kun det åbne definition-endpoint.

Begrænsninger vi arbejder omkring:
  * sidestørrelsen er låst til 30 (limit/pageSize/perPage ignoreres)
  * hver forespørgsel er hårdt loftet ved 10.000 resultater
  * `total` i svaret er det reelle antal, når det er under loftet

Derfor deles hentningen i overall-bånd, som hver holder sig under loftet.
Målt dækning: 20.710 spillere mod EA's 20.689.

    python3 enrich_futgg.py

Skriver futgg_enrichment.json ved siden af scriptet: {eaId: {...}}.
Kørslen kan afbrydes og genoptages — færdige bånd caches i raw_futgg/.
"""
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

GAME = 27
BASE = f"https://www.fut.gg/api/fut/players/v2/{GAME}/definitions/"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "raw_futgg")
OUT = os.path.join(HERE, "futgg_enrichment.json")

# Beskeden samtidighed: endpointet er åbent, men vi henter ~690 sider og vil
# ikke belaste en gratistjeneste unødigt.
WORKERS = 5
PAGE_SIZE = 30
HARD_CAP = 10000

HEADERS = {
    "user-agent": "Mozilla/5.0 (compatible; fut27/1.0; +https://github.com/mikkelefrost/fut27)",
    "accept": "application/json",
    # identity: uden den svarer endpointet af og til med en krop vi ikke kan pakke ud
    "accept-encoding": "identity",
}

# Bånd valgt så hvert enkelt ligger godt under 10.000-loftet. Kontrolleres i
# fetch_band() — vokser FUT.GG's database, fejler den hellere end at afkorte.
BANDS = [
    (0, 55), (56, 62), (63, 67), (68, 71), (72, 74),
    (75, 77), (78, 80), (81, 84), (85, 99),
]

# Kun de felter EA mangler. Vi kopierer ikke ratings eller attributter herfra —
# EA er kilden til dem, og to kilder til samme tal ville bare kunne modsige
# hinanden.
WANTED = ("height", "weight", "accelerateType")


def get(url, tries=5):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:      # forbi sidste side
                return {"data": []}
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def fetch_band(band):
    lo, hi = band
    path = os.path.join(CACHE, f"{lo}-{hi}.json")
    if os.path.exists(path) and os.path.getsize(path) > 2:
        with open(path) as f:
            return band, json.load(f)

    q = f"overall__gte={lo}&overall__lte={hi}"
    head = get(f"{BASE}?{q}")
    total = head.get("total") or 0
    if total >= HARD_CAP:
        raise SystemExit(
            f"AFBRUDT: båndet {lo}-{hi} har {total} spillere og rammer FUT.GG's "
            f"loft på {HARD_CAP}. Del BANDS finere op i enrich_futgg.py, "
            f"ellers mangler der spillere i beriget data."
        )

    pages = max(1, -(-total // PAGE_SIZE))
    rows = {}
    for page in range(1, pages + 1):
        data = get(f"{BASE}?{q}&page={page}")
        items = data.get("data") or []
        if not items:
            break
        for it in items:
            eid = it.get("eaId")
            if eid is None:
                continue
            vals = {k: it.get(k) for k in WANTED if it.get(k) not in (None, "", 0)}
            if vals:
                rows[str(eid)] = vals

    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f)
    print(f"  overall {lo:2}-{hi:2}: {total:6} spillere, {pages:3} sider -> {len(rows)} berigede",
          flush=True)
    return band, rows


if __name__ == "__main__":
    print(f"beriger fra FUT.GG (game {GAME}) — {len(BANDS)} bånd")
    merged = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for _band, rows in pool.map(fetch_band, BANDS):
            merged.update(rows)

    with open(OUT, "w") as f:
        json.dump(merged, f, separators=(",", ":"))

    have = {k: sum(1 for v in merged.values() if v.get(k)) for k in WANTED}
    print(f"\nskrev {OUT}: {len(merged)} spillere")
    for k, n in have.items():
        print(f"  {k:16} {n}")
