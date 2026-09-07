# fut27

Spillerdatabase for **EA SPORTS FC 27** — bladr i og filtrér alle 20.689
spillerkort. Ren statisk HTML: ingen backend, ingen API-nøgle, intet build-trin.

Åbn `index.html` (virker også ved at dobbeltklikke filen lokalt).

## Datakilder

| Kilde | Bruges til | Adgang |
|---|---|---|
| `drop-api.ea.com/rating/ea-sports-fc` | ratings, attributter, klub/liga/nation, position | åben |
| samme, uden `drop-referrer` | forrige årgang (FC 26), til ratingændringer | åben |
| `fut.gg/api/fut/players/v2/27/definitions/` | højde, vægt, accelerationstype | åben |

### `drop-referrer` afgør årgangen

Det samme EA-endpoint svarer med **to forskellige databaser** afhængigt af én header:

| Kald | Spillere | Årgang | #1 |
|---|---|---|---|
| uden header | 17.873 | FC 26 | Salah 91 |
| `drop-referrer: https://www.ea.com/games/ea-sports-fc/ratings` | 20.689 | **FC 27** | Mbappé 91 |

Værdien valideres — en vilkårlig streng giver FC 26-datasættet igen. Der findes
ingen årgangsparameter: `game=`, `version=`, `year=` og `iteration=` ignoreres
alle, og `/rating/ea-sports-fc/filters` returnerer `iterations: []`.

**Fælde:** EA's CDN cacher på URL alene — svaret har `cache-control: public,
s-maxage=600` og **ingen `Vary: drop-referrer`**. To kald til samme URL, der kun
adskiller sig ved headeren, deler cache-post, og det andet får det førstes
årgang tilbage. Derfor bærer hver årgang sin egen `_e`-parameter i
`fetch_ratings.py`. Uden den henter `--previous` glad og gerne FC 27 igen.

`fetch_ratings.py` kører desuden en kontrol før hver hentning: den henter én
side med og én uden headeren og afbryder, hvis de er ens. Headeren er
udokumenteret, så uden kontrollen ville en ændring hos EA stille og roligt give
et forældet datasæt.

### Sådan verificerer du årgangen

`campaignOverview.internalName` er **ikke** et pålideligt signal — det er et
marketing-banner og sagde "FC 27 Ratings | FUT" i månedsvis, mens `items`
stadig var FC 26. Tjek i stedet spillere, hvis rating faktisk ændrede sig:

| eaId | Spiller | FC 26 | FC 27 |
|---|---|---|---|
| 239085 | Erling Haaland | 90 | 91 |
| 277643 | Lamine Yamal | 89 | 90 |
| 203376 | Virgil van Dijk | 90 | 88 |
| 251854 | Pedri | 89 | 90 |

Uafhængigt facit: `curl https://www.fut.gg/api/fut/player-item-definitions/27/239085/`

### Felter EA ikke udfylder

EA's drop-api efterlader `height` og `weight` tomme i hele FC 27-droppet og har
slet ikke accelerationstype. FUT.GG's definition-endpoint er åbent og har alle
tre, så `enrich_futgg.py` henter dem derfra.

Dækning: **16.164 af 20.689** (78 %) for højde og accelerationstype, 14.584 for
vægt. Hullerne sidder i bunden af rangeringen. Siden viser dækningsgraden i
filterpanelet frem for at lade brugeren tro, at filteret er i stykker.

`playerAbilities` (PlayStyles) er tom for alle spillere — også hos
tredjeparter, og EA's egen filter-taksonomi bekræfter det
(`playerAbilities: []`). PlayStyles-filteret skjules automatisk og dukker op af
sig selv, når et datasæt igen har dem.

### Hvad vi ikke kan hente

**Markedspriser.** FUT.GG's prisruter (`/api/fut/player-prices/…`) ligger bag
Cloudflares JS-challenge, og FUTBIN, FUTWIZ og FUTNext blokerer al
programmatisk adgang med HTTP 403. Det er bevidst adgangsbeskyttelse, og den
omgår vi ikke. Dermed er priser, prisgrafer, "billigst pr. rating" og
SBC-løsningsforslag uden for rækkevidde.

EA's officielle **FC Community API** ville give klub- og squaddata, men er kun
åben for tre godkendte partnersites (FUT.GG, FUTBIN, FUTWIZ).

## Hvorfor er data bundlet i stedet for hentet live?

EA sætter kun `access-control-allow-origin: https://www.ea.com`. Alle andre
origins får intet CORS-hoved, så browseren blokerer direkte kald:

```
$ curl -sS -D - -o /dev/null \
    "https://drop-api.ea.com/rating/ea-sports-fc?limit=1" \
    -H "Origin: https://example.com" | grep -i access-control
access-control-allow-credentials: true          # ingen allow-origin
```

Data hentes derfor server-side og lægges i `data/players.js`, som sætter
`window.FUT_DATA`. Et almindeligt `<script>`-tag frem for `fetch()` betyder også,
at siden virker direkte fra `file://`.

## Opdatér datasættet

```bash
./tools/refresh.sh
```

Kører de tre trin i rækkefølge:

```bash
python3 tools/fetch_ratings.py             # FC 27 (en + da)   ~35 s
python3 tools/fetch_ratings.py --previous  # FC 26 (en)        ~20 s
python3 tools/enrich_futgg.py              # højde/vægt/accel  ~2 min
python3 tools/build_dataset.py             # bygger players.js
```

