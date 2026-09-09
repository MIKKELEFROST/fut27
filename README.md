# FIFA Centralen — fut27

Dansk kortdatabase for **EA SPORTS FC 27** — ratings, egenskaber og meta på alle
20.689 spillerkort, plus en squad builder med chemistry. Ren statisk HTML: ingen
backend, ingen API-nøgle, intet build-trin.

**Live: https://mikkelefrost.github.io/fut27/**

Åbn `index.html` lokalt (virker også ved at dobbeltklikke filen).

## Sider

| Rute | Skærm |
|---|---|
| `#/` | Forside — hero, "Kort i fokus", største ratingspring, højeste rating |
| `#/spillere` | Databasen — ni filterpaneler og resultattabel |
| `#/spiller/:id` | Spillerside — kort, udvikling, fire faner, lignende kort |
| `#/hold` | Squad Builder — bane, chemistry, holdrating |

Filtre og opstillinger ligger i hash'en, så en visning kan deles præcist:
`#/spillere?pos=GK&rmin=85`, `#/hold?f=4-3-3&s=220901.239231.…`

## Udgivelse

Siden ligger på GitHub Pages og opdateres automatisk ved hvert push til `main`
via `.github/workflows/pages.yml`. Kun `index.html`, `data/players.js` og
`assets/` udgives; `tools/` er byggeværktøj.

Pages blev slået til ved at oprette `gh-pages`-branchen — Actions-tokenet må
ikke oprette et Pages-site selv (`configure-pages` med `enablement: true` fejler
med "Resource not accessible by integration"), så workflowet skriver til
branchen i stedet for at bruge `deploy-pages`.

`PROMPT.md` indeholder en byg-prompt der genskaber projektet fra bunden —
inklusive alle de fælder i API'et og layoutet, der kostede tid at finde.

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

Dækning: **16.164 af 20.689** (78 %) for højde og accelerationstype, 14.584
(70 %) for vægt. Hullerne sidder i bunden af rangeringen. "Om data"-dialogen
viser dækningsgraden, og filterpanelet siger, at kort uden værdi falder ud af
filteret — frem for at lade brugeren tro, at filteret er i stykker.

`playerAbilities` (PlayStyles) er tom for alle spillere — også hos
tredjeparter, og EA's egen filter-taksonomi bekræfter det
(`playerAbilities: []`). Derfor findes der ikke et Spilstile-filter; pladsen i
designet bruges i stedet til **Krop & løb** (løbestil, fod, køn, højde, alder),
som er data vi rent faktisk har.

### Hvad vi ikke kan hente

**Markedspriser.** FUT.GG's prisruter (`/api/fut/player-prices/…`) ligger bag
Cloudflares JS-challenge, og FUTBIN, FUTWIZ og FUTNext blokerer al
programmatisk adgang med HTTP 403. Det er bevidst adgangsbeskyttelse, og den
omgår vi ikke. Konkurrenterne får deres priser ved at **crowdsource dem gennem
deres egen browserudvidelse** — FUTBIN Updater beskriver det selv sådan:
brugeren slår priser op i webappen, og udvidelsen sender resultatet tilbage.
Dermed er priser, prisgrafer, "billigst pr. rating" og SBC-løsningsforslag uden
for rækkevidde her.

EA's officielle **FC Community API** ville give klub- og squaddata, men er kun
åben for tre godkendte partnersites (FUT.GG, FUTBIN, FUTWIZ).

## Design

Designet kommer fra handoff-pakken **FIFA Centralen** (tokens, ni filterpaneler,
kortgeometri, tilstandsmodel, 17 referenceskærmbilleder). Prototypen i pakken
kørte på 62 opdigtede guldkort med opdigtede priser; her er datalaget skiftet
ud med det rigtige.

Fire steder afviger implementeringen bevidst fra prototypen, fordi designet
byggede på data der ikke findes:

| Designet | Her | Hvorfor |
|---|---|---|
| MARKEDSPULS (24 t prisændring) | **Største ratingspring** (FC 26 → FC 27) | Ingen priser. Ratingspringet er ægte historik, og ingen af prissiderne har det. |
| `Pris`-filter, `PRIS`-kolonne, `Billigst`-fane, markedsboks, `Marked`-fane | `Ratingspring`-filter, `FC 26`-kolonne, `Største spring`-fane, udviklingsboks, `Udvikling`-fane | Samme. |
| `Spilstile`-filter og SPILSTILE-badges | `Krop & løb`-filter og profil-badges | EA har ikke udgivet PlayStyles til FC 27. |
| `Virkeligheden`-fane (sæsonstatistik + kommentarer) | `Profil`-fane (fødselsdato, krop, løbestil, EA-plads) | Sæsonstatistik og kommentarer var genereret; profilfelterne er ægte. |
| "alle kort er guld i denne udgave" | guld, sølv og bronze | Datasættet spænder 47–91. |

