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
