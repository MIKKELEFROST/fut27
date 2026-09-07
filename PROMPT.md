# Byg-prompt for fut27

Den her prompt genskaber projektet fra bunden. Den er skrevet til at blive
givet til en AI-assistent med adgang til en terminal, en browser og et repo —
men den fungerer også som specifikation for et menneske.

Alt under "Fælder" er fundet den hårde vej. Springer man dem over, bygger man
noget der ser rigtigt ud og er forkert.

---

## Prompten

> Byg en statisk hjemmeside der viser hele spillerdatabasen fra EA SPORTS FC 27
> og lader brugeren filtrere i den og bygge et hold med chemistry.
>
> Ingen backend, ingen API-nøgle, intet build-trin. Slutresultatet er
> `index.html` + én genereret datafil, som kan hostes på GitHub Pages og også
> virker ved at dobbeltklikke filen lokalt. Al tekst i brugerfladen er dansk.
>
> **Hent data server-side med Python og bundl det.** EA sætter kun
> `access-control-allow-origin: https://www.ea.com`, så en browser kan ikke
> kalde API'et. Skriv datasættet som `data/players.js`, der sætter
> `window.FUT_DATA`, og indlæs den med et `<script>`-tag — ikke `fetch()`, så
> siden også virker fra `file://`.
>
> Verificér alt du bygger i en rigtig browser, ikke kun i koden. Tag
> screenshots og kig på dem.

---

## Datakilder

### 1. EA's ratings-API — ratings og attributter

```
https://drop-api.ea.com/rating/ea-sports-fc?limit=100&offset=0&locale=da
```

Ingen nøgle, intet login. `limit` maks. 100 (større giver HTTP 400), `offset`
paginerer, `locale` understøtter bl.a. `en` og `da`.

**Årgangen afgøres af én header:**

| Kald | Spillere | Årgang |
|---|---|---|
| uden header | 17.873 | FC 26 |
| `drop-referrer: https://www.ea.com/games/ea-sports-fc/ratings` | 20.689 | FC 27 |

Værdien valideres — en vilkårlig streng giver FC 26 igen. Der er ingen
årgangsparameter: `game=`, `version=`, `year=` og `iteration=` ignoreres alle.

Hent **begge** årgange. Forskellen pr. spiller er en funktion, ingen af
konkurrenterne har.

Hent `en` til positioner og attributnavne (GK, CB, ST er det alle bruger) og
`da` til nationer og PlayStyles.

### 2. FUT.GG's definition-endpoint — felter EA ikke udfylder

```
https://www.fut.gg/api/fut/players/v2/27/definitions/?overall__gte=85
```

Åbent, ingen nøgle. Giver `height`, `weight` og `accelerateType`, som EA lader
stå tomme. Sidestørrelsen er låst til 30, og hver forespørgsel er hårdt loftet
ved 10.000 resultater — så del hentningen i `overall`-bånd, der hver holder sig
under loftet, og lad scriptet fejle hvis et bånd rammer loftet.

Tag kun de tre felter herfra. Ratings og attributter kommer fra EA; to kilder
til samme tal kan kun modsige hinanden.

### 3. Kortskabelonen

Byg ikke kortet som en CSS-gradient — brug EA's rigtige skabelon. FUT.GG's
`rarity.imageUrls` i definition-svaret peger på guld-, sølv- og bronzekortene,
og CDN-stien kan tvinges til fuld kvalitet og PNG med alfa:

```
.../cdn-cgi/image/quality=100,format=png,width=500/2027/rarities-level-3-large/...
```

Beskær til den ikke-gennemsigtige kasse først — filen har 12 % tom luft i
toppen, og uden beskæringen passer CSS-forholdet ikke til det, man ser.
Konvertér til WebP; det tager filerne fra ~450 KB til ~50 KB.

Placér alt i procent af skabelonen og sæt skrift i `cqw` med
`container-type: inline-size` på kortet, så det skalerer i ét stykke.
Mål selv de to ting der styrer layoutet: delelinjen (63,3 % nede — navnet står
lige under) og hvor langt skjoldet når ned ved forskellige x-positioner. Det går
længst ned på midten, så centrerede logoer i bunden har plads. Husk at de to
statrækker fylder ca. 19 % af kortets højde: begynder de for lavt, lander de
oven på logoerne.

### 4. Billeder

```
https://ratings-images-prod.pulse.ea.com/FC25/full/player-portraits/p{eaId}.png?padding=0.7
```

`FC25` er EA's CDN-mappe, som de ikke har omdøbt; `FC24`, `FC26` og `FC27`
giver alle 403. URL'en kan udledes af spiller-id — kontrollér det (den matchede
i 600 af 600 stikprøver) frem for at gemme en URL pr. spiller.

Klub- og nationslogoer har derimod hashede URL'er, der **ikke** kan udledes —
gem dem i opslagstabeller.

---

## Fælder

