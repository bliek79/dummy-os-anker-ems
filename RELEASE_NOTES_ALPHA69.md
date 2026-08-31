# Dummy OS EMS 0.0.1-alpha.69 - Exact Home Power Entity ID

## Correctie
- De canonieke EMS Home Power krijgt exact de project-afgesproken entity-ID `sensor.do_ems_home_power`.
- De bestaande alpha68 entity `sensor.dummy_os_ems_do_ems_home_power` wordt via de entity registry gemigreerd zonder de stable unique_id te vervangen.
- De naming-migratie draait zowel voor als na platform-setup, zodat ook nieuw aangemaakte entiteiten direct aan het expliciete Dummy OS naming-contract worden onderworpen.

## Vaste projectregel
Nieuwe Dummy OS / EMS entity-ID's worden vooraf expliciet vastgelegd en gecontroleerd. Een automatisch door Home Assistant afgeleide object-ID is geen geldige vervanging voor de afgesproken entity-ID.

## Niet gewijzigd
Home Power formule, bronselectie, forecast, Plan72, safety en fysieke execution blijven ongewijzigd.
