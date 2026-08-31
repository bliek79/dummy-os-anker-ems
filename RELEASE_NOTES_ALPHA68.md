# Dummy OS EMS 0.0.1-alpha.68 - Internal Home Power

## Doel
De EMS krijgt een eigen canonieke woningvermogenssensor als fundering voor de latere interne historie- en forecastlaag.

## Nieuw
- Nieuwe configureerbare Solar Power bronentiteit.
- Grid Import Power en Grid Export Power zijn voor nieuwe configuraties en reconfigure nu verplichte bronnen voor de Home Power laag.
- Battery Charge Power en Battery Discharge Power blijven afzonderlijke directionele bronnen.
- Nieuwe `DO EMS Home Power` sensor, bedoeld als `sensor.do_ems_home_power`.
- Interne formule: `solar + grid_import + battery_discharge - grid_export - battery_charge`.
- Diagnostiek toont de vijf bronentiteiten, actuele bronwaarden, raw resultaat en ontbrekende bronnen.
- Kleine negatieve transients door niet-gelijktijdige sensormetingen worden alleen op de canonieke Home Power naar 0 W begrensd; de raw waarde blijft zichtbaar.

## Veilig migratiegedrag
- Bestaande installaties zonder geconfigureerde Solar Power bron blijven laden.
- `DO EMS Home Power` rapporteert dan geen waarde en status `waiting_for_sources` totdat de vijf bronnen via Reconfigure zijn ingevuld.
- Alpha68 vervangt de huidige Home Forecast of Plan72-bron nog niet. De nieuwe Home Power draait eerst parallel/shadow.

## Volgende stap
Na live-validatie wordt op deze sensor de eigen 15-minuten historie en daarna de interne Home Demand Forecast gebouwd.