**EA's CDN cacher på URL alene.** Svaret har `cache-control: public,
s-maxage=600` og **ingen `Vary: drop-referrer`**. To kald til samme URL, der
kun adskiller sig ved headeren, deler cache-post, og det andet får det førstes
årgang tilbage. Giv hver årgang sin egen parameter i query-strengen
(`&_e=cur` / `&_e=prev`). Uden det henter "forrige årgang" glad og gerne den
nuværende, og ratingændringen bliver lutter nuller — og ser helt korrekt ud.

**`campaignOverview.internalName` lyver.** Det er et marketing-banner. Det sagde
"FC 27 Ratings | FUT" i månedsvis, mens `items` stadig var FC 26. Brug det
aldrig til at afgøre årgangen — se "Verifikation" nedenfor.

**Headeren er udokumenteret og kan forsvinde.** Læg en kontrol i
hentescriptet: hent én side med og én uden headeren, og afbryd hvis de er ens.
Ellers vil en ændring hos EA stille og roligt give et forældet datasæt.

**EA udfylder ikke alle felter.** I FC 27-droppet er `height`, `weight` og
`playerAbilities` (PlayStyles) tomme for **alle** spillere. Byg funktioner der
skjuler sig selv når data mangler, frem for at vise tomme felter — og lad dem
komme tilbage af sig selv, når et fremtidigt datasæt har dem.

**Målmænd bruger de samme seks felter.** `pac/sho/pas/dri/def/phy` indeholder
for målmænd DIV/HAN/KIC/REF/SPE/POS. Skift kun etiketterne.

**Portrætdækningen falder med rangeringen** — 12/12 i top 100, ca. 1/12
omkring rang 11.000. Vis en silhuet frem for et tomt felt.

**Priser er bevidst beskyttede.** FUT.GG's prisruter ligger bag Cloudflares
JS-challenge, og FUTBIN, FUTWIZ og FUTNext afviser al programmatisk adgang med
HTTP 403. Forsøg ikke at omgå det. Det betyder at priser, prisgrafer,
"billigst pr. rating" og SBC-løsninger er uden for projektets rækkevidde — sig
det ærligt i brugerfladen frem for at lade som om.

---

## Datamodel

20.689 spillere skal kunne filtreres flydende i browseren. Skriv datasættet som
**arrays frem for objekter** (en fast feltrækkefølge, ikke nøgler pr. spiller) og
læg klubber, nationer, ligaer og PlayStyles i opslagstabeller. Det giver ca.
4,5 MB / 1,5 MB gzippet — acceptabelt for en enkelt fil.

Dokumentér feltrækkefølgen ét sted i byggescriptet og spejl den i konstanter
øverst i sidens JavaScript. Ændrer man den ene, skal den anden følge med.

Byggescriptet skal virke selv når de valgfrie trin mangler: uden forrige årgang
eller berigelse bygges datasættet stadig, og siden skjuler bare funktionerne.

---

## Funktioner

### Spillerliste

Kortgrid i FUT-stil: rating, position, nations- og klublogo, portræt,
navn og de seks hovedattributter. Guld/sølv/bronze efter rating (75+/65+/derunder).

Ratingændringen siden forrige årgang vises som et badge på kortet — grønt ved
stigning, rødt ved fald, "NY" for spillere der ikke fandtes sidste år.

**Filtre:** fritekst (accent-ufølsom, så "mbappe" finder "Mbappé"),
rating-interval, position med valgfri medregning af alternativpositioner,
spillerkategori, køn, liga, klub, nation, foretrukken fod, tricks, svag fod,
maksimal alder, minimumshøjde, accelerationstype, ændring siden forrige årgang,
minimumskrav på hver af de seks hovedattributter, og PlayStyles når de findes.

**Sortering:** rating, hver hovedattribut, tricks, svag fod, alder, navn,
største stigning og største fald.

Hvor et filter bygger på delvis data, så skriv dækningsgraden ved filteret.
Brugeren skal ikke gætte på, om filteret er i stykker.

**Detaljevisning:** alle 40 attributter grupperet med søjler, ratingændringen,
PlayStyles med beskrivelser når de findes, og lignende spillere (nærmeste nabo
på hovedattributterne inden for samme position, vægtet med rating).

**Sammenligning** af op til fire spillere over alle attributter med den bedste
værdi fremhævet pr. række.

Filtertilstanden skal ligge i URL'ens hash, så en filtreret visning kan deles.

**Ydelse:** rendér kortene i portioner via en `IntersectionObserver` frem for
at lægge 20.689 i DOM'en. Genobservér sentinelen efter hver portion — ellers
stopper uendelig scroll, hvis sentinelen stadig er synlig efter en render.

### Holdbygger

Bane med 11 pladser og mindst 10 formationer. Brug kun de 12 positioner EA's
data indeholder (GK, CB, LB, RB, CDM, CM, CAM, LM, RM, LW, RW, ST) — der er
ingen LWB/RWB/CF.

Klik på en plads åbner en vælger, der som standard kun viser spillere, der kan
stå der. Formationsskift beholder de spillere, der stadig passer.

**Chemistry efter FC 26/27-reglerne:**

| | 1 point | 2 point | 3 point |
|---|---|---|---|
| Klub | 2 | 4 | 7 |
| Liga | 3 | 5 | 8 |
| Nation | 2 | 5 | 8 |

De tre lægges sammen og loftes ved 3 pr. spiller, altså 33 for et fuldt hold.

Den regel der betyder mest: **en spiller ude af position får 0 chemistry og
tælles heller ikke med i holdkammeraternes forbindelser.** Tællingerne skal
derfor kun løbe over spillere, der står rigtigt. Markér kortet visuelt, når det
ikke er tilfældet.

Ikoner og helte har særregler, men findes ikke i EA's ratings-database — den
indeholder kun basisspillere. Samme grund til at der ikke er manager-bonus.

**Holdrating** er gennemsnittet plus overskuddet fra spillere over det:

```
avg      = sum / 11
overskud = Σ max(0, rating − avg)
rating   = ⌊(sum + overskud) / 11⌋
```

Kontrol: 10 × 80 og 1 × 90 giver 81.

Vis et panel der forklarer *hvorfor* holdet har den chemistry det har — hvilke
klubber, ligaer og nationer der tæller, og hvor mange point hver giver.

**Værktøjer:** fyld bedste XI (fyld pladser med færrest kandidater først, så en
sjælden position ikke bliver spist af en tidligere plads), grådig
chemistry-optimering der bytter spillere på samme position så længe det hæver
chemistry uden at koste mere end 1 i holdrating, ryd hold, og delbart link med
opstillingen i URL-hashen.

---

## Design

Mørkt, roligt, informationstæt. Guld som accent. Alt i én HTML-fil med egen CSS
— ingen framework, ingen CDN-afhængighed.

Filterpanel til venstre, resultater til højre, aktive filtre som chips man kan
fjerne enkeltvis. Responsivt ned til 390 px, hvor filterpanelet bliver en
skuffe. Ingen vandret scroll på noget tidspunkt.

---

## Verifikation

**Afgør aldrig årgangen på `campaignOverview`.** Tjek spillere, hvis rating
faktisk ændrede sig:

| eaId | Spiller | FC 26 | FC 27 |
|---|---|---|---|
| 239085 | Erling Haaland | 90 | 91 |
| 277643 | Lamine Yamal | 89 | 90 |
| 203376 | Virgil van Dijk | 90 | 88 |
| 251854 | Pedri | 89 | 90 |

Uafhængigt facit pr. spiller og årgang:
`curl https://www.fut.gg/api/fut/player-item-definitions/27/239085/`

