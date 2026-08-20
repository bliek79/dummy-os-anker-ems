# Changelog

## 0.0.1-alpha.35 - Scheduler to Safety Guard Handoff

- Adds the first automatic, non-actuating handoff from a Scheduler-ready planner-owned plan to the Safety Guard layer.
- Requires the authoritative pre-start gate to be active and safe before Safety Guard handoff can pass.
- Revalidates planner identity continuity, Action Bridge validity, forecast readiness, execution-buffer safety, action, power, SOC, target SOC and conflicting battery power.
- Verifies that all three configured control-path entities exist in the integration configuration without requiring `third_party_control` to be active yet.
- Blocks handoff while a physical test or another execution is active, preserving the one-controller-at-a-time principle before physical automation is enabled.
- Exposes handoff status, reasons, warnings, selected slot, identity and control-path readiness through the existing Action Candidates attributes.
- A changed planner signature remains a warning when stable planner identity still matches.
- Automatic Execution Controller handoff and physical battery commands remain disabled.
- Runtime bridge note is now version-neutral instead of carrying an old alpha number.
- Entity count remains unchanged at 105.

## 0.0.1-alpha.34 - Time-Aware Pre-Start Diagnostics

- Separated continuous early diagnostics from the authoritative Scheduler-ready pre-start gate.
- Added explicit diagnostic phase (`early`, `near_start`, `due`) and non-authoritative status metadata.
- Current SOC direction and execution-reserve failures are warnings while a plan is outside the live pre-start decision window.
- The same SOC checks become hard blockers inside the decision window and remain hard blockers for the real Scheduler-ready pre-start gate.
- Added diagnostic metadata for whether live SOC is currently enforced and the active decision-window duration.
- Dry-run safety tests now respect the same time relevance as the continuous diagnostic.
- Automatic physical execution remains disabled.
- Entity count remains unchanged at 105.
- Reworked README into a compact current-state guide; alpha-by-alpha history now remains in CHANGELOG and GitHub Releases only.

## 0.0.1-alpha.33 - Pre-Start Diagnostics & Testability

- Adds continuous dry-run pre-start diagnostics for the nearest future planner-owned pending plan.
- Exposes every individual pre-start check as structured attributes on the existing Action Candidates sensor.
- Adds diagnostic slot, start time, minutes-to-start, SOC, target SOC, execution reserve, identity/signature match, blockers and warnings.
- Adds an in-memory dry-run test matrix for current conditions plus forecast-not-ready, unsafe execution-buffer and invalid-planner scenarios.
- Keeps the actual Scheduler-ready pre-start gate unchanged in safety intent.
- No physical battery commands are enabled; automatic execution remains disabled.
- No new Home Assistant entities; entity count remains 105.

## 0.0.1-alpha.32 - Pre-Start Safety Validation

- Adds a dedicated observational pre-start safety gate for automatic Scheduler-ready plans.
- Revalidates the current 72-hour planner validity, forecast readiness, 2% execution buffer and Action Bridge validity immediately before an automatic plan would be eligible for execution.
- Requires the Scheduler-selected automatic plan to still exist in the current rolling planner by stable `planner_identity`.
- Rechecks current SOC against the stored target SOC and, for discharge actions, the current execution-reserve floor.
- Reports a changed planner revision/signature as a warning while stable planner identity remains the hard continuity requirement.
- Exposes pre-start diagnostics through the existing Action Bridge entity attributes; no new Home Assistant entities are added.
- Automatic physical execution remains disabled and no Anker command is sent by the new validator.
- Entity count remains unchanged at 105.

## 0.0.1-alpha.31 - Automatic Pending Plan Reconciliation

- Separates stable `planner_identity` from mutable `planner_signature`.
- Matches planner-owned pending plans by action identity instead of exact forecast revision.
- Reconciles future pending plans when target SOC, power or expected energy changes.
- Clears stale future planner-owned pending plans that disappear from the rolling 72-hour preview.
- Freezes automatic plans at their planned start so Scheduler-ready/due plans are not rewritten.
- Keeps manual/user-edited plans protected.
- Scheduler handoff remains enabled; automatic physical execution remains disabled.
- Entity count remains unchanged.

# 0.0.1-alpha.30

## Controlled Scheduler Handoff

- Adds the first automatic handoff from validated planner-owned Plan Store concepts to Scheduler-visible `pending` plans.
- Handoff is allowed only when the 72-hour plan is valid, the 2% execution buffer is safe, forecast sources are ready, all bridge candidates are valid, and the persistent planner signature still exactly matches the current proposal.
- Planner-owned pending slots are matched by signature on later refreshes so they are not misreported as manual conflicts.
- Manual/user-edited plans remain protected and are never promoted automatically.
- Automatic physical execution remains disabled; alpha30 stops at Scheduler handoff.
- Empty planner slots are reset with neutral/manual origin instead of retaining `automatic_72h_planner`.
- Adds bridge attributes for Scheduler handoff gate, changed state, handed-off slots and skipped slots.
- Entity count remains unchanged at 105.

# 0.0.1-alpha.29

## Controlled Automatic Plan Store Write

