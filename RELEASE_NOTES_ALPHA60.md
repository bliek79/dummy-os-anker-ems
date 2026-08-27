## Dummy OS EMS 0.0.1-alpha.60

Gerichte stabiliteitsrelease om request-storms en onnodige systeembelasting rond de directe Stroomvoorspeller-prijsforecast te stoppen.

### Opgelost
- De 30-minuten cache voor de directe Stroomvoorspeller `forecast.json` werd onbedoeld gewist tijdens iedere Plan72 refreshbeslissing.
- Daardoor kon de coordinator bij een HTTP 403 opnieuw en opnieuw dezelfde externe forecast ophalen, ondanks de bestaande 30-minuten fetchguard.
- De cache-reset is verwijderd uit `_should_refresh_72h_plan()`.
- Een mislukte directe forecast-fetch blijft nu onder dezelfde 30-minuten fetchguard vallen.
- De laatst geldige directe forecastpayload blijft behouden wanneer een latere fetch mislukt.
- Hierdoor veroorzaakt een tijdelijke Stroomvoorspeller/Vercel 403 geen request-storm meer vanuit Dummy OS EMS.

### Gewijzigd
- Interne versie bijgewerkt naar `0.0.1-alpha.60`.
- De snelle 10-seconden coordinatorcyclus blijft bestaan voor live safety/execution, maar kan niet meer iedere cyclus de directe prijsforecast ophalen.

### Ongewijzigd
- Plan72-plannerlogica.
- Prijsnormalisatie en EUR/MWh -> EUR/kWh conversie.
- Known today/tomorrow blijft leidend boven forecast voor hetzelfde uur.
- Import- en exportmarkup.
- Dynamische reserve en uitvoeringsbuffer.
- Safety-charge actionability threshold van 0,10 kWh.
- Automatic Plan Bridge, Plan Store, Scheduler en Safety Guard.
- Fysieke uitvoeringsvolgorde en vermogenslimieten.
- Alpha59 event-loop/thread-safety fix.

### Validatie
- Home Assistant volledig herstarten na installatie.
- Controleren dat Dummy OS EMS normaal initialiseert.
- Bij een eventuele Stroomvoorspeller 403 mag hooguit één fetchwaarschuwing per cachevenster ontstaan, niet iedere 5-10 seconden.
- Plan72 moet geldig blijven wanneer voldoende bekende/cached prijsdata beschikbaar is.
- De alpha59 thread-safety meldingen mogen niet terugkomen.
- Automatic Execution en safety-keten moeten ongewijzigd blijven werken.
