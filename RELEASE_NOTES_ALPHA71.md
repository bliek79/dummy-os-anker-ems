# Dummy OS EMS 0.0.1-alpha.71 - Parallel Internal Home Forecast

## Nieuw
- Eigen EMS Home Forecast uit de persistente 15-minutenhistorie van `sensor.do_ems_home_power`.
- 72 uur vooruit met 15-minutenresolutie en een parallelle uuraggregatie.
- Tijdvakpatroon met voorkeur voor dezelfde weekdag, daarna weekdag/weekend-type, met zwaardere weging van recente historie.
- Robuuste voorspelling op basis van gewogen mediaan en 75e percentiel zodat incidentele pieken niet volledig worden gladgestreken.
- Coverage en confidence groeien mee met de hoeveelheid en kwaliteit van de eigen EMS-historie.

## Nieuwe canonieke entiteiten
- `sensor.do_ems_home_forecast`
- `sensor.do_ems_home_forecast_coverage`
- `sensor.do_ems_home_forecast_confidence`

De entity-ID's zijn expliciet vastgelegd in het naming-contract; Home Assistant mag geen automatische `dummy_os_ems_`-prefix toevoegen.

## Scope
De nieuwe forecast draait volledig parallel/shadow. De bestaande externe Home Forecast blijft de actieve bron voor Energy Need en Plan72. Safety, trading en fysieke execution zijn niet gewijzigd.

## Validatie na installatie
- Controleer de drie exacte entity-ID's.
- Controleer dat de forecast 288 kwartierpunten en 72 uurpunten bevat.
- Controleer dat status aanvankelijk `learning` kan zijn en confidence met historie groeit.
- Controleer dat `plan72_source` false blijft.