- The validated 72-hour Action Bridge can now persist automatic proposals into reusable Plan Store slots.
- Automatic plans are always stored with lifecycle `concept`; Scheduler handoff remains disabled and no physical execution can start from this automatic write path.
- Existing active/actionable manual plans keep priority and are never overwritten.
- Cancelled, completed, failed and empty slots remain reusable as established in alpha28.
- Planner-owned concept slots can be refreshed by the rolling automatic preview. A user edit immediately claims that slot back as `manual`.
- Stale planner-owned slots are cleared when the rolling preview no longer needs them.
- Writes are idempotent through a planner signature to avoid persistent-storage writes on every 10-second coordinator refresh.
- Existing bridge entities expose write-gate state plus written, cleared and skipped slot diagnostics; no new entities are added. Entity count remains 105.
- Alpha27 Forward Reserve Precharge and the 2% execution buffer remain required gates before automatic Plan Store write is allowed.

## Safety gates

Automatic Plan Store write requires:

- valid 72-hour plan;
- safe execution buffer;
- ready forecast sources;
- zero invalid action candidates;
- a reusable slot for the candidate.

Still disabled in alpha29:

- Scheduler handoff;
- automatic lifecycle promotion to `pending`;
- automatic physical charge/discharge execution.

# 0.0.1-alpha.28

## English entity naming cleanup
- All 105 Dummy OS EMS entities now use English technical display names.
- Entity IDs are shortened to consistent English object IDs such as `plan72_exec_margin`, `bridge_candidates` and `plan_1_power`.
- Existing unique IDs are intentionally unchanged. Alpha28 migrates registered entity IDs during config-entry setup so the same registry entities are retained.
- Internal planner/store field names and existing plan option/state values are not migrated in this alpha; this avoids mixing a naming cleanup with behavioural state migration.

## Manual plan-slot lifecycle fix
- Cancelled (`geannuleerd`), completed (`voltooid`) and failed (`fout`) plans no longer keep a manual planslot permanently occupied for the automatic bridge preview.
- Empty/no-action slots remain reusable.
- Active or still actionable manual plans remain protected and are never considered available for automatic overwrite.
- With two cancelled slots and one empty slot, `available_manual_slots` should now become 3 and `manual_slot_conflict_count` should become 0.

## Safety unchanged
- Automatic Plan Store writes remain disabled.
- Scheduler handoff remains disabled.
- Automatic execution remains disabled.
- The alpha27 Forward Reserve Precharge and 2% execution buffer remain unchanged.

## Validation
- Confirm Home Assistant still exposes exactly 105 Dummy OS EMS entities.
- Confirm technical entity IDs are English and shortened.
- Confirm the action bridge reports cancelled/completed slots as available.
- Confirm `available_manual_slots: 3`, `manual_slot_conflict: false` and `manual_slot_conflict_count: 0` in the current validation scenario.
- Confirm planner buffer remains safe with zero breach hours before any later Plan Store-write work.

# 0.0.1-alpha.27

## Forward Reserve Precharge
- Correctie van een timingfout in de dynamische veiligheidslading die in alpha26 zichtbaar werd bij een plotselinge stijging van de uitvoeringsreserve.
- De planner behandelt de reserve die na een uur geldt nu als een echte einde-van-uur deadline.
- Een toekomstige reservepiek moet daardoor al aan het einde van het voorafgaande planningsuur haalbaar zijn en wordt niet meer pas in het volgende uur gecorrigeerd.
- Voor elke aantoonbare toekomstige uitvoeringsreservepiek wordt vooraf berekend hoeveel opgeslagen energie beschikbaar zal zijn uit start-SOC en gratis zonne-overschot.
- Alleen het resterende tekort wordt als veiligheidslading uit het net gepland.
- Dat tekort wordt verdeeld over de goedkoopste technisch haalbare uren vóór of op de reserve-deadline.
- De 2 procentpunt uitvoeringsbuffer uit alpha25 blijft ongewijzigd.
- Horizon-fallback zonder aantoonbare volgende bruikbare zonneperiode blijft behouden en creëert geen kunstmatige extra netlading.

## Actiebrug
- De observerende planner-naar-planslot brug uit alpha26 blijft aanwezig.
- De brug blijft blokkeren zolang `execution_buffer_safe=false`.
- Zodra de 72-uursplanner weer een veilige buffer berekent, kan de brug automatisch de netlaad-/netontlaadkandidaten tonen.

## Veiligheid
- `plan_store_write_enabled=false`.
- `scheduler_handoff_enabled=false`.
- `execution_enabled=false`.
- Geen automatische planslot-write en geen fysieke batterijaansturing.

## Te valideren
- `execution_buffer_breach_hours` moet bij een technisch haalbaar plan terug naar 0.
- `min_execution_headroom_soc` mag niet negatief zijn.
- `Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig` moet dan `on` worden.
- De eerder waargenomen reservepiek rond een einde-van-uur overgang mag niet meer één uur te laat worden aangevuld.
- Veiligheidslading mag alleen toenemen met de hoeveelheid die nodig is om de toekomstige reserve op tijd te halen.
- Na een veilige plannerbuffer moet de alpha26 actiebrug weer actiekandidaten kunnen produceren.
- Automatische fysieke uitvoering moet uitgeschakeld blijven.

# 0.0.1-alpha.26

## Observerende planner-naar-planslot brug
- Nieuwe `planner_action_bridge` vertaalt de 72-uurs planneroutput naar concrete uitvoerbare voorstellen.
- Alleen geforceerde acties worden vertaald:
  - veiligheidsladen uit het net;
  - handelsladen uit het net;
  - handelsontladen naar het net.
