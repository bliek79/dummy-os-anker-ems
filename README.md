# Dummy OS EMS

Home Assistant EMS-integratie voor de Anker SOLIX Solarbank Max AC.

**Status:** experimentele alpha  
**Domein:** `anker_ems`  
**Minimale Home Assistant-versie:** 2026.7.0  
**Huidige release:** `0.0.1-alpha.5`

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
