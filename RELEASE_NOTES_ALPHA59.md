# Dummy OS EMS 0.0.1-alpha.59 - Home Assistant Event-Loop Thread-Safety Fix

## Opgelost
- Herstelt de Home Assistant thread-safety fout waarbij `hass.async_create_task()` vanuit een worker thread werd aangeroepen door de execution-monitor callback.
- Vervangt de onveilige lambda in `execution.py` door een Home Assistant `@callback`-gemarkeerde event-loop callback.
- Past dezelfde root-cause fix preventief toe op de identieke monitorcallback in `physical_test.py`, zodat die codepad niet later dezelfde fout kan veroorzaken.
- Voorkomt de bijbehorende melding `coroutine ... was never awaited` voor deze monitorcallbacks.

## Gewijzigd
- Monitorcallbacks plannen de coroutine nu expliciet vanuit de Home Assistant event loop en krijgen een herkenbare taaknaam.
- Versie verhoogd naar `0.0.1-alpha.59` in `manifest.json` en `const.py`.

## Ongewijzigd
- Geen wijzigingen aan Plan72-logica.
- Geen wijzigingen aan safety-charge drempel van 0,10 kWh.
- Geen wijzigingen aan Plan Store, Scheduler, Pre-Start, Safety Guard of Final Revalidation.
- Geen wijzigingen aan laad-/ontlaadstrategie, SOC-reserves, execution buffer of vermogenslimieten.
- Geen wijzigingen aan Stroomvoorspeller-afhandeling of EMS-Plan logging in deze release.

## Validatie
- Python compile-check op de complete `custom_components/anker_ems` map geslaagd.
- Te bevestigen in Home Assistant na installatie: geen nieuwe `Detected that custom integration 'anker_ems' calls hass.async_create_task from a thread other than the event loop` melding tijdens een execution/monitor-cyclus.
