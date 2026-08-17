# Dummy OS EMS

Home Assistant EMS-integratie voor de Anker SOLIX Solarbank Max AC.

**Status:** experimentele alpha  
**Domein:** `anker_ems`  
**Minimale Home Assistant-versie:** 2026.7.0  
**Huidige release:** `0.0.1-alpha.4`

## Huidige functionaliteit

De integratie:
- wordt via de Home Assistant UI geconfigureerd;
- laat bestaande Anker- en netsensoren selecteren;
- leest SOC, apparaatstatus, laadvermogen, ontlaadvermogen en bedrijfsmodus;
- leest optioneel netafname en netexport;
- publiceert eigen `Dummy OS EMS` diagnose-entiteiten;
- onderscheidt `Bronnen beschikbaar` van `Besturing beschikbaar`;
- blijft standaard in simulatiemodus;
- bevat nog geen fysieke write-calls.

## Veilig ontwikkelmodel

De bestaande YAML-oplossing blijft voorlopig de operationele referentie.

Tijdens ontwikkeling geldt:
1. eerst uitlezen en valideren;
2. daarna simulatie;
3. vervolgens één gecontroleerde fysieke actie;
4. nooit twee fysieke controllers tegelijk.

## Installeren via HACS custom repository

Zodra deze map als openbare GitHub-repository beschikbaar is:

1. Open HACS.
2. Voeg de GitHub-repository toe als **Custom repository**.
3. Kies type **Integration**.
4. Installeer **Dummy OS EMS**.
5. Herstart Home Assistant.
6. Voeg **Dummy OS EMS** toe via *Instellingen -> Apparaten & diensten*.

## Forecast Sources - volgende ontwikkelstap

De eerstvolgende functionele laag wordt een genormaliseerde forecastbron voor:
- bekende/all-in stroomprijzen;
- verdere prijsforecast;
- Solcast vandaag, morgen en dag 3;
- woningverbruiksforecast.

De planner krijgt daarna per uur één intern gegevensmodel met onder andere:
- tijd;
- prijs;
- prijs minimum/maximum;
- zonneverwachting;
- verwacht woningverbruik.

Hierdoor blijft de latere 72-uursplanner onafhankelijk van de precieze bronintegratie.

## OmniBattery

OmniBattery wordt gebruikt als technische referentie, niet als vervanger.

Te onderzoeken principes:
- tekortgestuurd netladen;
- gegarandeerde reserve tot bruikbare zon;
- alleen benodigde goedkoopste laaduren;
- veiligheidslading en handelslading scheiden;
- Solar Charge Delay;
- live veiligheidscontrole;
- fallback en herstel.

## Belangrijk voor publicatie

Vervang vóór GitHub-publicatie alle voorkomens van:

`bliek79`

door de echte GitHub-gebruikersnaam.

Daarnaast zijn nog open:
- definitieve opensourcelicentie;
- definitieve brand/icon asset;
- naam-/merkcontrole voor Dummy OS / DummyOS / Dummy OS EMS.

Zie `GITHUB_SETUP.md`.
