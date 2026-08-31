# Dummy OS EMS 0.0.1-alpha.66 - Active Plan Duplicate Suppression Hotfix

## Samenvatting
Alpha66 voorkomt dat een periodieke Plan72-herberekening tijdens een al actieve automatische batterijactie een tweede overlappende actie van hetzelfde type naar een ander planslot schrijft.

## Opgelost
- `planner_action_bridge.py` herkent nu een al actieve `automatic_72h_planner`-actie.
- Een nieuwe kandidaat van hetzelfde type wordt onderdrukt wanneer de planner identity gelijk is aan de actieve actie.
- Als een rolling forecast de identity wijzigt, wordt een nieuwe kandidaat eveneens onderdrukt wanneer deze vóór het expliciete `planned_end_time` van de actieve actie start.
- Een onderdrukte kandidaat krijgt geen planslot en wordt niet naar Plan Store of Scheduler doorgezet.
- Een werkelijk latere, niet-overlappende actie blijft toegestaan.
- Nieuwe diagnostiek: `auto_bridge_active_execution_suppressed_count`, `active_execution_match` en `active_execution_slot`.

## Ongewijzigd
- Plan72 rekenlogica en economische handelsformules.
- Alpha65 terminal plan slot cleanup.
- Alpha62 planned-energy execution fidelity.
- Alpha61 low-SOC safety recovery.
- Manual priority.
- Automatic Execution-arm, safety gates, execution controller en safe return.
- Toekomstige niet-overlappende laad- of ontlaadacties.

## Validatie
- Python `compileall` moet slagen voor `custom_components/anker_ems`.
- HACS en Hassfest moeten slagen.
- Live Home Assistant-validatie: tijdens een actieve automatische laadactie mag geen tweede overlappende laadactie `startklaar` worden.
- Live Home Assistant-validatie: tijdens een actieve automatische ontlaadactie mag geen tweede overlappende ontlaadactie `startklaar` worden.
- Een latere niet-overlappende planneractie moet gewoon beschikbaar blijven.
