# Dummy OS EMS 0.0.1-alpha.67 - Home Forecast Hourly Aggregation Fix

## Samenvatting
Alpha67 corrigeert de omzetting van sub-uurlijkse woningforecast-energie naar de uurlijkse Plan72-laag. Kwartierwaarden in kWh worden voortaan per uur gesommeerd in plaats van elkaar te overschrijven.

## Opgelost
- Woningforecastregels worden eerst per unieke timestamp gede-dupliceerd.
- Meerdere forecastpunten binnen hetzelfde uur worden als energie (kWh) opgeteld.
- Een bron die al uurlijkse waarden levert blijft ongewijzigd: één punt per uur blijft één uurwaarde.
- Diagnostiek toegevoegd voor raw rows, unieke punten, uurlijkse rijen, sub-uurlijkse uren en maximaal aantal punten per uur.
- Wijzigingen in de woningforecast zijn toegevoegd aan de Source Monitor/Plan72 refresh-token, zodat een gewijzigde woningforecast niet tot de volgende periodieke refresh hoeft te wachten.

## Bewust ongewijzigd
- De externe Home Forecast-entiteit blijft in alpha67 nog de bron van woningforecastdata.
- Plan72 handelslogica, prijsformules en safety/execution-keten zijn niet gewijzigd.
- De geplande eigen lerende Home Demand Forecast in de EMS-integratie volgt als aparte uitbreiding na live-validatie van deze hotfix.

## Live validatie
- Controleer `forecast_home_aggregation = sum_energy_per_hour`.
- Bij vier kwartierpunten in een uur moet `forecast_home_max_points_per_hour` minimaal 4 kunnen worden.
- Vergelijk voor een uur de som van de bronkwartieren met `home_consumption_kwh` in de EMS forecast.
- Controleer daarna of nachtelijke Energy Need en Plan72 SOC-projectie realistischer worden.
