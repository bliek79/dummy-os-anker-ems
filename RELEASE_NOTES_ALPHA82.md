# Dummy OS EMS 0.0.1-alpha.82 — Dynamic Anker battery limits and emergency reset

## Aanleiding en beslissing
Op 22 oktober 2026 mislukten twee veiligheidslaadacties (2560 en 2620 W) doordat de Anker SOLIX bij een lage batterij-SOC tijdelijk maximaal 2408 W toestond. De alpha81-versie registreerde dit als emergency_stopped en bewaarde die inactieve laatste status na herstart. Beide verbeteringen zijn door de gebruiker goedgekeurd.

## Dynamische laadgrens bij fysieke uitvoering
- Lees op het moment van het fysieke laadcommando de actuele Number-entiteit, inclusief min, max en step. Stuur nooit meer vermogen dan oorspronkelijk gepland, de ingestelde EMS-limiet of de actuele batterijgrens.
- Bij 2620 W gepland en maximaal 2408 W toegestaan wordt maximaal 2408 W gestuurd (of de eerstvolgende lagere toegestane stap). Planning, doel-SOC en tijdvenster blijven gelijk; bij gereduceerd vermogen is het doel mogelijk niet tijdig haalbaar.
- Werkt voor zowel handmatige als automatische laadacties. Tijdens laden wordt de batterijgrens bij iedere monitorcyclus opnieuw gelezen; bij verandering wordt het vermogen veilig aangepast.
- Wanneer de batterij een waarde weigert doordat max intussen daalde, volgt maximaal één nieuwe poging met een strikt lager geldig vermogen. Bij ontbrekende/ongeldige limiet of mislukte retry volgt de bestaande veilige noodstop.
- Bewaar gevraagd vermogen, toegepast vermogen, actuele maximumlimiet, begrenzingsstatus en aanpassingen afzonderlijk in Execution Status en het automatische auditverleden.
- Ontlaadpad, SOC-grenzen, Planner72, duurvensters, 15-minuten tijdcontract en bevroren alpha80 beleidsbestanden zijn ongewijzigd.

## Noodstop bevestigen en status wissen
- Nieuwe knop: Dummy OS EMS Noodstop bevestigen, voorgestelde entity: button.dummy_os_ems_noodstop_bevestigen. Ook te bedienen met service anker_ems.reset_execution_status.
- Alleen toegestaan wanneer Execution Status emergency_stopped en niet actief is, er geen mode-switch/test loopt, Automatic Execution uitgeschakeld is en de batterij in self_consumption staat. Een beschikbaar extern vermogenssetpoint moet 0 W zijn.
- De reset stuurt geen enkel batterijcommando, herstart niets en activeert de automatische planner niet. Alleen de actuele status wordt idle; de oorspronkelijke oorzaak, stopdatum, last_result en runhistorie blijven bewaard.
- stop_error en actieve noodstopprocedures zijn niet resetbaar.

## Installatie en livevalidatie
1. Automatic Execution UIT laten en een werkende Home Assistant-back-up controleren.
2. Via HACS installeren, of de volledige custom_components/anker_ems-map vervangen door het archief. Herstart HA.
3. Controleer manifestversie alpha82; voeg de nieuwe knop aan het bestaande Lovelace-dashboard toe via Entiteiten.
4. Bevestig de oude noodstop uitsluitend bij de veilige voorwaarden; Execution Status wordt idle en historie blijft bewaard.
5. Test de dynamische vermogensbegrenzing gecontroleerd en met toezicht. Verifieer geplande en daadwerkelijk toegepaste watts en goede self_consumption-terugkeer.
6. Bij onverklaarbaar gedrag Automatic Execution uit, actueel setpoint en de integratielog controleren.

DOEMS, Dummy OS Data en Google Sheets zijn niet aangepast.
