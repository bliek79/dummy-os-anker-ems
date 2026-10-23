# Dummy OS EMS 0.0.1-alpha.83 — Feasible Safety-Charge Action Bridge

## Vastgesteld incident (23 oktober 2026)

De bestaande Plan72 is geldig en berekent veiligheidsladen, maar er ontstaan geen automatische planslots.
`Action Bridge Valid=off`, `candidate_count=9`, `invalid_candidate_count=1` en beide schrijf-/handoff-gates gesloten.
De tweede kandidaat vraagt **2,400 kWh** van 24 oktober **04:00–05:00 Nederlandse tijd** bij een ingestelde EMS-laadlimiet van **2.400 W**. Met twee minuten vaste omschakelruimte resteert 58 minuten. Benodigd was 2.482,8 W. De oorspronkelijke bridge stelde 2.400 W in, markeerde de kandidaat toch ongeldig (`required_power_above_limit`) en sloot vervolgens wegens één ongeldig toekomstig voorstel de **volledige** automatische Plan Store en Scheduler af.

## Veranderingen in alpha.83

1. **Haalbare gedeeltelijke veiligheidslading:** bij een fysiek haalbare resterende hoeveelheid begrenst de Action Bridge de gevraagde energie op `max_charge_power_w × (vensterduur − 2 min) / 1000`, afgerond naar beneden op 0,001 kWh. Geen hoger vermogen, geen langer prijsvenster, geen kunstmatige extra lading.
2. **Concreet geval:** `requested_energy_kwh=2.400`; `planned_energy_kwh=2.320`; `energy_shortfall_kwh=0.080`; `power_w=2400`; de projecteerde doel-SOC wordt opnieuw uit de werkelijk geplande **2,320 kWh** berekend in plaats van uit 2,400 kWh. Deze 0,080 kWh is **niet geleverd, niet doorgeschoven als bewezen lading en niet stilzwijgend ingevuld**.
3. **Per actie valideren:** een latere ongeldige kandidaat houdt niet meer automatisch een eerder geldig veiligheidslaadplan tegen. Alleen een chronologische reeks van geldige voorstellen komt in aanmerking. Een ongeldige **eerste** actie blijft fail-closed. De Plan Store gebruikt de individuele `plan_store_write_permitted` en Scheduler `scheduler_handoff_permitted` gates ongewijzigd.
4. **Voorspellingsafhankelijkheid bewaken:** na de eerste gedeeltelijk begrensde actie worden *latere* kandidaten aangehouden totdat het native kwartier-herplan de werkelijke SOC kan verwerken. We geven ze niet mee op basis van een mogelijk te optimistische SOC-route.
5. **Diagnostiek:** `sensor.dummy_os_ems_bridge_candidates` en `sensor.dummy_os_ems_bridge_status` bevatten `capacity_limited_count`, `capacity_limited_candidates`, `unmet_requested_energy_kwh`, `invalid_candidates` en tellers voor later aangehouden acties. De oorspronkelijke 9 kandidaten blijven in het kandidatenoverzicht; de uitvoerbare slotpreview is afzonderlijk.
6. **Eenmalig expliciet opnieuw inschakelen:** doordat deze versie opnieuw fysieke automatische acties mogelijk maakt, zet de Automatic Execution-schakelaar na de upgrade een eerder opgeslagen **alpha.82 AAN** veilig terug naar **UIT**. De gebruiker moet na beoordeling expliciet opnieuw AAN zetten. Daarna kan de eigen alpha.83 herstelde stand normaal worden bewaard bij herstarts.

## Ongewijzigde contracten

- **Plannerbeleid bevroren:** `energy_need.py`, `planner_preview.py` en `planner_72h.py` zijn byte-voor-byte gelijk gebleven; native 15-minuten / 72-uur / 288 slots blijft ongewijzigd.
- **Beveiliging:** elektrische EMS-maxgrenzen, minimale SOC, de Safety Guard, pre-start- en post-mode-validatie, legacy authority fence en handmatige voorrang blijven actief.
- **Alpha.82:** dynamisch Anker `number.max` bij laden, gecontroleerde vermogensaanpassing, noodstopresetknop, automatische audits blijven behouden.
- **Niet gewijzigd:** DOEMS, Dummy OS Data, de bestaande dashboardconfiguratie, Google Sheets of oudere executiehistorie.

## Tests vóór publicatie

- Reproductie van negen kandidaten met 1 kandidaat die oorspronkelijk 2,400 kWh/2.400 W in 58 minuten vroeg.
- Bevestigen dat 2,320 kWh bij 2.400 W haalbaar wordt, met 0,080 kWh zichtbaar tekort, doel-SOC aangepast en latere afhankelijkheden aangehouden.
- Negatieve gevallen: eerste kandidaat ongeldig, ontbrekende SOC, te kort tijdvenster, niet-overschrijfbaar handmatig slot.
- Vorige alpha.82 fysieke-fail-safe-tests en bevroren plannerhashes.
- Volledige `unittest`- en `pytest`-sets, Hassfest en HACS (PR), archive byte-verificatie (release).

## Installeren en live valideren

1. Zet **Automatic Execution UIT** en controleer je Home Assistant-back-up.
2. Installeer via HACS of vervang de **hele** `custom_components/anker_ems`-map met de release-ZIP; herstart Home Assistant.
3. Controleer versie `0.0.1-alpha.83`. De Automatic Execution-schakelaar hoort wegens eenmalige nieuwe-armbeveiliging **UIT** te blijven.
4. Bekijk `sensor.dummy_os_ems_bridge_candidates`: de te krappe 2,400 kWh-actie is nu een geldige gedeeltelijke actie met zichtbaar tekort, **indien** de forecast ongewijzigd blijft.
5. Bekijk `sensor.dummy_os_ems_bridge_valid`, `sensor.dummy_os_ems_bridge_status` en `sensor.dummy_os_ems_bridge_slots`: geldige voorstellen moeten door de Plan Store en Scheduler kunnen worden verwerkt zonder een globale `blocked_invalid_candidates`.
6. Controleer zonder fysieke uitvoering dat het volgende planslot geldig is en de veiligheidsgates passend reageren. Pas daarna, onder toezicht, Automatic Execution bewust opnieuw aanzetten.
7. Controleer werkelijke SOC en energielevering na iedere actie; valideer of het onvervulde deel bij een volgende herplanning zichtbaar en correct behandeld blijft. De planner herschikt het tekort niet vooraf gegarandeerd.

**Status bij publicatie: statische/CI-tests; live Home Assistant-validatie nog uit te voeren.**

