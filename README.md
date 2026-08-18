# Dummy OS EMS

Home Assistant EMS-integratie voor de Anker SOLIX Solarbank Max AC.

**Status:** experimentele alpha  
**Domein:** `anker_ems`  
**Minimale Home Assistant-versie:** 2026.7.0  
**Huidige release:** `0.0.1-alpha.14`

## Alpha 5 - Forecast Sources

Alpha 5 bouwt voort op de stabiele HACS/GitHub-basis en voegt de eerste read-only forecastlaag toe.

De integratie normaliseert maximaal 72 uur naar één intern uurmodel met:
- `time`;
- `price`;
- `price_min`;
- `price_max`;
- `price_source`;
- `solar_kwh`;
- `home_consumption_kwh`.

Bekende prijzen hebben voor hetzelfde uur voorrang op een prijsprognose.

De standaardbronnen sluiten aan op de bestaande Dummy OS/YAML-architectuur:
- `sensor.battery_control_energy_prices` -> attribuut `prices`;
- `sensor.forecast_prices_all_in_data` -> attribuut `forecasts`;
- `sensor.forecast_home_consumption_data` -> attribuut `forecasts`;
- Solcast vandaag/morgen/dag 3 -> attribuut `detailedHourly`.

Deze bronnen kunnen na installatie via **Instellingen -> Apparaten & diensten -> Dummy OS EMS -> Configureren** worden aangepast.

## Nieuwe diagnose-entiteiten

- `Dummy OS EMS Forecast status`
- `Dummy OS EMS Forecast complete uren`
- `Dummy OS EMS Forecast bronnen beschikbaar`

`Forecast status` bevat als attributen de bronselectie, aantallen uren en het genormaliseerde 72-uursmodel.

## Veilig ontwikkelmodel

Alpha 5 blijft volledig uitlezend. Er zijn geen automatische plannerbeslissingen en geen fysieke write-calls naar de batterij. De bestaande operationele YAML-oplossing blijft tijdens ontwikkeling de referentie.

## OmniBattery

OmniBattery blijft een technische referentie, niet een vervanger. De latere planner kan principes gebruiken zoals tekortgestuurd netladen, reserve tot bruikbare zon, benodigde goedkoopste laaduren, scheiding tussen veiligheids- en handelslading, Solar Charge Delay, live veiligheidscontrole en fallback/herstel.

## Onafhankelijk project

Dummy OS EMS is een onafhankelijk opensource-communityproject en is niet gelieerd aan of goedgekeurd door Anker Innovations, Home Assistant, Nabu Casa of andere fabrikanten. Product- en merknamen blijven eigendom van hun rechthebbenden.


## Alpha 6 - Plan Store

Alpha 6 voegt drie onafhankelijke, persistent opgeslagen planplaatsen toe. Elke planplaats bevat een actie, uitvoeringsmodus, starttijd, vermogen, doel-SOC, maximale looptijd, maximale startvertraging en een afgeleide status. De waarden blijven na een Home Assistant-herstart behouden.

Alpha 8 plant en schakelt nog niets fysiek. Scheduler, Action Controller en Safety Guard zijn aanwezig, maar fysieke uitvoering blijft bewust uitgeschakeld.


## Alpha 7 Scheduler

The Scheduler evaluates persistent plans, start windows and conflicts. It remains simulation-only and performs no physical Anker writes.


## Alpha 8 safety boundary

Alpha 8 adds the Action Controller and Safety Guard decision chain, but it does not call Home Assistant services or write commands to the Anker device. It only prepares and validates the semantic command that a later alpha may execute after explicit validation.

## Alpha 10 - gecontroleerde fysieke laadtest

Alpha 10 voegt uitsluitend een expliciete fysieke testactie toe. De normale EMS-keten blijft in simulatie.

Veiligheidsgrenzen voor deze test:

- alleen laden;
- expliciete `confirm: true`;
- 100-500 W;
- 10-120 seconden;
- `third_party_control` moet vooraf actief zijn;
- Scheduler, Safety Guard en Action Controller moeten de laadactie goedkeuren;
- automatische stop naar 0 W en terug naar `self_consumption`;
- bij herstart of unload tijdens een actieve test wordt een safe-stop poging uitgevoerd.

De eerste aanbevolen test is 300 W gedurende 120 seconden.


## Alpha 12 - automatische modusovergang en uitvoerstate-machine

Alpha 12 bouwt voort op de geslaagde fysieke laadtest van alpha 11. De nieuwe
uitvoerstate-machine kan een door de Scheduler geselecteerd laadplan na een
expliciete bevestiging fysiek uitvoeren.

Belangrijkste eigenschappen:

- service `anker_ems.execute_selected_plan` met verplichte `confirm: true`;
- schakelt zelfstandig van `self_consumption` naar `third_party_control`;
- wacht maximaal 20 seconden tot richting- en setpoint-entiteiten beschikbaar zijn;
- voert daarna opnieuw Safety Guard en Action Controller uit;
- zet richting en gepland laadvermogen pas na een geldige veiligheidscontrole;
- bewaakt doel-SOC, maximale looptijd, externe modus, richting, bronbeschikbaarheid en onverwacht ontladen;
- safe-stop zet eerst het setpoint op 0 W en schakelt daarna terug naar `self_consumption`;
- actieve uitvoering wordt persistent gevolgd en na een Home Assistant-herstart veilig afgebroken;
- service `anker_ems.stop_execution` blijft beschikbaar voor handmatige stop;
- ontladen is in alpha 12 nog fysiek geblokkeerd totdat een afzonderlijke gecontroleerde ontlaadtest is uitgevoerd;
- de automatische 72-uursplanner start deze uitvoerstate-machine nog niet zelfstandig.

Nieuwe diagnose-entiteiten:

- `Dummy OS EMS Uitvoering status`;
- `Dummy OS EMS Uitvoering resterend`;
- `Dummy OS EMS Uitvoering actief`.


## Alpha 13 - Source Monitor

Alpha 13 observes when Solcast, Stroomvoorspeller, EnergyZero price data and the price forecast are reported and when their actual content changes. The monitor keeps seven days of event history in Home Assistant storage. It is observational only and does not yet trigger the automatic planner.
