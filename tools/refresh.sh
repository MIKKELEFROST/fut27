#!/usr/bin/env bash
# Opdaterer hele datasættet bag fut27.
#
#   ./tools/refresh.sh
#
# 1) FC 27 fra EA's drop-api (en + da)
# 2) FC 26 fra samme endpoint uden drop-referrer — til ratingændringer
# 3) højde, vægt og accelerationstype fra FUT.GG's åbne definition-endpoint
# 4) bygger data/players.js
#
# Trin 2 og 3 er valgfrie: mangler de, bygges datasættet stadig, og siden
# skjuler bare de funktioner der ikke har data.
#
# Rå sider caches i tools/raw_*/ og er git-ignoreret.
set -euo pipefail
cd "$(dirname "$0")"

python3 fetch_ratings.py
python3 fetch_ratings.py --previous
python3 enrich_futgg.py
python3 build_dataset.py

echo
echo "Færdig. Tjek diffen i data/players.js før du committer."