**Kør en browsertest, ikke kun en kodegennemgang.** Tællingerne skal stemme med
datasættet. Fra snapshottet 7. september 2026 — tallene flytter sig, når EA
efterjusterer, så brug dem som størrelsesorden, ikke som facit:

- 20.689 spillere, Mbappé 91 som #1
- 2.061 i kvindefodbold, 2.290 målmænd
- accelerationstype: 1.576 eksplosive, 10.851 kontrollerede, 3.737 lange
- 5.975 steget + 3.793 faldet = 9.768 ændrede, 7.377 nye

**Test chemistry uafhængigt af din egen kode:** tæl de grønne diamanter i
DOM'en og sammenlign med det viste total. De skal stemme, og totalen må aldrig
overstige 33. Efterregn desuden et par spillere i hånden mod tærskeltabellen.

**Tag screenshots og kig på dem.** Tre fejl i det her projekt var usynlige i
koden og åbenlyse på et billede:

1. Banen kollapsede til 2×3 pixels, fordi holdbyggeren var et tredje barn i et
   to-kolonne-grid. Brug `minmax(0,1fr)`, så en bred celle ikke kan sprænge en
   kolonne.
2. Målmandspladsen kunne ikke klikkes, fordi banens dekorative
   straffesparksfelt blev malet oven på den. Giv rene pyntelag
   `pointer-events: none`.
3. Vandret scroll på mobil, fordi spillernavnet lå i en `<span>`. Inline-elementer
   kan ikke klippe tekst — `overflow: hidden` og ellipsis virker først med
   `display: block`, og uden det sætter det længste navn min-content-bredden på
   hele gridkolonnen.

Den samme klasse af fejl gik igen tre gange: **et element hvis kasse ikke passer
til dets indhold.** Mål geometrien i browseren, når noget opfører sig mærkeligt,
frem for at gætte ud fra CSS'en.

---

## Ikke-mål

Priser og alt der hænger på dem. SBC-løsninger. Evolutions. Login og klubdata
— EA's officielle FC Community API findes, men er kun åben for tre godkendte
partnersites.

## Til sidst

Skriv en README der forklarer, hvor data kommer fra, hvad der er verificeret, og
hvad der er antaget. Sæt en synlig ansvarsfraskrivelse på selve siden: uofficiel
demo, ikke tilknyttet EA, billeder og logoer tilhører EA Sports.
