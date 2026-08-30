# Dummy OS EMS 0.0.1-alpha.63 - Startup Recovery Hotfix

## Samenvatting

Alpha63 corrigeert twee concrete recoveryproblemen na een Home Assistant-herstart.

## Opgelost

- Een cached Plan72 in `waiting_for_soc` wordt eenmalig opnieuw opgebouwd zodra de SOC-entiteit na startup geldig numeriek wordt.
- De Stroomvoorspeller-cache wordt daarbij niet gewist; alpha60 rate limiting blijft intact.
- Een verlopen planner-owned slot met lifecycle `fout` na een onderbroken uitvoering wordt bij startup gereconcilieerd zodat het slot opnieuw bruikbaar is.
- Handmatige plannen worden niet aangepast.

## Ongewijzigd

- Alpha62 planned-energy execution en economische bloksemantiek blijven ongewijzigd.
- Alpha61 low-SOC safety recovery blijft ongewijzigd.
- Automatic Execution-arm, safety gates en safe-return blijven ongewijzigd.
