# Dummy OS EMS 0.0.1-alpha.84 — Herstel van het derde automatische planslot

## Aanleiding — live validatie op 23 oktober 2026

Bij alpha.83 berekent de 72-uursplanner negen automatische laadkandidaten, maar de Action Bridge toont er slechts twee. In Home Assistant is **planslot 1 actief**, **planslot 2 wachtend** en **planslot 3 leeg**. De tweede kandidaat vraagt **3,200 kWh** tussen 04:00 en 05:00 Nederlandse tijd op 24 oktober; met maximaal **3.200 W** en twee minuten omschakelruimte kan **3,093 kWh** worden ingepland. Alpha.83 begrenst deze lading terecht, maar de daarna toegevoegde blokkade (`first_limited_index`) houdt alle zeven latere kandidaten tegen en voorkomt het vullen van planslot 3.

## Gerichte correctie in alpha.84

1. De **extra alpha.83-blokkade van alle kandidaten na een begrensd laadvenster** is verwijderd. Een latere individueel geldige actie mag weer doorstromen naar een beschikbaar automatisch planslot.
2. **Drie planslots worden gebruikt waar mogelijk.** Een regressietest controleert exact de situatie: slot 1 actief, slot 2 automatisch pending, slot 3 vrij. De derde geldige laadactie krijgt toestemming om slot 3 te vullen.
3. **Geen verruiming van laadvermogen of laadvenster.** Voor de genoemde actie blijft `requested_energy_kwh=3.200`, `planned_energy_kwh=3.093` en `energy_shortfall_kwh=0.107` zichtbaar bij maximaal 3.200 W. De ontbrekende energie wordt niet als geladen beschouwd.
4. **Overige veiligheidscontroles blijven intact:** een werkelijk ongeldige kandidaat sluit zijn latere afhankelijkheden uit (chronologische validatie); een ongeldige eerste actie blijft fail-closed. Handmatige acties behouden voorrang, lopende automatische acties worden niet gedupliceerd, per-slot schrijf-/Scheduler-gates en de fysieke veiligheid/laatste validatie blijven van kracht. De dynamische Anker-limiet en noodstop uit alpha.82 blijven behouden.
5. Bestaand diagnoseveld `held_after_limited_count` blijft voor dashboardcompatibiliteit beschikbaar en meldt `0`.

## Herinschakelbeveiliging

Omdat meer automatische plannen uitvoerbaar worden, gebruikt alpha.84 een **nieuw Automatic Execution-armcontract**. De eerdere alpha.83-AAN-stand wordt bij upgrade niet stilzwijgend overgenomen. De gebruiker schakelt fysieke automatische uitvoering pas na het beoordelen van nieuwe plannen expliciet opnieuw in.

## Controle en testdekking

- Negen kandidaten, inclusief één begrensde laadactie; preview heeft weer drie geldige slots in plaats van twee.
- Live reproductie: actief slot 1, pending slot 2 en vrij slot 3, inclusief 0,107 kWh tekort.
- Negatieve gevallen: ongeldige eerste kandidaat, ontbrekende doel-SOC, fysiek onhaalbaar venster en niet-overschrijfbaar handmatig planslot.
- Bevroren Plan72-/Energy-Need-/Planner-Preview-bestanden worden via SHA256-tests gecontroleerd.
- Volledige Python unittest-/pytest-/compilatiecontrole, HACS en Hassfest; releaseworkflow maakt een byte-gecontroleerd installatiearchief en SHA256-checksum.

## Installatie en live validatie

1. **Niet updaten tijdens een actieve fysieke laad- of ontlaadactie.** Het herladen van de integratie kan een uitvoering als `integration_unload` afbreken. Laat de actie gecontroleerd aflopen of stop deze bewust via de bestaande EMS-stopknop; controleer daarna `self_consumption`.
2. Installeer alpha.84 via HACS, of gebruik het **volledige** installatie-ZIP van deze release. Herstart Home Assistant.
3. Controleer versie `0.0.1-alpha.84`. Laat **Automatic Execution UIT** totdat je de nieuwe automatische plannen hebt beoordeeld.
4. Controleer `sensor.dummy_os_ems_bridge_slots`: bij drie geschikte kandidaten en beschikbare slots hoort `slot_preview_count: 3`, `held_after_limited_count: 0` en een toewijzing aan planslot 3. De werkelijke planning hangt af van actuele forecast, SOC, geldigheid, handmatige en lopende acties.
5. Controleer in `sensor.dummy_os_ems_bridge_candidates` dat het tekort en de vermogensbegrenzing zichtbaar blijven en dat de geplande tijden niet onbedoeld overlappen.
6. Zet Automatic Execution desgewenst onder toezicht **bewust opnieuw AAN**. Controleer aangevraagd én daadwerkelijk laadvermogen, SOC-verloop en het rollend vullen van nieuwe slots.

## Architectuur, beperkingen en status

- De leidende architectuur blijft **native 15 minuten / 72 uur / 288 slots**; bestaande Plan72-prijs-/actieblokken gebruiken nog uurresolutie. De plankern is in alpha.84 **niet gewijzigd**.
- Deze correctie verwijdert uitsluitend de extra blokkade van latere kandidaten na een begrensde lading. Een voorspelde latere SOC kan daardoor van de werkelijkheid afwijken; bestaande kwartier-herplanning en veiligheidscontroles vlak voor fysieke start blijven noodzakelijk.
- **Status bij release: automatische CI geslaagd; fysieke livevalidatie in de Home Assistant-installatie nog open.**
- Google Sheets is uitsluitend gelezen; DOEMS en Dummy OS Data zijn niet gewijzigd.