- Zonneladen en woningontlading blijven onder normale `self_consumption` en worden niet als planslot aangemaakt.
- Opeenvolgende uren met dezelfde actie en hetzelfde doel worden samengevoegd.
- Per voorstel worden onder andere starttijd, eindtijd, vermogen, doel-SOC, looptijd en verwachte energie berekend.
- De eerstvolgende maximaal drie acties vormen een rolling 3-slot preview.
- Extra toekomstige acties blijven zichtbaar als overflow-kandidaten.
- Bestaande handmatige planslots worden als leidend behandeld en nooit automatisch overschreven.

## Nieuwe entiteiten
- Dummy OS EMS Automatische actiebrug status.
- Dummy OS EMS Automatische actiekandidaten.
- Dummy OS EMS Automatische planslot preview.
- Dummy OS EMS Automatisch voorstel plan 1.
- Dummy OS EMS Automatisch voorstel plan 2.
- Dummy OS EMS Automatisch voorstel plan 3.
- Dummy OS EMS Automatische actiebrug geldig.

## Veiligheid
- De 2% uitvoeringsbuffer uit alpha25 blijft volledig actief.
- De brug blokkeert bij een ongeldig 72-uursplan of een onveilige uitvoeringsbuffer.
- Handmatige planslots worden niet overschreven.
- `plan_store_write_enabled=false`.
- `scheduler_handoff_enabled=false`.
- `execution_enabled=false`.
- Geen fysieke batterijaansturing vanuit de automatische planner.

## Te valideren
- De actiebrug moet `ready_preview`, `idle_no_forced_actions` of een duidelijke blokkeerstatus tonen.
- Netveiligheidsladen moet als `laden` / `veiligheidsladen` verschijnen.
- Handelsontladen moet als `ontladen` / `handel_ontladen` verschijnen.
- Zonneladen en woningontlading mogen niet als automatische planslotactie verschijnen.
- De eerste drie toekomstige geforceerde acties moeten in voorstel plan 1 t/m 3 staan.
- Bij meer dan drie acties moet `overflow_count` groter dan 0 worden.
- Bestaande handmatige plannen mogen alleen een conflictstatus opleveren en nooit gewijzigd worden.
- Geen Scheduler- of fysieke uitvoering mag automatisch starten.

# 0.0.1-alpha.25

## Uitvoeringsbuffer voor toekomstige automatische uitvoering
- Standaard 2 procentpunt SOC operationele buffer boven de berekende dynamische reserve.
- De inhoudelijke dynamische reserve blijft ongewijzigd en afzonderlijk zichtbaar.
- Veiligheidsladen wordt nu gepland tegen de gebufferde uitvoeringsreserve.
- Woning- en handelsontlading mogen de gebufferde uitvoeringsreserve niet onderschrijden.
- Per planuur toegevoegd:
  - `execution_reserve_floor_start_soc`
  - `execution_reserve_floor_soc`
  - `execution_buffer_percent`
  - `execution_headroom_soc`
- Nieuwe samenvattende diagnose voor minimale uitvoeringsmarge en bufferonderschrijdingen.
- Nieuwe sensor: Dummy OS EMS Automatisch plan uitvoeringsreserve.
- Nieuwe sensor: Dummy OS EMS Automatisch plan minimale uitvoeringsmarge.
- Nieuwe sensor: Dummy OS EMS Automatisch plan bufferonderschrijding.
- Nieuwe binary sensor: Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig.

## README
- De vaste EMS-besturingsfilosofie is expliciet opgenomen: nul op de meter eerst,
  daarna tekortgestuurd goedkoop netladen, dure netafname vermijden en alleen
  werkelijk vrije energie financieel zinvol verkopen.

## Ongewijzigd
- Planner blijft observerend.
- `execution_enabled=false`.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep vanuit de 72-uurs planner.
- Geen fysieke batterijaansturing vanuit de automatische planner.

## Te valideren
- `execution_buffer_percent` moet 2,0% tonen.
- De uitvoeringsreserve moet normaal 2 procentpunt boven de dynamische reserve liggen,
  behalve wanneer 100% SOC de bovengrens vormt.
- `execution_buffer_breach_hours` hoort bij een uitvoerbaar plan 0 te zijn.
- `Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig` hoort dan aan te staan.
- Veiligheidslading mag iets toenemen wanneer dat nodig is om de extra buffer te bewaken.
- Geen enkele automatische fysieke actie mag door deze alpha worden gestart.

# 0.0.1-alpha.24.4

## Correctie dynamische reserve
- `next_usable_solar: null` wordt niet meer geïnterpreteerd als bewijs dat er
  binnen de toekomst geen bruikbare zon meer komt.
- Bij een onvolledige solarhorizon valt de reserve terug op:
  5% apparaatgrens + softwarematige veiligheidsreserve.
- De resterende woningforecast wordt dan niet meer volledig opgestapeld tot
  een kunstmatige 100% reserve.
- Nieuwe diagnosevelden:
  - `solar_horizon_complete`
  - `solar_horizon_incomplete_hours`
  - per planuur `solar_horizon_complete`

## Goedkoopste noodzakelijke veiligheidsuren
- Dynamische veiligheidslading wordt vooraf gepland.
- Voor elk aantoonbaar reservepiekmoment wordt alleen het werkelijk benodigde
  energietekort bepaald.
