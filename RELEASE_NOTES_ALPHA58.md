GitHub Release

Tag: 0.0.1-alpha.58

Release title: Dummy OS EMS 0.0.1-alpha.58 - Safety Action Threshold & Execution Audit Fix

## Dummy OS EMS 0.0.1-alpha.58

Gerichte correctierelease op basis van de eerste echte automatische laadsessies van alpha57. De release voorkomt dat minieme dynamische safety-charge restwaarden als fysieke laadactie worden uitgevoerd en verbetert de meting van werkelijk overgedragen energie in Execution Audit / Plan-vs-Actual.

### Opgelost
- De Automatic Plan Bridge gebruikte in alpha57 dezelfde `0,01 kWh` grens als de numerieke plannerlogica. Daardoor konden kleine safety-charge restwaarden van bijvoorbeeld `0,034`, `0,041` en `0,088 kWh` worden omgezet in een fysieke laadactie met minimaal `100 W`.
- Voor automatische **veiligheidslaadacties** geldt nu een aparte `minimum actionable` grens van `0,10 kWh`. Waarden daaronder blijven zichtbaar in Plan72, maar worden niet meer naar Plan Store / Scheduler / Execution gepromoveerd.
- Execution Audit berekent werkelijk overgedragen energie nu primair door de gemeten batterijvermogens tussen de 5-secondenmonsters te integreren.
- Wanneer de vermogensbron tijdens een echte run effectief `0 W` blijft rapporteren maar SOC aantoonbaar met minimaal `0,5 procentpunt` verandert, gebruikt de audit een transparante SOC-delta fallback.
- De interne `VERSION`-constante stond nog op `0.0.1-alpha.54` en is gecorrigeerd naar `0.0.1-alpha.58`.

### Nieuw
- Bridge-diagnostiek: `min_actionable_safety_charge_kwh`, `suppressed_safety_charge_kwh`, `suppressed_safety_charge_count` en `suppressed_safety_charge_hours`.
- Execution Audit / Plan-vs-Actual / Execution Monitor tonen `actual_energy_source`, zodat zichtbaar is of de werkelijke energie uit `power_samples` of `soc_delta_fallback` komt.

### Ongewijzigd
- De dynamische reserveberekening blijft ongewijzigd.
- De extra execution buffer van `2 procentpunt` blijft volledig actief.
- De numerieke planner-epsilon van `0,01 kWh` blijft bestaan; alleen de fysieke actionability van safety-charge is aangescherpt.
- Stroomvoorspeller prijsarchitectuur en 168-uurs bronpad zijn ongewijzigd.
- Plan Store, Scheduler, Pre-Start, Safety Guard, Final Revalidation, two-stage Anker readiness en de `0 W -> third_party_control -> revalidation -> setpoint -> 0 W -> self_consumption` veiligheidsketen zijn ongewijzigd.
- Maximum laad-/ontlaadvermogen en overige Options Flow-instellingen zijn ongewijzigd.

### Validatie
- Controleer na installatie dat de Automatic Plan Bridge in de attributen `min_actionable_safety_charge_kwh: 0.1` toont.
- Bij een Plan72 safety-charge restwaarde kleiner dan `0,10 kWh` mag de bridge deze niet als automatische laadkandidaat naar een planslot schrijven; de suppressed-diagnostiek moet de waarde/uren wel zichtbaar maken.
- Een aantoonbare safety-charge van `>= 0,10 kWh` moet nog steeds normaal als kandidaat kunnen worden aangemaakt, mits alle overige gates groen zijn.
- Na de eerstvolgende echte automatische run controleer `sensor.dummy_os_ems_execution_audit` en `sensor.dummy_os_ems_plan_vs_actual`: `actual_energy_kwh` moet een bruikbare waarde geven wanneer power samples of een aantoonbare SOC-delta beschikbaar zijn, en `actual_energy_source` moet de gebruikte methode aangeven.
- Controleer dat een uitgevoerde actie na stoppen terugkeert naar `self_consumption` zoals in alpha57.
