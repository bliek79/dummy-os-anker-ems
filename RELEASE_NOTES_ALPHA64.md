# Dummy OS EMS 0.0.1-alpha.64 - Coordinator SOC Recovery Hotfix

## Samenvatting
Alpha64 maakt de Plan72-startuprecovery deterministisch door deze in de coordinator-refreshpolicy zelf op te nemen.

## Opgelost
- Als de eerste startup-pass `waiting_for_soc` cachet en een latere coordinatorcyclus een geldige numerieke SOC ziet, wordt Plan72 direct opnieuw opgebouwd.
- De recovery is niet langer afhankelijk van een losse achtergrondtaak vanuit entity-migratie.
- De tijdelijke alpha63 startup-task is verwijderd.
- De Stroomvoorspeller direct-forecastcache wordt niet gewist; alpha60 rate limiting blijft intact.

## Ongewijzigd
- Alpha63 reconciliatiegedrag voor automatische planslots via de bestaande Plan Store lifecycle blijft beschikbaar.
- Alpha62 planned-energy execution, target-SOC-afleiding en prijsvensterbegrenzing blijven ongewijzigd.
- Alpha61 low-SOC safety recovery blijft ongewijzigd.
- Manual plans, Automatic Execution-arm, safety gates en safe-return blijven ongewijzigd.

## Validatie
- `python -m compileall -q custom_components/anker_ems` moet slagen.
- Gerichte broncontrole bevestigt de nieuwe refreshreden `soc_recovered_after_startup`.
- Live Home Assistant-validatie na installatie/herstart blijft vereist.