`Marked` og `SBC'er` i navigationen, platformskifteren `PS / Xbox` og `Log ind`
er fjernet frem for at stå som døde knapper. `Squad Builder` er derimod bygget.

Fanen `Kemistile` er en **udledning**, ikke hentet data: den fremhæver de stile,
der løfter kortets stærkeste ansigtsstats, og siden siger det direkte i
brødteksten.

### Kortgrafikken

Kortene bruger EA's egne skabeloner på designets lærred:

```
assets/kort-{guld,soelv,bronze}.webp   504x700, kunsten ligger i (48,83)–(458,652)
```

Guldkortet er filen fra handoff-pakken uændret; sølv og bronze er de tilsvarende
EA-skabeloner lagt på samme lærred med samme forskydning, så alle tre deler
geometri og kan bruge én og samme CSS.

Hver del af kortet ligger **absolut placeret i procent af kortkassen**, og
skrift er sat i `cqw` med `container-type: inline-size`. Uden padding på
kortet er 1 `cqw` præcis 1 % af kortets bredde, så placeringer og
skriftstørrelser er i samme enhed, og kortet skalerer i ét stykke fra mobil til
desktop uden brudpunkter.

Tallene er aflæst på et rigtigt FC-kort og regnet om fra kunstens kasse
(48,83)–(458,652) til kortkassen 504×700 — `x = 9,52 + 0,8135·x_kunst`,
`y = 11,86 + 0,8129·y_kunst`:

| Del | Placering (% af kortkassen) |
|---|---|
| Rating (venstre) + primærposition under den | venstre 17 %, top 19,4 %, 12,2 cqw |
| Alternative positioner (højre, stablet) | højre 12,5 %, top 24,2 %, 5,3 cqw |
| Portræt | bredde 60 %, klippet ved delelinjen 63,4 % |
| Navn | top 65,2 %, 7,4 cqw |
| Statlinjer | 16–84 %, top 72 %, etiket 3,7 cqw, tal 7,2 cqw (ingen streg) |
| Nations- og klublogo | top 81,6 %, 6,3 cqw |

Fod, tricks og svagt ben står **ikke** på kortet — de hører til blandt
metabrikkerne på spillersiden. Uden dem fordeler navn, stats og logoer sig over
hele den flade guldbund fra 64 % til afsmalningen ved 86 %.

Skjoldet står i fuld bredde (9,7–90,7 %) fra 25 % til 83 % nede og smalner brat
efter 86 % — derfor er der ikke plads til mere under fodrækken.

Der skal **ingen streg** være over statlinjerne. Skabelonen har sin egen
adskillelse indbygget: kunsten skifter fra mønster til flad guldbund omkring
61–64 % nede, og navnet står lige under skiftet. En CSS-streg oveni giver
kortet en linje, EA's eget kort ikke har.

Tabellen på **Spillere** viser samme kort som miniature yderst til venstre i
hver række — kun skabelon og portræt, for ved 46 px ville ratingen stå på fem
pixel, og rækken har den i forvejen i sin egen kolonne. Klassen hedder
`k-mini` og ikke `mini`, fordi `.mini` allerede er filterpanelernes
hurtigvalg-knapper.

Portrættet hotlinkes fra EA's CDN. Billederne er 512×512 med hovedtop ved
10,7 %, hage ved ca. 72 % og skuldrene flugtende med underkanten;
`padding`-parameteren på CDN'et gør ingen forskel, der findes kun det ene
udsnit. Underkanten lægges lige under delelinjen, så skuldrene altid når ned
til den, og bredden 60 % giver hovedet samme placering på kortet som på et
rigtigt FC-kort. Slår billedet fejl, falder kortet tilbage til en cirkel med
spillerens initialer (`futFace()` sætter `has-face` ved `onload` og fjerner
billedet ved `onerror`).

**EA's CDN laver content negotiation.** Samme `.png`-URL svarer med AVIF, når
kaldet sender et almindeligt browser-`Accept`-hoved — 57 KB i snit mod 334 KB
som PNG. En tabelside med 15 portrætter vejer derfor ~860 KB, ikke 4,8 MB.
Resize-parametre (`?width=`, `?resize=`) ignoreres, og der findes ingen mindre
udgave af stien: `/small/`, `/thumb/` og `/medium/` svarer alle 403.

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
årgang eller berigelsen, står de tilhørende felter bare tomme.