- De planner selecteert vervolgens de goedkoopste haalbare uren vóór dat
  tekortmoment.
- Maximaal laadvermogen en laadrendement blijven onderdeel van de selectie.
- Veiligheidslading blijft gescheiden van handelslading.

## Nieuwe entiteiten
- Dummy OS EMS Automatisch plan solarhorizon
- Dummy OS EMS Automatisch plan solarhorizon ontbrekende uren

## Ongewijzigd
- Solar Charge Delay blijft actief.
- Handelsreserve-logica blijft actief.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Reserve mag bij ontbrekende toekomstige solar niet meer naar 100% springen.
- `solarhorizon` moet `onvolledig` aangeven wanneer de resterende forecast geen
  volgende bruikbare zonneperiode bevat.
- Veiligheidslading moet naar goedkopere beschikbare uren verschuiven wanneer
  het tekort pas later optreedt.
- Alleen de benodigde hoeveelheid veiligheidsenergie mag worden gepland.
- SOC en dynamische reserve moeten gedurende de volledige horizon consistent
  blijven.

# 0.0.1-alpha.24.3

## Dynamische 72-uurs reserve
- Reservevloer wordt nu voor ieder forecastuur opnieuw berekend.
- Dezelfde bruikbare-zonregel als alpha21 wordt gebruikt:
  eerste van twee opeenvolgende uren waarin solar >= woningverbruik.
- Woningbehoefte tot de volgende bruikbare zonneperiode wordt per uur bepaald.
- Ontlaadrendement wordt meegenomen bij de benodigde opgeslagen energie.
- 5% apparaatgrens en softwarematige veiligheidsreserve blijven onderdeel van
  de reservevloer.
- Woningontlading en handelsontlading mogen de dynamische reserve niet
  onderschrijden.
- Observerende veiligheidslading kan worden toegevoegd wanneer de opgeslagen
  energie na zonnelading onder de actuele dynamische reservebehoefte ligt.
- Nieuwe planvelden:
  - `reserve_floor_start_soc`
  - `reserve_floor_soc`
  - `dynamic_need_until_solar_kwh`
  - `dynamic_need_after_hour_kwh`
  - `next_usable_solar`
- Nieuwe sensoren:
  - Dummy OS EMS Automatisch plan dynamische reserve
  - Dummy OS EMS Automatisch plan maximale reserve

## Ongewijzigd
- Solar Charge Delay uit alpha24.1 blijft actief.
- Handelsreserve-logica blijft actief.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Reservevloer moet door de 72 uur heen zichtbaar veranderen.
- Reserve moet in de avond/nacht oplopen wanneer meer energie nodig is tot
  de volgende bruikbare zon.
- Reserve moet terugvallen wanneer bruikbare solar beschikbaar wordt.
- SOC mag na woning- of handelsontlading niet onder de dynamische reserve komen.
- Eventuele veiligheidslading moet alleen ontstaan wanneer de actuele
  batterijvoorraad werkelijk onvoldoende is voor behoefte plus reserve.

# 0.0.1-alpha.24.2

## Hotfix
- Runtime `NameError` in `planner_72h.py` opgelost.
- Verwijderde variabele `trade_charge_stored` werd nog gebruikt in de
  samenvattende uitvoer van de 72-uurs planner.
- `auto_plan_72h_trade_charge_stored_kwh` wordt nu berekend als:
  geplande handelsnetlading × laadrendement.
- Hierdoor kan de coordinator weer normaal vernieuwen en worden de
  Dummy OS EMS-entiteiten opnieuw beschikbaar.

## Functioneel
- De Solar Charge Delay- en handelsreservecorrecties uit alpha24.1 blijven
  ongewijzigd.
- Geen wijziging aan fysieke besturing of Scheduler.

# 0.0.1-alpha.24.1

## Correctie op alpha24
- Solar Charge Delay nu daadwerkelijk toegepast op handelsladen.
- Geen handelslading uit het net wanneer verwacht solaroverschot vóór het
  geselecteerde handelsontlaaduur de benodigde batterijruimte kan vullen.
- Handelsladen wordt beperkt tot de vrije capaciteit die naar verwachting niet
  door gratis zonne-energie wordt gevuld.
- Handelsenergie wordt als tijdelijke reserve bijgehouden.
- Woningontlading mag deze handelsreserve niet meer automatisch in
  financieel minder interessante uren opmaken.
- De handelsreserve mag wel voor de woning worden gebruikt wanneer het actuele
  tarief minimaal gelijkwaardig is aan de effectieve laadkost plus de ingestelde
  minimum handelsmarge.
- Op het gekozen handelsontlaaduur heeft woningverbruik eerst prioriteit; alleen
  resterend ontlaadvermogen/energie wordt naar het net gestuurd.
- Per planuur nieuw attribuut `trade_reserved_kwh` voor diagnose.

## Veiligheid
- Nog steeds uitsluitend observerend.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Het eerder waargenomen handelsladen vlak vóór een grote zonnepiek moet
  verdwijnen of sterk afnemen.
- Solar Charge Delay moet voorkomen dat netgeladen energie kort daarna vrije
  zonnelading verdringt.
- Handelsenergie mag niet in goedkope tussenuren voor woningverbruik verdwijnen.
- SOC-keten moet 72 uur aaneengesloten blijven.
- Reservevloer moet intact blijven.

