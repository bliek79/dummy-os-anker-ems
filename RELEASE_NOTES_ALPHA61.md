# Dummy OS EMS 0.0.1-alpha.61

Gerichte safety-recovery hotfix voor een logische deadlock waarbij een onveilige execution buffer juist de noodzakelijke veiligheidslaadactie blokkeerde.

## Gewijzigd
- `planner_action_bridge.py` gebruikt bij een onveilige execution buffer een expliciete recovery-modus.
- In recovery-modus worden uitsluitend noodzakelijke `veiligheidsladen`-acties uit Plan72 naar de Plan Store/Scheduler doorgelaten.
- Handelsladen en netontladen blijven geblokkeerd zolang de execution buffer onveilig is.
- Een gecombineerd `veiligheidsladen+handelsladen`-uur wordt in recovery-modus beperkt tot alleen het safety-charge-deel; handelsenergie wordt niet meegenomen.
- `coordinator.py`, `prestart_validator.py`, `safety_guard.py` en `execution.py` herkennen een veiligheidslaadactie als toegestane herstelactie wanneer de execution buffer al onveilig is.

## Opgelost
- Een onveilige execution buffer kon voor alpha61 de Automatic Plan Bridge volledig blokkeren voordat de door Plan72 berekende veiligheidslading een planslot kon bereiken.
- Dezelfde buffercheck kon vervolgens ook in pre-start, Safety Guard, shadow gate en final revalidation de herstelactie blokkeren.
- Hierdoor kon de batterij verder ontladen terwijl Plan72 al een steeds grotere veiligheidslaadbehoefte berekende.
- De execution buffer blijft een harde blokkade voor economische laad- en ontlaadacties, maar niet meer voor de veiligheidslaadactie die de buffer zelf herstelt.

## Ongewijzigd
- Dynamische reserveberekening en execution buffer van 2 procentpunt.
- Safety-charge actionability threshold van 0,10 kWh.
- Plan72-plannerlogica en 72-uurs horizon.
- Handmatige plannen blijven voorrang houden op automatische plannen.
- Forecast-, prijs- en handelslogica buiten de recovery-uitzondering.
- Vermogenslimieten en doel-SOC-validatie.
- Two-stage Anker control-path readiness.
- Fail-safe terugkeer naar `self_consumption`.
- Alpha59 event-loop/thread-safety fix.
- Alpha60 Stroomvoorspeller fetchguard/cache-fix.

## Validatie
- Home Assistant volledig herstarten na installatie.
- Controleren dat Dummy OS EMS als `0.0.1-alpha.61` initialiseert.
- Bij een onveilige execution buffer én een Plan72 safety charge van minimaal 0,10 kWh moet de Automatic Plan Bridge een `veiligheidsladen`-kandidaat kunnen maken.
- Die veiligheidslaadactie moet een beschikbaar automatisch planslot kunnen bereiken en door Scheduler/pre-start/Safety Guard/final revalidation kunnen gaan als alle overige veiligheidsgates geldig zijn.
- Handelsladen en netontladen mogen niet via deze recovery-uitzondering worden uitgevoerd zolang de execution buffer onveilig is.
- Na voldoende veiligheidsladen moet de execution buffer weer veilig worden en blijft de normale automatische logica gelden.
- Controleren dat handmatige planslots niet worden overschreven.