EA efterjusterer ratings hen over september efter transfervinduet, så en refresh
er en god idé et par uger inde i sæsonen.

## Filtre

Ni paneler, ét åbent ad gangen, alle med aktive filtre vist som fjernbare piller:

| Panel | Indhold |
|---|---|
| Positioner | Alle/Primær/Alternativ + 12 positioner i tre grupper, med genveje |
| Ligaer · Nationer · Klubber | søgbare afkrydsningslister (63 / 164 / 755) |
| Ratingspring | min/maks + Nye i FC 27, +1–+2, +3–+5, +6 og op, Uændret, Nedgraderet |
| Rating | min/maks + Bronze, Sølv, Guld, 84–86, 87–88, 89+ |
| Tricks & ben | 1★–5★ for hver |
| Stats | min/maks på hver af de seks hovedattributter |
| Krop & løb | løbestil, fod, herre-/kvindefodbold, højde, alder |

Fritekstsøgning er accent-ufølsom ("mbappe" finder "Mbappé") og dækker navn,
klub, nation, liga og position. Sortering: rating, ratingspring, navn, alder.
Tabellen viser 15 rækker ad gangen.

**Ratingændring.** Fordi `drop-referrer` giver adgang til begge årgange, kan
hver spiller vises med sin FC 26-rating og ændringen. 9.768 spillere har fået ny
rating, og 7.377 er nye i FC 27. Prissiderne følger kun ændringer inden for én
sæson, så den her sammenligning findes ikke hos dem.

Målmandskort viser DIV/HAN/KIC/REF/SPE/POS i stedet for PAC/SHO/PAS/DRI/DEF/PHY;
EA lægger målmandsværdierne i de samme seks felter. Målmænd får også deres egne
egenskabsgrupper og en `/3400`-nævner i "samlede egenskaber" mod markspillernes
`/2900`.

## Squad Builder

En bane med 11 pladser og 10 formationer (4-4-2, 4-3-3, 4-2-3-1, 4-3-2-1,
4-1-2-1-2, 4-4-1-1, 4-2-2-2, 3-5-2, 3-4-2-1, 5-3-2). Kun de 12 positioner EA's
ratingsdata indeholder bruges, så der er ingen LWB/RWB/CF-pladser.

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
derfor kun spillere der står rigtigt, og en plads markeres rød, når kortet står
ude af position.

Ikoner og helte har særregler (dobbelttælling for nation henholdsvis liga), men
de findes ikke i EA's ratings-database — den indeholder kun basisspillere. Af
samme grund er der ingen manager-bonus.

### Holdrating

Gennemsnittet af de 11 ratings plus overskuddet fra spillere over gennemsnittet:

```
avg      = sum / 11
overskud = Σ max(0, rating − avg)
rating   = ⌊(sum + overskud) / 11⌋
```

Et hold med 10 × 80 og 1 × 90 giver 81, ikke 81,9.

### Værktøjer

- **Fyld bedste XI** — højest ratede spiller pr. plads uden gengangere. Pladser
  med færrest kandidater fyldes først, så en sjælden position ikke bliver spist
  af en tidligere plads. Giver 90 i holdrating og 16 i chemistry.
- **Optimér chemistry** — bytter gentagne gange en spiller ud med en kandidat
  på samme position, der hæver den samlede chemistry uden at koste mere end 1 i
  holdrating. Grådig og lokal, ikke garanteret optimal — men den finder 33/33
  fra det udgangspunkt og lander på 89.
- **Ryd hold** — tømmer banen.

Opstillingen skrives løbende til hash'en, så et hold kan deles ved at kopiere
URL'en. Formationsskift beholder de spillere der stadig passer på deres nye
plads og rydder resten.

## Filstruktur

```
index.html                hele appen — fire skærme, CSS og JS i én fil
assets/kort-*.webp        EA's kortskabeloner på designets 504x700-lærred
assets/logo.webp          FIFA Centralen-logoet (256 px)
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

Uofficiel database, ikke tilknyttet EA. Spillerbilleder hotlinkes fra EA's eget
CDN og tilhører EA Sports. Højde, vægt og accelerationstype kommer fra FUT.GG's
åbne definition-endpoint. `drop-referrer`-adfærden er udokumenteret og kan
forsvinde uden varsel — derfor kontrollen i `fetch_ratings.py`.