# 0.0.1-alpha.24

## Toegevoegd
- Eerste volledige, doorlopende automatische 72-uurs planpreview.
- Sequentiële SOC-berekening per forecastuur.
- Batterijcapaciteit 7,2 kWh en 5% absolute ondergrens.
- Softwarematige veiligheidsreserve wordt gedurende de planning bewaakt.
- Solar dekt eerst woningverbruik; overschot kan de batterij laden.
- Veiligheidslading uit alpha21/22 wordt in de 72-uurs preview geplaatst.
- Financieel beste handelslaaduur uit alpha23 kan observerend worden ingepland.
- Financieel beste handelsontlaaduur uit alpha23 kan observerend worden ingepland.
- Woningtekort kan uit de batterij worden gedekt zolang de reserve intact blijft.
- Laadlimiet 3,5 kW en ontlaadlimiet 3,0 kW.
- Laad- en ontlaadverliezen worden in het SOC-pad verwerkt.
- Volledige uurreeks wordt gepubliceerd in het `plan`-attribuut.

## Nieuwe entiteiten
- Dummy OS EMS Automatisch plan 72u status
- Dummy OS EMS Automatisch plan 72u
- Dummy OS EMS Automatisch plan eind-SOC
- Dummy OS EMS Automatisch plan minimum-SOC
- Dummy OS EMS Automatisch plan zonnelading
- Dummy OS EMS Automatisch plan veiligheidslading
- Dummy OS EMS Automatisch plan handelslading
- Dummy OS EMS Automatisch plan ontladen woning
- Dummy OS EMS Automatisch plan ontladen net
- Dummy OS EMS Automatisch plan 72u geldig

## Veiligheid
- Geen automatische plancreatie in de drie planslots.
- Geen Scheduler-aanroep vanuit de 72-uurs planner.
- Geen fysieke batterijaansturing vanuit de 72-uurs planner.
- Bestaande handmatige besturingsketen blijft ongewijzigd.

## Te valideren
- Plan bevat maximaal 72 chronologische uren.
- SOC blijft tussen 5% en 100%.
- Reservevloer wordt niet door normale woning-/handelsontlading onderschreden.
- Zonnelading, veiligheidslading en handelslading worden apart zichtbaar.
- Laad- en ontlaadlimieten worden per uur gerespecteerd.
- Eind-SOC komt overeen met het laatste planuur.
- Plan-attribuut blijft stabiel beschikbaar in Home Assistant.

# 0.0.1-alpha.23

## Toegevoegd / gewijzigd
- Observerende financiële handelslogica bovenop de alpha22 Planner Decision Preview.
- Configureerbaar laadrendement, standaard 92%.
- Configureerbaar ontlaadrendement, standaard 92%.
- Configureerbare minimale netto handelsmarge, standaard € 0,10/kWh.
- Roundtrip-rendement wordt expliciet berekend.
- Effectieve laadkost wordt gecorrigeerd voor laad- én ontlaadverliezen.
- Alle toekomstige prijsuren worden als laad/ontlaad-combinatie vergeleken.
- Beste handelslaaduur en beste handelsontlaaduur worden gepubliceerd.
- Verwachte netto handelsmarge wordt gepubliceerd.
- Nieuwe binary sensor `Dummy OS EMS Handel rendabel`.
- Plannerbeslissing kan observerend `handelsladen` of `ontladen` aangeven wanneer het huidige uur financieel het beste uur is en de veiligheidsvoorwaarden dit toelaten.
- Veiligheidslading blijft altijd leidend boven handel.

## Nieuwe entiteiten
- Dummy OS EMS Planner roundtrip rendement
- Dummy OS EMS Effectieve laadkost
- Dummy OS EMS Verwachte handelsmarge
- Dummy OS EMS Minimale handelsmarge
- Dummy OS EMS Beste handelslaaduur
- Dummy OS EMS Beste handelslaadprijs
- Dummy OS EMS Beste handelsontlaaduur
- Dummy OS EMS Beste handelsontlaadprijs
- Dummy OS EMS Handel rendabel

## Veiligheid
- Nog geen automatische plancreatie.
- Nog geen nieuwe fysieke handelsuitvoering.
- Bestaande Scheduler, Safety Guard, Action Controller en Execution Controller blijven ongewijzigd.

## Te valideren
- Roundtrip-rendement bij 92% / 92% moet 84,6% zijn.
- Effectieve laadkost en verwachte handelsmarge controleren tegen actuele prijsuren.
- Beste laad- en ontlaaduren controleren op chronologische volgorde.
- `Handel rendabel` moet alleen Aan zijn wanneer netto marge minimaal € 0,10/kWh bedraagt.
- Veiligheidslading moet handelslogica blijven overrulen.

# 0.0.1-alpha.22

## Toegevoegd / gewijzigd
- Nieuwe observerende `Planner Decision Preview` bovenop de alpha21-energiebalans.
- Plannerbeslissing en leesbare plannerreden.
- Vereiste minimum-SOC uit behoefte, 5% absolute ondergrens en softwarematige reserve.
- Energie boven reserve zichtbaar gemaakt voor latere handelslogica.
- Veiligheidslading als afzonderlijke plannerbeslissing.
- Goedkoopste benodigde kandidaat-laaduren tot bruikbare zon.
- Controle of voldoende laaduren beschikbaar zijn om het berekende tekort te dekken.
- `Solar Charge Delay` als observerende status wanneer netladen kan worden uitgesteld tot bruikbare zon.
- Observerende status voor mogelijke ontlading boven reserve.
- Observerende handelslading-kandidaat op basis van vrije capaciteit en forecast-prijsverschil.
- Planner prijsverschil en herplanreden als diagnosewaarden.