Rå sider caches i `tools/raw_*/` og er git-ignoreret — slet dem for at tvinge en
frisk hentning. Bygningen fungerer også uden de valgfrie trin: mangler forrige
årgang eller berigelsen, skjuler siden bare de tilhørende funktioner.

EA efterjusterer ratings hen over september efter transfervinduet, så en refresh
er en god idé et par uger inde i sæsonen.

## Funktioner

**Filtre:** fritekst (accent-ufølsom, så "mbappe" finder "Mbappé"),
rating-interval, position med eller uden alternativpositioner, spillerkategori,
køn, liga, klub, nation, foretrukken fod, tricks, svag fod, maksimal alder,
minimumshøjde, accelerationstype, ændring siden forrige årgang og minimumskrav
på hver af de seks hovedattributter. PlayStyles, når datasættet har dem.

**Sortering:** rating, hver hovedattribut, tricks, svag fod, alder, navn samt
største stigning og største fald siden forrige årgang.

**Ratingændring.** Fordi `drop-referrer` giver adgang til begge årgange, kan
hver spiller vises med sin FC 26-rating og ændringen markeret direkte på kortet.
9.768 spillere har fået ny rating, og 7.377 er nye i FC 27. Prissiderne følger
kun ændringer inden for én sæson, så den her sammenligning findes ikke hos dem.

**Sammenligning.** Op til fire spillere side om side over alle 40 attributter
med den bedste værdi fremhævet pr. række.

**Lignende spillere.** Nærmeste nabo på de seks hovedattributter inden for samme
position, vægtet med rating.

## Holdbygger med chemistry

Fanen "Holdbygger" giver en bane med 11 pladser og 10 formationer (4-4-2,
4-3-3, 4-2-3-1, 4-3-2-1, 4-1-2-1-2, 4-4-1-1, 4-2-2-2, 3-5-2, 3-4-2-1, 5-3-2).
Kun de 12 positioner EA's ratingsdata indeholder bruges, så der er ingen
LWB/RWB/CF-pladser.

### Chemistry-reglerne

Efter FC 26/27-systemet ([kilde](https://fifauteam.com/fc-26-chemistry/)):

| | 1 point | 2 point | 3 point |
|---|---|---|---|
| Klub | 2 | 4 | 7 |
| Liga | 3 | 5 | 8 |
| Nation | 2 | 5 | 8 |

De tre lægges sammen og loftes ved 3 pr. spiller, altså 33 for et fuldt hold.

Den regel der betyder mest: **en spiller ude af position får 0 chemistry og
tælles heller ikke med i holdkammeraternes forbindelser.** Beregningen tæller
derfor kun spillere der står rigtigt. Et kort markeres sølvfarvet, når det står
ude af position.

Ikoner og helte har særregler (dobbelttælling for nation henholdsvis liga), men
de findes ikke i EA's ratings-database — den indeholder kun basisspillere. Af
samme grund er der ingen manager-bonus.

### Holdrating

Gennemsnittet af de 11 ratings plus overskuddet fra spillere over gennemsnittet:

```
avg     = sum / 11
overskud = Σ max(0, rating − avg)
rating  = ⌊(sum + overskud) / 11⌋
```

Et hold med 10 × 80 og 1 × 90 giver 81, ikke 81,9.

### Værktøjer

- **Fyld bedste XI** — højest ratede spiller pr. plads uden gengangere. Pladser
  med færrest kandidater fyldes først, så en sjælden position ikke bliver spist
  af en tidligere plads.
- **Optimér chemistry** — bytter gentagne gange en spiller ud med en kandidat
  på samme position, der hæver den samlede chemistry uden at koste mere end 1 i
  holdrating. Grådig og lokal, ikke garanteret optimal — men den finder typisk
  33/33 fra et 90-ratet udgangspunkt og lander på 89.
- **Kopiér link** — holdet ligger i URL'ens hash (`#view=squad&f=4-3-3&s=…`),
  så en opstilling kan deles og genindlæses præcist.

Formationsskift beholder de spillere der stadig passer på deres nye plads og
rydder resten.

Filtertilstanden ligger i URL'ens hash, så en filtreret visning kan deles —
fx `#change=up&accel=5,6,7` for lange spillere der er steget.

Målmandskort viser DIV/HAN/KIC/REF/SPE/POS i stedet for PAC/SHO/PAS/DRI/DEF/PHY;
EA lægger målmandsværdierne i de samme seks felter.

Kortene renderes i portioner på 60 via en IntersectionObserver, så alle 20.689
kan filtreres uden at belaste DOM'en.

## Filstruktur

```
index.html                hele appen — spillerliste, holdbygger, CSS og JS i én fil
data/players.js           genereret datasæt (~4,5 MB, ~1,5 MB gzippet)
tools/fetch_ratings.py    henter en årgang fra EA's drop-api
tools/enrich_futgg.py     henter højde/vægt/accelerationstype fra FUT.GG
tools/build_dataset.py    bygger det kompakte players.js
tools/refresh.sh          kører det hele
```

`players.js` er tupler frem for objekter for at holde filen lille.
Feltrækkefølgen er defineret i `build_dataset.py` og spejlet i konstanterne
øverst i scriptet i `index.html` — **ændrer du den ene, skal den anden følge med.**

## Forbehold

Uofficiel demo, ikke tilknyttet EA. Spillerbilleder og klublogoer hotlinkes fra
EA's eget CDN og tilhører EA Sports. Højde, vægt og accelerationstype kommer fra
FUT.GG's åbne definition-endpoint. `drop-referrer`-adfærden er udokumenteret og
kan forsvinde uden varsel — derfor kontrollen i `fetch_ratings.py`.
