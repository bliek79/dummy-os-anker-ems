# Dummy OS EMS - Home Forecast Transition Plan

## Doel
De interne EMS Home Forecast zo ver mogelijk voorbereiden voordat voldoende historie beschikbaar is, zodat de uiteindelijke overgang naar Plan72 gecontroleerd en stapsgewijs kan plaatsvinden.

## Uitgangspunten
- De huidige externe Home Forecast blijft actief totdat de interne bron aantoonbaar geschikt is.
- Nieuwe interne onderdelen draaien eerst observation/shadow.
- Geen fysieke execution-, safety- of tradinglogica wordt in deze voorbereidingsfase gewijzigd.
- Dummy OS Data blijft technisch buiten EMS. De Data Home Forecast is wel een functionele benchmark/referentie.
- Afwezigheidsmodus moet normale en afwezigheidshistorie strikt gescheiden houden.
- De bestaande Data-implementatie van normal/vacation wordt als functioneel voorbeeld gebruikt voor de EMS-versie.

## Overgangsstappen
1. `learning`
   - interne historie en forecast bouwen op;
   - geen plannerinvloed.
2. `shadow`
   - interne forecast parallel vergelijken met werkelijk verbruik;
   - externe bron blijft actief.
3. `candidate`
   - interne forecast mag parallel door dezelfde Energy Need- en Plan72-berekeningen worden gehaald;
   - resultaten zijn observatief en leiden nog geen acties.
4. `leading_ready`
   - alleen bereikbaar als historie, coverage, confidence en evaluatiefouten aan afgesproken drempels voldoen;
   - dit betekent alleen technisch gereed voor een expliciete overschakelbeslissing, niet automatisch overschakelen.
5. `internal leading`
   - pas na afzonderlijke expliciete goedkeuring;
   - externe forecast blijft fallback en onafhankelijke benchmark.

## Voorbereide readiness-gates
De eerste technische defaults zijn conservatieve startwaarden en moeten later met echte historie worden gevalideerd:
- minimaal 7 dagen voor shadow;
- minimaal 14 dagen voor candidate;
- minimaal 30 dagen voor `leading_ready`;
- minimaal 90% broncoverage;
- confidence minimaal 25% voor candidate en 50% voor leading-ready;
- evaluatie controleert kwartier-MAE en dagelijkse absolute bias.

Deze waarden zijn geen definitieve productdrempels. Ze zijn bewust gecentraliseerd zodat ze later op basis van echte meetdata kunnen worden aangepast zonder de bronkeuzelogica te herschrijven.

## Evaluatielaag
Per afgerond kwartier moet later een evaluatiepunt kunnen worden vastgelegd met minimaal:
- timestamp;
- mode (`normal` of `absence`);
- voorspeld kWh;
- werkelijk kWh;
- absolute fout;
- signed error / bias;
- dagdeel.

Samenvattingen:
- MAE per kwartier;
- mean bias;
- absolute bias omgerekend naar dag;
- voorspeld versus werkelijk totaal;
- uitsplitsing per mode;
- uitsplitsing per dagdeel.

## Afwezigheidsmodus
De functionele referentie uit Dummy OS Data gebruikt een `normal`- en `vacation`-profiel en laat de actieve operating mode doorwerken in forecast en batterijregeling. Voor EMS gebruiken we zichtbaar de term Afwezigheidsmodus, maar behouden we dezelfde ontwerpprincipes:
- elk nieuw historisch kwartier krijgt bij opslag een mode-label;
- normal-data voedt alleen het normale profiel;
- absence-data voedt alleen het afwezigheidsprofiel;
- einde afwezigheid schakelt direct terug naar normal;
- bij te weinig absence-data wordt een veilige fallback gebruikt;
- afwezigheidsdata mag het normale profiel nooit vervuilen.

De circa twee weken bestaande afwezigheidshistorie kan later worden onderzocht als initiële profielbasis. Een niveau rond 340-350 W overdag zonder bewoners is alleen een referentie met marge en geen harde grens.

## Bronkeuze en rollback
De voorbereide resolver ondersteunt conceptueel:
- `external`: externe forecast actief;
- `internal_shadow`: externe forecast actief, interne forecast alleen vergelijking;
- `internal`: interne forecast alleen actief als readiness `leading_ready` is.

Als de interne bron ontbreekt of niet ready is, valt de resolver altijd terug op external.

## Nog te bouwen zodra passend
- persistente forecast-versus-actual evaluatiepunten;
- mode-label in de interne 15m historie;
- eigen EMS Afwezigheidsmodus-bron/migratie vanaf bestaande legacy helpers;
- shadow Energy Need-resultaat met interne forecast;
- shadow Plan72-resultaat met interne forecast;
- zichtbare readiness/evaluatie-diagnostiek;
- later pas expliciete source selector in Options Flow.

## Niet doen vóór voldoende data
- geen agressieve tuning op 2-7 dagen historie;
- geen automatische overgang naar internal;
- geen wijziging aan safety/execution op basis van de nieuwe forecast;
- geen verwijdering van de externe forecast als fallback/referentie.