## Belangrijke begrenzing
- Alpha22 maakt nog geen automatische plannen aan.
- Alpha22 voert geen nieuwe fysieke acties uit.
- Handelslading is alleen een kandidaatstatus.
- Laadverlies, ontlaadverlies en minimale netto handelsmarge zijn nog niet gemodelleerd.
- Kandidaat-laaduren gebruiken maximaal 3500 W alleen voor een observatieve ureninschatting; dit is geen uitvoeringscommando.

## Nieuwe entiteiten
- Dummy OS EMS Planner preview status
- Dummy OS EMS Planner beslissing
- Dummy OS EMS Planner reden
- Dummy OS EMS Vereiste minimum-SOC
- Dummy OS EMS Energie boven reserve
- Dummy OS EMS Veiligheidslading nodig
- Dummy OS EMS Goedkoopste benodigde laaduren
- Dummy OS EMS Planner prijsverschil
- Dummy OS EMS Herplan reden
- Dummy OS EMS Planner veiligheidslading nodig
- Dummy OS EMS Planner handelslading kandidaat
- Dummy OS EMS Planner ontladen mogelijk
- Dummy OS EMS Solar Charge Delay

## Te valideren
- Plannerbeslissing gedurende zonnige uren.
- Omschakeling naar veiligheidsladen wanneer de behoefte tot bruikbare zon groter wordt dan beschikbare batterij-energie minus reserve.
- Selectie van de goedkoopste benodigde laaduren.
- Solar Charge Delay in de periode voor verwachte bruikbare zon.
- Gedrag van handels- en ontlaadkandidaten zonder dat deze fysieke acties veroorzaken.

# 0.0.1-alpha.21

## Toegevoegd
- Eerste **observatieve energiebalans** als rekenlaag voor de toekomstige automatische planner.
- Nieuwe berekening van netto energiebehoefte vanaf nu tot de eerstvolgende bruikbare zonneproductie.
- Bruikbare zon wordt in deze eerste versie gedefinieerd als het eerste van twee opeenvolgende forecasturen waarin `solar_kwh >= home_consumption_kwh`.
- Het resterende deel van het actuele uur wordt proportioneel meegenomen.
- Beschikbare batterij-energie wordt berekend boven de absolute 5% SOC-ondergrens op basis van 7,2 kWh batterijcapaciteit.
- Softwarematige veiligheidsreserve toegevoegd als configureerbare integratie-optie van 0-30%; standaard 7%.
- Berekening van benodigde aanvullende netlading.
- Berekening van vrije/verhandelbare batterij-energie boven behoefte plus reserve.
- Diagnose-/redenstatus voor de energiebalans.

## Nieuwe sensoren
- `Dummy OS EMS Energiebehoefte status`
- `Dummy OS EMS Energiebehoefte tot bruikbare zon`
- `Dummy OS EMS Beschikbare batterij-energie`
- `Dummy OS EMS Veiligheidsreserve`
- `Dummy OS EMS Benodigde aanvullende netlading`
- `Dummy OS EMS Vrije verhandelbare batterij-energie`
- `Dummy OS EMS Eerste bruikbare solar`
- `Dummy OS EMS Energiebehoefte reden`

## Veiligheid / scope
- De nieuwe energiebalans is **uitsluitend observerend**.
- Alpha21 maakt op basis hiervan nog geen automatische plannen aan.
- De bestaande Scheduler, Safety Guard, Action Controller en Execution Controller zijn niet gewijzigd door deze rekenlaag.
- De vaste hardwaregrens van 5% SOC blijft leidend.

## Te valideren
- Controleer of het eerste bruikbare solar-uur logisch overeenkomt met Solcast en de woningforecast.
- Controleer of de energiebehoefte afneemt naarmate de tijd richting bruikbare zon vordert.
- Controleer of beschikbare batterij-energie overeenkomt met SOC en 7,2 kWh capaciteit.
- Beoordeel gedurende meerdere situaties of benodigde netlading en vrije/verhandelbare energie logisch reageren.

# 0.0.1-alpha.20

## Toegevoegd / gewijzigd
- Gecontroleerde retry-logica voor geplande laad- en ontlaadacties.
- `max_start_delay` wordt nu daadwerkelijk gebruikt als startvenster voor tijdelijke startproblemen.
- Bij tijdelijke Anker-/besturingsvertraging wordt een gepland plan niet direct definitief afgebroken.
- Retry-interval: 10 seconden, nooit langer dan de resterende startmarge.
- Tussen mislukte pogingen wordt de bestaande safe-stop gebruikt en het plan alleen binnen het geldige startvenster opnieuw op `pending` gezet.
- Ondersteunde tijdelijke retry-redenen omvatten onder andere:
  - externe modus nog niet tijdig beschikbaar;
  - `control_sources_missing`;
  - `not_in_external_mode`;
  - `observation_sources_missing`;
  - tijdelijk tegengestelde laad-/ontlaadflow;
  - tijdelijk niet-gereed Action Controller.
