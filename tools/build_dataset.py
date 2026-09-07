#!/usr/bin/env python3
"""Bygger et kompakt datasæt til FUT-demoen ud fra de rå drop-api-sider.

Output: data/players.js  ->  window.FUT_DATA = {...}
Formatet er tupler frem for objekter for at holde filen lille.
"""
import json, glob, os, re, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, os.pardir, "data", "players.js")

STAT_KEYS = [
    "pac", "sho", "pas", "dri", "def", "phy",
    "acceleration", "sprintSpeed", "positioning", "finishing", "shotPower",
    "longShots", "volleys", "penalties", "vision", "crossing", "freeKickAccuracy",
    "shortPassing", "longPassing", "curve", "agility", "balance", "reactions",
    "ballControl", "dribbling", "composure", "interceptions", "headingAccuracy",
    "defensiveAwareness", "standingTackle", "slidingTackle", "jumping", "stamina",
    "strength", "aggression", "gkDiving", "gkHandling", "gkKicking",
    "gkPositioning", "gkReflexes",
]

POS_TYPE = {
    "GK": 0,
    "CB": 1, "LB": 1, "RB": 1,
    "CDM": 2, "CM": 2, "CAM": 2, "LM": 2, "RM": 2,
    "LW": 3, "RW": 3, "ST": 3,
}


def load(dirname):
    seen = {}
    for f in glob.glob(os.path.join(HERE, dirname, "*.json")):
        for it in json.load(open(f))["items"]:
            seen[it["id"]] = it
    return seen


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def birthdate(raw):
    # "6/15/1992 12:00:00 AM" -> "1992-06-15"
    try:
        return datetime.strptime(raw.split(" ")[0], "%m/%d/%Y").strftime("%Y-%m-%d")
    except Exception:
        return ""


def display_name(p):
    common = clean(p.get("commonName"))
    if common:
        return common
    return clean(f"{clean(p.get('firstName'))} {clean(p.get('lastName'))}") or clean(p.get("lastName"))


en = load("raw_en")
da = load("raw_da")
print(f"indlæst {len(en)} spillere (en) / {len(da)} (da)")

# Forrige årgang, udelukkende til ratingændringen. Mangler den, bygges
# datasættet stadig — feltet står bare tomt, og siden skjuler funktionen.
prev = {}
try:
    prev = {pid: pl.get("overallRating") for pid, pl in load("raw_prev_en").items()}
    print(f"forrige årgang: {len(prev)} spillere (til ratingændring)")
except Exception:
    print("forrige årgang mangler — kør 'fetch_ratings.py --previous' for ratingændringer")

# Felter EA lader stå tomme, hentet fra FUT.GG's åbne definition-endpoint.
enrich = {}
_ep = os.path.join(HERE, "futgg_enrichment.json")
if os.path.exists(_ep):
    with open(_ep) as f:
        enrich = json.load(f)
    print(f"berigelse: {len(enrich)} spillere (højde/vægt/accelerationstype)")
else:
    print("ingen berigelse — kør 'enrich_futgg.py' for højde, vægt og accelerationstype")

# EA's egne koder; rækkefølgen her er den siden viser dem i.
ACCEL = ["EXPLOSIVE", "MOSTLY_EXPLOSIVE", "CONTROLLED_EXPLOSIVE", "CONTROLLED",
         "CONTROLLED_LENGTHY", "MOSTLY_LENGTHY", "LENGTHY"]
ACCEL_IDX = {a: i + 1 for i, a in enumerate(ACCEL)}  # 0 = ukendt

# PlayStyles vises på dansk. EA leverer dem pr. spiller, så slå dem op én gang
# på tværs af hele det danske datasæt og genbrug oversættelsen.
da_abilities = {}
for _p in da.values():
    for _a in _p.get("playerAbilities") or []:
        da_abilities[_a["id"]] = _a

nations, clubs, leagues, styles = {}, {}, {}, {}
players = []

for pid, p in sorted(en.items(), key=lambda kv: kv[1]["rank"]):
    d = da.get(pid, {})

    nat = p.get("nationality") or {}
    if nat.get("id") is not None and nat["id"] not in nations:
        da_nat = (d.get("nationality") or {}).get("label")
        nations[nat["id"]] = [clean(da_nat) or clean(nat.get("label")), nat.get("imageUrl") or ""]

    team = p.get("team") or {}
    if team.get("id") is not None and team["id"] not in clubs:
        clubs[team["id"]] = [clean(team.get("label")), team.get("imageUrl") or ""]

    lg = clean(p.get("leagueName"))
    if lg and lg not in leagues:
        leagues[lg] = len(leagues)

    ps, psplus = [], []
    for a in p.get("playerAbilities") or []:
        key = a["id"]
        if key not in styles:
            tr = da_abilities.get(key, a)
            styles[key] = [len(styles), clean(tr.get("label")) or clean(a.get("label")),
                           a.get("imageUrl") or "",
                           clean(tr.get("description")) or clean(a.get("description"))]
        idx = styles[key][0]
        (psplus if a.get("type", {}).get("id") == "playStylePlus" else ps).append(idx)

    pos = (p.get("position") or {}).get("shortLabel") or ""
    stats = p.get("stats") or {}
    ex = enrich.get(str(pid)) or {}
    players.append([
        pid,
        display_name(p),
        p.get("overallRating") or 0,
        p.get("rank") or 0,
        pos,
        POS_TYPE.get(pos, 1),
        [a.get("shortLabel") for a in (p.get("alternatePositions") or []) if a.get("shortLabel")],
        team.get("id"),
        nat.get("id"),
        leagues.get(lg, -1),
        (p.get("gender") or {}).get("id") or 0,
        p.get("preferredFoot") or 0,
        p.get("skillMoves") or 0,
        p.get("weakFootAbility") or 0,
        p.get("height") or ex.get("height") or 0,
        p.get("weight") or ex.get("weight") or 0,
        birthdate(p.get("birthdate") or ""),
        [(stats.get(k) or {}).get("value") or 0 for k in STAT_KEYS],
        ps,
        psplus,
        ACCEL_IDX.get(ex.get("accelerateType"), 0),
        prev.get(pid),
    ])

data = {
    "meta": {
        "total": len(players),
        "generatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://drop-api.ea.com/rating/ea-sports-fc",
        "edition": "FC 27",
        "previousEdition": "FC 26",
        "portrait": "https://ratings-images-prod.pulse.ea.com/FC25/full/player-portraits/p{id}.png?padding=0.7",
        "shield": "https://ratings-images-prod.pulse.ea.com/FC25/full/player-shields/en/{id}.png?width=265",
    },
    "statKeys": STAT_KEYS,
    "accelTypes": ACCEL,
    "nations": nations,
    "clubs": clubs,
    "leagues": [k for k, _ in sorted(leagues.items(), key=lambda kv: kv[1])],
    "playstyles": [[v[1], v[2], v[3]] for v in sorted(styles.values(), key=lambda v: v[0])],
    "players": players,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("window.FUT_DATA=")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

size = os.path.getsize(OUT)
print(f"skrev {OUT}  {size/1024/1024:.2f} MB")
print(f"  spillere={len(players)} klubber={len(clubs)} nationer={len(nations)} "
      f"ligaer={len(leagues)} playstyles={len(styles)}")
