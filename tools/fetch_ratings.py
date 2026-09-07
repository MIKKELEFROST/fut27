#!/usr/bin/env python3
"""Henter hele EA SPORTS FC ratings-databasen fra EA's åbne drop-api.

Endpointet kræver hverken API-nøgle eller login, men EA sætter kun
`access-control-allow-origin: https://www.ea.com`, så en browser kan ikke kalde
det direkte. Derfor hentes data her (server-side) og bundles med siden.

VIGTIGT — `drop-referrer`-headeren afgør hvilken årgang man får:

    uden headeren            -> 17.873 spillere, FC 26-ratings (Salah 91 som #1)
    med headeren             -> 20.689 spillere, FC 27-ratings (Mbappé 91 som #1)

Det er samme URL i begge tilfælde; kun headeren skiller. EA's egen ratings-side
(www.ea.com/games/ea-sports-fc/ratings) sætter den, og backenden serverer den
aktuelle årgang til de kald der oplyser den. En forkert værdi i headeren giver
det gamle FC 26-datasæt igen, så den skal matche præcist.

    python3 fetch_ratings.py             # FC 27, både en og da
    python3 fetch_ratings.py en          # FC 27, kun én locale
    python3 fetch_ratings.py --previous  # FC 26 (uden headeren), kun en

Netop fordi headeren giver adgang til begge årgange, kan vi hente dem begge og
regne ratingændringen ud pr. spiller. Det er noget prissiderne ikke viser, fordi
de kun følger ændringer inden for én sæson. `--previous` bruges til det.

Skriver rå API-sider til raw_<locale>/<offset>.json ved siden af scriptet
(raw_prev_en/ for forrige årgang). Allerede hentede sider genbruges, så kørslen
kan afbrydes og genoptages — slet raw_*-mapperne for at tvinge en frisk hentning.
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://drop-api.ea.com/rating/ea-sports-fc"
LIMIT = 100  # API'et afviser limit > 100 med HTTP 400
WORKERS = 6
HERE = os.path.dirname(os.path.abspath(__file__))

# Uden denne header falder API'et tilbage til forrige års database. Se modulets
# docstring. Værdien skal være EA's ratings-side, ikke en vilkårlig URL.
RATINGS_REFERRER = "https://www.ea.com/games/ea-sports-fc/ratings"

UA = "Mozilla/5.0 (fut27 dataset builder)"

HEADERS = {
    "accept": "application/json",
    "user-agent": UA,
    "drop-referrer": RATINGS_REFERRER,
}

# Uden drop-referrer svarer det samme endpoint med forrige årgang.
PREV_HEADERS = {"accept": "application/json", "user-agent": UA}


def get(url, tries=5, headers=None):
    """GET med eksponentiel backoff — EA's edge svarer af og til 5xx."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or HEADERS)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def assert_current_edition():
    """Fejl højlydt hvis drop-referrer holder op med at virke.

    Uden headeren serverer API'et forrige års database. De to svar skal derfor
    være forskellige — er de ens, har EA ændret adfærden, og alt hvad vi henter
    ville stille og roligt være forældet.
    """
    with_hdr = get(f"{BASE}?limit=1&locale=en&_cb=guard1")

    without_hdr = get(f"{BASE}?limit=1&locale=en&_cb=guard2", headers=PREV_HEADERS)

    a, b = with_hdr["totalItems"], without_hdr["totalItems"]
    if a == b:
        raise SystemExit(
            f"AFBRUDT: drop-referrer gør ingen forskel længere (begge svar har "
            f"{a} spillere).\nEA har sandsynligvis ændret API'et. Undersøg hvad "
            f"https://www.ea.com/games/ea-sports-fc/ratings kalder nu, før du "
            f"henter videre — ellers bygger du på forældede ratings."
        )
    print(f"kontrol: med header {a} spillere, uden {b} — headeren virker")
    return a


def fetch_locale(locale, previous=False):
    """Henter én locale. previous=True udelader headeren og giver forrige årgang.

    VIGTIGT: EA's CDN cacher på URL alene — svaret har `cache-control: public,
    s-maxage=600` og INGEN `Vary: drop-referrer`. To kald til samme URL, der kun
    adskiller sig ved headeren, deler altså cache-post, og det andet får det
    førstes årgang tilbage. Derfor bærer hver årgang sin egen `_e`-parameter, så
    de aldrig kan kollidere. Uden den henter --previous glad og gerne FC 27 igen.
    """
    headers = PREV_HEADERS if previous else HEADERS
    edition = "prev" if previous else "cur"
    out = os.path.join(HERE, f"raw_prev_{locale}" if previous else f"raw_{locale}")
    os.makedirs(out, exist_ok=True)

    first = get(f"{BASE}?limit={LIMIT}&offset=0&locale={locale}&_e={edition}",
                headers=headers)
    total = first["totalItems"]
    print(f"[{locale}] totalItems = {total}")
    with open(os.path.join(out, "0.json"), "w") as f:
        json.dump(first, f)

    def page(offset):
        path = os.path.join(out, f"{offset}.json")
        if os.path.exists(path) and os.path.getsize(path) > 100:
            return offset, "cached"
        data = get(f"{BASE}?limit={LIMIT}&offset={offset}&locale={locale}&_e={edition}",
                   headers=headers)
        with open(path, "w") as f:
            json.dump(data, f)
        return offset, len(data.get("items", []))

    offsets = list(range(LIMIT, total + LIMIT, LIMIT))
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for offset, n in pool.map(page, offsets):
            done += 1
            if done % 40 == 0 or done == len(offsets):
                print(f"[{locale}]   {done}/{len(offsets)} sider", flush=True)
    return total


if __name__ == "__main__":
    args = sys.argv[1:]
    assert_current_edition()
    if "--previous" in args:
        # Kun 'en': forrige årgang bruges udelukkende til ratingændringen,
        # ikke til viste labels.
        fetch_locale("en", previous=True)
    else:
        for loc in (args or ["en", "da"]):
            fetch_locale(loc)
    print("færdig")