- Buiten het startvenster of bij een niet-tijdelijke fout wordt niet opnieuw geprobeerd.

## Ongewijzigd
- Maximale startvertraging blijft per plan instelbaar op 1-120 minuten.
- Minimale looptijd blijft 15 minuten.
- Laden en ontladen gebruiken dezelfde Scheduler → Safety Guard → Action Controller → Execution Controller-keten.
- Safe-stop blijft 0 W zetten en terugkeren naar `self_consumption`.

## Te valideren
- Een gepland plan waarbij de Anker-besturingsentiteiten bij de eerste startpoging nog niet beschikbaar zijn, maar binnen `max_start_delay` alsnog gereed komen.
- Een gepland plan waarbij een tegengestelde batterijflow tijdelijk actief is en later binnen het startvenster verdwijnt.
- Geen automatische start meer nadat `max_start_delay` is verstreken.

# 0.0.1-alpha.19

## Toegevoegd / gewijzigd
- Normale fysieke ontlaaduitvoering vrijgegeven via de bestaande Execution Controller.
- Directe ontlaadplannen kunnen via `anker_ems.start_plan_now` worden uitgevoerd.
- Geplande ontlaadplannen worden bij `startklaar` automatisch overgedragen van Scheduler naar Execution Controller.
- Ontladen gebruikt dezelfde veilige modusovergang als laden: `self_consumption` → `third_party_control` → besturing beschikbaar → Safety Guard → fysieke uitvoering.
- Runtime-monitoring controleert nu per actie de juiste richting en tegengestelde energiestroom.
- Ontladen stopt normaal bij doel-SOC, minimale hardware-SOC van 5% of maximale looptijd.
- Safe-stop blijft 0 W zetten en terugkeren naar `self_consumption`.
- Reëel maximaal ontlaadvermogen wordt in de Safety Guard/Execution Controller begrensd op 3000 W.
- Minimale maximale looptijd verlaagd van 30 minuten naar **15 minuten (0,25 uur)**.
- Stapgrootte voor maximale looptijd verlaagd naar 15 minuten.

## Validatiestatus
- Gepland laden: fysiek end-to-end bevestigd in alpha17.
- Gecontroleerde fysieke ontlaadtest: bevestigd in alpha18.
- Normale geplande ontlaaduitvoering: te valideren in alpha19.

# 0.0.1-alpha.18

## Toegevoegd
- Expliciete service `anker_ems.start_discharge_test` voor een gecontroleerde fysieke ontlaadtest.
- Ontlaadtest is begrensd op 100-500 W en 10-120 seconden.
- Test vereist expliciete `confirm: true`, een startklaar ontlaadplan, simulatiemodus en vooraf geactiveerde `third_party_control`.
- Safety Guard moet de gekozen ontlaadactie vrijgeven voordat de fysieke test kan starten.
- De test bewaakt richting, tegengesteld laadvermogen, SOC, doel-SOC, testduur en besturingsbeschikbaarheid.
- Bij 5% SOC of het ingestelde ontlaaddoel stopt de test automatisch.
- Safe-stop zet het setpoint terug naar 0 W en keert terug naar `self_consumption`.
- Fysieke testdiagnostiek bevat nu ook de actieve testactie.

## Bewust nog niet gewijzigd
- De normale Execution Controller voert ontlaadplannen nog niet automatisch uit.
- Geplande ontlaadacties worden nog niet automatisch gestart.
- Pas na een geslaagde gecontroleerde ontlaadtest wordt automatische ontlaaduitvoering vrijgegeven.

# Changelog

## 0.0.1-alpha.17

- Fixed scheduled manual charge plans stopping at `startklaar` while `self_consumption` was active.
- A user-scheduled charge plan now automatically hands off from the Scheduler to the existing Execution Controller when its start window opens.
- The Execution Controller performs the proven automatic mode transition to `third_party_control`, waits for the Anker control entities, rechecks Safety Guard/Action Controller, and then starts charging.
- `Nu starten` remains an explicit direct action and is unchanged.
- Scheduled physical discharge remains intentionally disabled until the separate controlled discharge path has been validated.
- Prevents duplicate auto-start tasks while coordinator refreshes occur during the mode transition.

## 0.0.1-alpha.16

- Hotfix for alpha15 service registration.
- Fixes Home Assistant startup error: `ServiceRegistry.async_register() got multiple values for argument 'schema'`.
- No intended functional changes to the alpha15 manual plan controls.


## 0.0.1-alpha.15

- Added explicit manual plan controls: schedule, start now, cancel, and stop all.
- Plan edits now become `concept` first and are not scheduler-eligible until the user explicitly schedules or starts them.
- Existing plan lifecycle, safe execution, Source Monitor, and simulation-first architecture remain intact.


## 0.0.1-alpha.15

- Added persistent plan lifecycle states for the three manual plan slots.
- A physically started plan now becomes `actief` and is no longer selectable by the Scheduler.
- A normally finished plan becomes `voltooid`.
- A manually stopped plan becomes `geannuleerd`.
- An emergency/error stop becomes `fout`.
- Completed/cancelled/error plans remain terminal across Home Assistant restarts.
- Editing any plan field resets its lifecycle to `pending`, making that edited plan eligible for scheduling again.
- Prevents an already executed direct plan from remaining `startklaar` and being selected again.

