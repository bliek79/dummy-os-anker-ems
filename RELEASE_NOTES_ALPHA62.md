# Dummy OS EMS 0.0.1-alpha.62 - Plan72 Execution Energy Fidelity Hotfix

## Samenvatting
Alpha62 corrigeert de vertaling van Plan72 naar fysieke automatische batterijacties. De expliciet door Plan72 geplande netenergie is voortaan leidend voor uitvoering, zodat een totaal geprojecteerde `soc_end` niet langer kan veroorzaken dat een safety-laadactie doorloopt of opvolgende duurdere uren meeneemt.

## Opgelost
- Automatische planneracties bewaren nu de exacte `planned_energy_kwh` en `planned_end_time` uit de Plan72-bridge.
- Het fysieke target-SOC wordt voor automatische netacties afgeleid uit uitsluitend de expliciet geplande grid-energie, batterijcapaciteit en laad-/ontlaadefficientie; het totale Plan72-uurveld `soc_end` is niet langer het fysieke uitvoertarget.
- Execution stopt een automatische actie normaal met `planned_energy_reached` zodra de geplande energie is geleverd.
- Een automatische prijsvensteractie mag niet voorbij `planned_end_time` doorlopen; als de energie niet tijdig geleverd kon worden stopt deze met `planned_window_ended` en wordt een volgende Plan72-herberekening leidend.
- De bridge reserveert 2 minuten van het resterende planvenster voor third-party-control handoff/stabilisatie en verhoogt binnen de hardwarelimiet het gevraagde vermogen zodat de geplande energie voor het einde van het gekozen prijsuur kan worden geleverd.
- De audit gebruikt voor automatische acties de echte geplande Plan72-energie in plaats van `vermogen x max_runtime`.

## Gewijzigd
- Plan Store en Scheduler dragen `planned_energy_kwh` en `planned_end_time` als planner-metadata mee.
- `max_runtime_h` blijft een harde veiligheidsgrens, maar is niet langer het normale primaire stopcriterium voor automatische planneracties.

## Ongewijzigd
- Alpha61 buffer-recovery: veiligheidsladen blijft toegestaan wanneer de execution buffer al onveilig is; handelsladen en netontladen blijven dan geblokkeerd.
- Minimum actionable safety charge blijft 0,10 kWh.
- Manual plans, hardware minimum-SOC, software reserve, +2 procentpunt execution buffer, 72-uursplanner, prijsbronnen en third-party-control veiligheidsketen zijn niet inhoudelijk gewijzigd.
- Automatische ontlading is met deze release nog niet als live end-to-end geval gevalideerd.

## Technische oorzaak
De Plan72 bridge gebruikte `soc_end` van de laatste uurregel rechtstreeks als `target_soc`, terwijl `soc_end` alle energiestromen van dat uur bevat. Het fysieke laadvermogen werd daarentegen alleen berekend uit `charge_from_grid_safety_kwh` / `charge_from_grid_trade_kwh`. Daardoor kon het target fysiek niet passen bij de geplande netenergie en eindigden correcte laadacties met `max_runtime_reached` of liepen ze door naar opvolgende uren.

## Validatie
- Python compileall: geslaagd.
- Gerichte bridge-test: 0,940 kWh safety-lading vanaf 65% SOC leidt bij 7,2 kWh en 92% efficiency tot circa 77,0% fysiek target, niet meer tot het totale Plan72 `soc_end` van 95,9%.
- Gerichte bridge-test bevestigt `planned_energy_kwh = 0.940`, prijsvenster-einde en verhoogd uitvoervermogen met 2 minuten handoff-reserve.
- Live Home Assistant-validatie na installatie blijft vereist voor `planned_energy_reached`, prijsvenster-einde, normale terugkeer naar `self_consumption` en economische uurkeuze.
