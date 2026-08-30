# Dummy OS EMS 0.0.1-alpha.65 - Terminal Plan Slot Cleanup Hotfix

## Samenvatting
Alpha65 ruimt verlopen automatische planner-slots met een terminale lifecycle-status automatisch op, zodat oude acties niet zichtbaar blijven hangen terwijl ze technisch al herbruikbaar zijn.

## Opgelost
- Planner-owned slots met `fout`, `voltooid` of `geannuleerd` worden na het volledige startvenster teruggezet naar de standaard lege/conceptstatus wanneer er geen actuele planneractie voor dat slot is.
- De cleanup geldt uitsluitend voor `origin: automatic_72h_planner`; handmatige plannen worden niet aangeraakt.
- De execution audit/historie blijft intact; alleen de actieve Plan Store-slotinhoud wordt opgeschoond.
- De lifecycle-reason voor deze cleanup is `automatic_terminal_released`.
- De interne `VERSION` in `const.py` is gelijkgetrokken met de releaseversie.

## Ongewijzigd
- Alpha64 Plan72 SOC-startuprecovery blijft ongewijzigd.
- Alpha62 planned-energy execution en prijsvensterbegrenzing blijven ongewijzigd.
- Alpha61 low-SOC safety recovery blijft ongewijzigd.
- Manual plans, Automatic Execution-arm, safety gates en safe-return blijven ongewijzigd.

## Validatie
- Python compileall moet slagen voor `custom_components/anker_ems`.
- De broncontrole moet bevestigen dat alleen automatische terminale slots buiten hun startvenster worden geleegd.
- Live Home Assistant-validatie blijft vereist om te bevestigen dat het bestaande oude `fout`-slot na de eerstvolgende coordinator/sync-cyclus verdwijnt.