## 0.0.1-alpha.13

- Added persistent Source Monitor for Solcast, Stroomvoorspeller, EnergyZero price data and price forecast updates.
- Tracks Home Assistant report moments separately from actual content changes.
- Keeps seven days of recent monitor events for later planner-trigger analysis.
- Adds one diagnostic entity: `Dummy OS EMS Bronmonitor`.
- Does not trigger replanning yet; this version only measures when source data really changes.


## 0.0.1-alpha.12

- Added explicit plan execution state machine via `anker_ems.execute_selected_plan`.
- Added automatic transition from `self_consumption` to `third_party_control`.
- Waits for Anker control entities to become available before setting direction and power.
- Re-validates Safety Guard and Action Controller after entering external mode.
- Monitors target SOC, maximum runtime, mode, direction and unexpected discharge during execution.
- Added guaranteed safe-stop back to 0 W and `self_consumption`.
- Added persistent restart recovery for an interrupted execution.
- Added execution status, remaining-time and active entities.
- Physical discharge remains blocked pending a separate controlled discharge test.
- Automatic 72-hour planner execution remains disabled; starting an existing selected plan still requires explicit confirmation.

## 0.0.1-alpha.11

- Fixed the physical test auto-stop path after the first 300 W / 120 s live test showed the countdown could reach 0 while the test remained running.
- Replaced the primary delayed stop callback with a dedicated fail-safe task tied to the absolute stop time.
- Added idempotent stop locking to prevent concurrent watchdog/manual stop races.
- The UI now enters `stopping` before the zero-setpoint and return to `self_consumption` are executed.
- Manual stop and restart recovery remain available as independent safety paths.


## 0.0.1-alpha.10

- Added non-actuating Action Controller.
- Added Safety Guard for selected scheduler plans.
- Added safety checks for source availability, SOC, target SOC, power and conflicting battery flow.
- Added semantic desired command attributes for later device-specific execution.
- Added Safety Guard and Action Controller status/binary sensors.
- Physical Anker writes remain disabled; alpha 8 is still safe simulation/observe preparation.

## 0.0.1-alpha.7

- Added simulation-only Scheduler on top of the persistent Plan Store.
- Scheduler evaluates all three plan slots every coordinator refresh.
- Scheduled plans become `startklaar` only inside their configured start window.
- Plans that miss `start_time + max_start_delay` become `verlopen`.
- Direct plans become immediately eligible for simulated scheduling.
- Deterministic conflict handling selects only one slot; other ready slots become `geblokkeerd`.
- Added `Dummy OS EMS Scheduler status`.
- Added `Dummy OS EMS Scheduler geselecteerd plan`.
- Added `Dummy OS EMS Scheduler startklaar`.
- Plan status sensors now expose Scheduler runtime state.
- Persistent plans are re-evaluated after Home Assistant restart.
- No Home Assistant service calls and no physical Anker writes are performed.

## 0.0.1-alpha.6

- Added persistent Plan Store with three independent plan slots.
- Added per-slot action and execution-mode select entities.
- Added per-slot start datetime.
- Added per-slot power, target SOC, maximum runtime and maximum start-delay number entities.
- Added per-slot validation/status sensor.
- Plan values survive Home Assistant restarts.
- No scheduler execution and no physical Anker control yet.


## 0.0.1-alpha.5

### Forecast Sources
- Eerste Python-gebaseerde forecastlaag toegevoegd.
- Bestaande prijs-, woningverbruiks- en Solcast-bronnen worden ingelezen.
- 72 uur wordt intern genormaliseerd naar één uurmodel met `time`, `price`, `price_min`, `price_max`, `price_source`, `solar_kwh` en `home_consumption_kwh`.
- Bekende prijzen krijgen voorrang op prijsprognoses voor hetzelfde uur.
- Nieuwe sensor `Dummy OS EMS Forecast status` publiceert diagnose-attributen en de genormaliseerde forecast.
- Nieuwe sensor `Dummy OS EMS Forecast complete uren` toont hoeveel uren alle drie de hoofdbronnen bevatten.
- Nieuwe binary sensor `Dummy OS EMS Forecast bronnen beschikbaar`.
- Forecastbronnen zijn via de integratie-opties selecteerbaar; bestaande config-entry blijft behouden.
- Veilige update-listener toegevoegd zodat gewijzigde opties de integratie herladen.
- Geen plannerbeslissingen en geen fysieke write-calls toegevoegd.

## 0.0.1-alpha.4

### GitHub/HACS basis
- Repositorystructuur voorbereid voor `dummy-os-anker-ems`.
- HACS-manifest toegevoegd.
- Home Assistant minimumversie vastgelegd op 2026.7.0.
- GitHub Actions toegevoegd voor HACS-validatie en hassfest.
- Issue templates toegevoegd.
- Onafhankelijkheids- en aansprakelijkheidsstatement toegevoegd.
- Alpha 3 runtime als functionele basis behouden.
- Nog geen fysieke write-calls naar de Anker.

## 0.0.1-alpha.3
- `Bronnen beschikbaar` controleert alleen observatiebronnen.
- `Besturing beschikbaar` toegevoegd.
- Extra read-only diagnostische sensoren toegevoegd.
- Simulatiemodus blijft standaard actief.

## 0.0.1-alpha.1
- Eerste config flow.
- Eerste coordinator.
- Eerste read-only sensoren.
