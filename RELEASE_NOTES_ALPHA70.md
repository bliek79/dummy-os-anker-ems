# Dummy OS EMS 0.0.1-alpha.70 - Internal Home History

## Nieuw
- Persistente EMS-eigen kwartierhistorie opgebouwd uit de gevalideerde `sensor.do_ems_home_power`.
- Nieuwe canonieke entiteit `sensor.do_ems_home_energy_15m`: laatst voltooide kwartierenergie in kWh, inclusief dekking en samplediagnostiek.
- Nieuwe diagnostische entiteit `sensor.do_ems_home_history_days`: aantal lokale kalenderdagen dat in de interne historie vertegenwoordigd is.
- Historie wordt 42 dagen bewaard om meerdere weekpatronen op te kunnen bouwen.
- Meetgaten langer dan 120 seconden worden niet als verbruik ingevuld; dekking per kwartier blijft daardoor controleerbaar.

## Naamgevingscontract
De twee nieuwe entity-ID's zijn expliciet vastgelegd. Home Assistant mag deze namen niet automatisch vervangen of van een `dummy_os_ems_`-prefix voorzien.

## Scope
Deze historylaag draait parallel/shadow. De bestaande externe Home Forecast en Plan72 blijven volledig ongewijzigd. De interne EMS Home Forecast wordt pas in een volgende stap op deze historie gebouwd en eerst parallel gevalideerd.
