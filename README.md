# Dummy OS EMS

**Dummy OS EMS** is een Home Assistant Energy Management System voor de **Anker SOLIX Solarbank Max AC**.

Het project wordt ontwikkeld als een lokale, modulaire EMS-laag bovenop Home Assistant. Het doel is niet alleen om de batterij te bedienen, maar om uiteindelijk batterijstatus, stroomprijzen, zonneprognose, woningverbruik, veiligheidsgrenzen en handmatige keuzes samen te brengen in één begrijpelijk en onderhoudbaar systeem.

> **Status:** experimentele alpha  
> **Domein:** `anker_ems`  
> **Minimale Home Assistant-versie:** 2026.7.0  
> **Huidige ontwikkelversie:** `0.0.1-alpha.17`

---

## Doel van Dummy OS EMS

Dummy OS EMS wordt opgebouwd rond vier hoofdfuncties:

1. **Observeren**  
   De relevante batterij-, net-, prijs-, solar- en verbruiksbronnen uitlezen en normaliseren.

2. **Plannen**  
   Bepalen wanneer laden, ontladen of niets doen logisch is.

3. **Uitvoeren**  
   Een goedgekeurd plan veilig vertalen naar Anker-besturing.

4. **Evalueren**  
   Vergelijken wat gepland was met wat werkelijk is gebeurd en die informatie later gebruiken om de planner te verbeteren.

Het einddoel is één centrale **72-uursplanning** die grotendeels automatisch wordt opgebouwd, terwijl de gebruiker de planning altijd kan bekijken, aanpassen of handmatig overrulen.

---

# Benodigde software en integraties

Dummy OS EMS maakt gebruik van bestaande Home Assistant-integraties als bron- en besturingslaag. De integratie zelf bevat bewust geen hardcoded lokale entity-id's: tijdens de config flow worden de juiste Home Assistant-entiteiten per functie geselecteerd.

## Verplicht voor de huidige handmatige EMS-functies

### 1. Home Assistant

Dummy OS EMS draait als custom integration binnen Home Assistant.

- Minimale ondersteunde versie: **Home Assistant Core 2026.7.0**
- Website: https://www.home-assistant.io/

### 2. HACS

HACS is de aanbevolen manier om Dummy OS EMS en andere benodigde custom integrations te installeren en bij te werken.

- Documentatie: https://www.hacs.xyz/docs/use/

HACS is technisch niet verplicht wanneer custom integrations handmatig in `custom_components` worden geplaatst, maar is voor normaal gebruik de aanbevolen installatieroute.

### 3. Anker Solix Integration for Home Assistant

Voor het uitlezen en fysiek aansturen van de Anker SOLIX Solarbank Max AC gebruikt Dummy OS EMS de bestaande **Anker Solix Integration for Home Assistant** van `thomluther`.

- GitHub: https://github.com/thomluther/ha-anker-solix

Deze integratie levert onder andere de bron- en bedieningseenheden die Dummy OS EMS tijdens de config flow kan koppelen voor:

- batterij-SOC;
- apparaatstatus;
- laadvermogen;
- ontlaadvermogen;
- bedrijfsmodus;
- laad-/ontlaadrichting;
- vermogenssetpoint.

**Dummy OS EMS vervangt deze Anker-integratie niet.** De Anker-integratie blijft verantwoordelijk voor de communicatie met het fysieke Anker-systeem; Dummy OS EMS vormt de plannings-, veiligheids- en besturingslaag daarboven.

---

## Benodigd voor de forecast- en toekomstige automatische plannerlaag

De huidige handmatige planfunctie kan zonder volledige forecastset functioneren. Voor de forecastlaag en de toekomstige automatische planner zijn aanvullende databronnen nodig.

### 4. Solcast PV Forecast

Voor de zonneprognose ondersteunt de huidige forecast-normalisatie de Home Assistant custom integration **Solcast PV Forecast**.

- GitHub: https://github.com/BJReplay/ha-solcast-solar

Dummy OS EMS kan onder andere de `detailedHourly`-gegevens voor vandaag, morgen en dag 3 normaliseren naar `solar_kwh` per uur.

Solcast is nodig wanneer de automatische planner rekening moet houden met verwachte zonneproductie.

### 5. EnergyZero

Voor bekende dynamische elektriciteitsprijzen kan de officiële Home Assistant **EnergyZero**-integratie worden gebruikt.

- Home Assistant-integratie: https://www.home-assistant.io/integrations/energyzero/

De EnergyZero-integratie kan dynamische elektriciteitsprijzen ophalen en ondersteunt ook aanbieders die het EnergyZero-platform gebruiken, waaronder ANWB Energie.

Dummy OS EMS gebruikt prijsdata als bron voor bekende prijsuren. De exacte bronentiteit wordt via de integratieconfiguratie gekoppeld; Dummy OS EMS is dus niet op één vaste entity-id gebaseerd.

### 6. Prijsprognose na de bekende day-ahead uren

Voor uren waarvoor nog geen officiële day-ahead prijs beschikbaar is, kan Dummy OS EMS een afzonderlijke **prijsprognosebron** gebruiken.

De huidige ontwikkelinstallatie gebruikt hiervoor een bestaande Home Assistant-bron die als forecast-entiteit aan Dummy OS EMS wordt gekoppeld.

Deze bron is op dit moment **geen harde externe integratie-afhankelijkheid van Dummy OS EMS**. De architectuur is bewust zo opgezet dat later iedere compatibele prijsprognosebron geselecteerd kan worden.

De huidige forecast-normalisatie kent hiervoor onder andere het interne veld:

`price_source`

waardoor bekende prijs en prognose van elkaar onderscheiden blijven.

### 7. Woningverbruiksprognose

Voor een volledige automatische planner is ook een uurprognose van het verwachte woningverbruik nodig.

De huidige ontwikkelomgeving gebruikt hiervoor een Home Assistant-bron die aan Dummy OS EMS wordt gekoppeld. Ook deze bron is bewust **niet hardcoded** en is nog geen verplichte externe integratie voor de handmatige functies.

De toekomstige planner gebruikt deze prognose om onder andere te bepalen:

- hoeveel energie voor eigen verbruik moet worden gereserveerd;
- hoeveel batterijcapaciteit beschikbaar is voor handel;
- hoeveel energie nodig is tot bruikbare zonneproductie;
- of goedkoop netladen werkelijk nodig is.

---

## Netvermogen en woningvermogen

Dummy OS EMS heeft voor planning en veiligheid betrouwbare informatie nodig over netimport en netexport.

De gebruiker kan hiervoor bestaande Home Assistant-vermogenssensoren selecteren. Dummy OS EMS schrijft geen specifieke slimme meter-, P1- of omvormerintegratie voor.

In de huidige ontwikkelarchitectuur worden onder andere canonieke Home Assistant-projectsensoren gebruikt voor:

- netimportvermogen;
- netexportvermogen;
- woningvermogen.

De integratie moet uiteindelijk met verschillende bronintegraties kunnen werken zolang de gekozen entiteiten de juiste functie en eenheid hebben.

---

# Huidige functionaliteit

## Config Flow en bronmapping

Dummy OS EMS hardcodet geen specifieke lokale Anker- of energiemeter-entity-id's.

Tijdens de config flow selecteert de gebruiker de Home Assistant-entiteiten die de benodigde functies leveren, waaronder:

- batterij-SOC;
- apparaatstatus;
- laadvermogen;
- ontlaadvermogen;
- netimport;
- netexport;
- bedrijfsmodus;
- laad-/ontlaadrichting;
- vermogensinstelling.

Forecastbronnen kunnen via de opties van de integratie worden gekoppeld.

Hierdoor kan dezelfde integratie ook worden gebruikt wanneer apparaatnamen, talen, serienummers of entity-id's verschillen.

---

## Batterij-observatie

De integratie exposeert een genormaliseerde Dummy OS EMS-laag voor belangrijke live batterijwaarden, waaronder:

- EMS-status;
- SOC;
- laadvermogen;
- ontlaadvermogen;
- bedrijfsmodus;
- beschikbaarheid van bronnen;
- beschikbaarheid van besturing.

De originele Anker-entiteiten blijven de fysieke bron.

---

## Drie persistente handmatige planplaatsen

De huidige handmatige bedieningslaag bevat precies **drie onafhankelijke planplaatsen**.

Elke planplaats bevat:

| Instelling | Bereik / opties |
|---|---|
| Actie | geen / laden / ontladen |
| Uitvoering | direct / gepland |
| Starttijd | datum en tijd |
| Vermogen | 100–3500 W |
| Doel-SOC | 5–100% |
| Maximale looptijd | 0,5–12 uur |
| Maximale startvertraging | 1–120 minuten |

Planinstellingen worden persistent opgeslagen en blijven behouden na een Home Assistant-herstart.

Het wijzigen van een plan zet het plan eerst in een conceptstatus. Pas via **Inplannen** of **Nu starten** wordt het plan expliciet vrijgegeven.

### Plan-lifecycle

Een plan kan onder andere door deze statussen lopen:

`leeg → concept → wachtend → startklaar → actief → voltooid`

Daarnaast bestaan uitzonderings- en eindstatussen zoals:

- geannuleerd;
- verlopen;
- fout.

Voltooide of geannuleerde plannen worden niet automatisch opnieuw geselecteerd.

---

# Scheduler

De Scheduler beoordeelt de drie planplaatsen en bepaalt welk plan uitgevoerd mag worden.

Daarbij wordt rekening gehouden met:

- planstatus;
- starttijd;
- maximale startvertraging;
- conflicten tussen meerdere plannen;
- reeds actieve fysieke uitvoering;
- deterministische selectie wanneer meerdere plannen startklaar zijn.

Er mag maximaal **één fysieke batterijactie tegelijk** actief zijn.

Sinds alpha17 wordt een ingepland laadplan dat `startklaar` wordt automatisch overgedragen aan de Execution Controller.

---

# Safety Guard

De Safety Guard vormt de verplichte veiligheidsgrens tussen planning en fysieke batterijbediening.

Er wordt onder andere gecontroleerd op:

- bronbeschikbaarheid;
- beschikbaarheid van besturing;
- SOC;
- doel-SOC;
- gevraagd vermogen;
- tegengestelde laad- of ontlaadstromen;
- bedrijfsmodus;
- geldigheid van de geselecteerde actie.

Een plan mag alleen fysiek worden uitgevoerd wanneer de veiligheidsketen dit toestaat.

---

# Action Controller

De Action Controller vertaalt een geselecteerd EMS-plan naar een semantische batterijopdracht.

De controller bepaalt onder andere:

- laden of ontladen;
- gevraagd vermogen;
- geldigheid van de opdracht;
- status van de Safety Guard.

Hierdoor blijft planningslogica gescheiden van de daadwerkelijke Anker-aansturing.

---

# Execution Controller

De Execution Controller verzorgt de gecontroleerde fysieke uitvoering.

Voor een gevalideerde laadactie kan de integratie:

1. van `self_consumption` naar `third_party_control` schakelen;
2. wachten tot de Anker-bedieningsentiteiten beschikbaar zijn;
3. de veiligheidscontrole opnieuw uitvoeren;
4. richting en vermogen instellen;
5. de uitvoering bewaken;
6. stoppen op doel-SOC, maximale looptijd, handmatige stop of fout;
7. het vermogenssetpoint terugzetten naar 0 W;
8. terugschakelen naar `self_consumption`.

De uitvoeringsstatus wordt persistent bijgehouden zodat na een Home Assistant-herstart veilig kan worden gereageerd op een onderbroken actie.

## Fysiek gevalideerde werking

**Laden is fysiek gevalideerd.**

Bevestigde onderdelen:

- automatische overgang naar `third_party_control`;
- werkelijk laden;
- ingesteld laadvermogen;
- automatische stop;
- setpoint terug naar 0 W;
- terugkeer naar `self_consumption`;
- correcte afronding van de plan-lifecycle.

**Fysiek ontladen is nog niet als bewezen uitvoerpad vrijgegeven.**

Daarvoor wordt eerst een afzonderlijke gecontroleerde ontlaadtest uitgevoerd.

---

# Handmatige services

De integratie bevat onder andere de volgende Home Assistant-services:

| Service | Functie |
|---|---|
| `anker_ems.schedule_plan` | Een planplaats inplannen |
| `anker_ems.start_plan_now` | Een specifieke planplaats direct starten |
| `anker_ems.cancel_plan` | Een plan annuleren |
| `anker_ems.stop_all` | Actieve EMS-besturing veilig stoppen |
| `anker_ems.execute_selected_plan` | Het geselecteerde Scheduler-plan uitvoeren |
| `anker_ems.stop_execution` | Een actieve uitvoering stoppen |
| `anker_ems.start_charge_test` | Beperkte fysieke laadtest |
| `anker_ems.stop_physical_test` | De fysieke test veilig stoppen |

De normale gebruikersworkflow is bedoeld om via de planplaatsen te werken. De fysieke testservices zijn uitsluitend bedoeld voor gecontroleerde ontwikkeling en validatie.

---

# Forecastlaag

Dummy OS EMS bevat inmiddels een eerste Python-gebaseerde forecast-normalisatielaag.

Bestaande Home Assistant-bronnen worden genormaliseerd naar één uurmodel met maximaal ongeveer 72 toekomstige uren.

Het interne uurmodel bevat:

- `time`;
- `price`;
- `price_min`;
- `price_max`;
- `price_source`;
- `solar_kwh`;
- `home_consumption_kwh`.

Voor hetzelfde uur heeft een bekende prijs voorrang op een prijsprognose.

De forecastlaag **normaliseert bestaande databronnen; zij maakt op dit moment niet alle prognoses zelf**.

---

# Source Monitor

De Source Monitor registreert wanneer belangrijke brondata opnieuw wordt gerapporteerd en wanneer de inhoud werkelijk verandert.

De huidige monitor observeert onder andere:

- Solcast;
- bekende prijsdata;
- prijsprognose;
- de huidige Stroomvoorspeller-bron in de ontwikkelomgeving.

De historie wordt begrensd opgeslagen voor diagnose.

Het doel hiervan is om de toekomstige planner **event-driven** te laten herberekenen: alleen wanneer relevante broninformatie daadwerkelijk verandert, in plaats van zware forecast- en planningslogica voortdurend opnieuw uit te voeren.

De Source Monitor is momenteel observerend en start de automatische planner nog niet.

---

# Diagnostiek

Dummy OS EMS exposeert diagnose-entiteiten voor de verschillende interne lagen.

Belangrijke groepen zijn:

### Core
- `Dummy OS EMS Status`
- `Dummy OS EMS SOC`
- `Dummy OS EMS Laadvermogen`
- `Dummy OS EMS Ontlaadvermogen`
- `Dummy OS EMS Bedrijfsmodus`
- `Dummy OS EMS Bronnen beschikbaar`
- `Dummy OS EMS Besturing beschikbaar`

### Forecast
- `Dummy OS EMS Forecast status`
- `Dummy OS EMS Forecast complete uren`
- `Dummy OS EMS Forecast bronnen beschikbaar`
- `Dummy OS EMS Bronmonitor`

### Scheduler
- `Dummy OS EMS Scheduler status`
- `Dummy OS EMS Scheduler geselecteerd plan`
- `Dummy OS EMS Scheduler startklaar`

### Safety en Action
- `Dummy OS EMS Safety Guard status`
- `Dummy OS EMS Safety Guard reden`
- `Dummy OS EMS Safety Guard veilig`
- `Dummy OS EMS Action Controller status`
- `Dummy OS EMS Action Controller actie`
- `Dummy OS EMS Action Controller gereed`

### Execution
- `Dummy OS EMS Uitvoering status`
- `Dummy OS EMS Uitvoering resterend`
- `Dummy OS EMS Uitvoering actief`

### Planplaatsen
Iedere planplaats exposeert eigen entiteiten voor:

- actie;
- uitvoeringsmodus;
- starttijd;
- vermogen;
- doel-SOC;
- maximale looptijd;
- maximale startvertraging;
- planstatus.

De uiteindelijke entity-id's worden door Home Assistant gegenereerd op basis van deze namen.

---

# Architectuur

```text
Externe Home Assistant-bronnen
        │
        ▼
Config Flow / Options
        │
        ▼
Integration Coordinator
        │
        ├── Forecast normalisatie
        ├── Source Monitor
        │
        ▼
Persistent Plan Store
        │
        ▼
Scheduler
        │
        ▼
Safety Guard
        │
        ▼
Action Controller
        │
        ▼
Execution Controller
        │
        ▼
Anker Solix Integration
        │
        ▼
Anker SOLIX Solarbank Max AC
```

Forecasting, planning, veiligheid en fysieke aansturing blijven hierdoor afzonderlijk testbaar.

---

# Veiligheidsprincipes

Dummy OS EMS moet altijd veilig falen.

Belangrijke ontwerpprincipes zijn:

- maximaal één fysieke actie tegelijk;
- Safety Guard vóór fysieke uitvoering;
- persistent uitvoeringsstate;
- veilige afhandeling na herstart;
- 0 W setpoint bij safe-stop;
- terugkeer naar `self_consumption`;
- hardwaregrenzen altijd respecteren;
- geen stille fallback naar onveilige bediening;
- laden en ontladen afzonderlijk fysiek valideren.

De Anker-batterij hanteert standaard een minimale SOC van **5%**. Dummy OS EMS mag geen lagere SOC-doelen plannen.

---

# Roadmap

## 1. Handmatige bediening volledig afronden

Nog te voltooien:

- geplande laadactie na de alpha17 Scheduler → Execution-fix opnieuw valideren;
- gecontroleerde fysieke ontlaadtest;
- alle drie planplaatsen end-to-end testen;
- edge-cases rond herstart, annuleren en stoppen verder valideren;
- tijdelijk onuitvoerbare plannen binnen `max_start_delay` slimmer opnieuw laten proberen.

---

## 2. Automatische 72-uursplanner

De toekomstige planner berekent één volledige 72-uursstrategie.

De dashboardlaag kan daarna kiezen tussen:

- alleen de eerste 24 uur;
- de volledige 72 uur.

Er komen dus niet twee aparte planningsstrategieën.

De planner zal uiteindelijk rekening houden met:

- actuele SOC;
- bruikbare batterijcapaciteit;
- verwachte woningafname;
- zonneprognose;
- bekende stroomprijzen;
- prijsprognose;
- laad- en ontlaadverliezen;
- minimale SOC en softwarematige reserve;
- energiebehoefte tot bruikbare zon;
- laad- en ontlaadlimieten;
- handmatige acties;
- veiligheidsgrenzen.

---

## 3. Slim netladen

Wanneer zonneproductie ontbreekt of onvoldoende is, moet Dummy OS EMS tijdens voldoende goedkope uren vanaf het net kunnen laden en die energie later tijdens duurdere uren gebruiken.

De planner beoordeelt de **netto financiële meerwaarde** en niet uitsluitend het goedkoopste prijsuur.

Daarbij worden onder andere meegenomen:

- prijsverschil;
- laadverlies;
- ontlaadverlies;
- woningverbruik;
- verwacht zonneoverschot;
- SOC-reserve;
- beschikbare batterijcapaciteit;
- veiligheidsmarges.

---

## 4. Veiligheidslading versus handelslading

De automatische planner moet onderscheid maken tussen:

### Veiligheidslading
Energie die nodig is om voldoende reserve beschikbaar te houden tot bruikbare zonneproductie of een andere betrouwbare energiebron beschikbaar is.

### Handelslading
Extra energie die uitsluitend wordt geladen omdat het verwachte prijsverschil na verliezen financieel aantrekkelijk is.

Veiligheid en beschikbaarheid blijven altijd belangrijker dan handelsoptimalisatie.

---

## 5. Solar Charge Delay

De planner moet zonneladen kunnen uitstellen wanneer het verstandiger is batterijcapaciteit beschikbaar te houden voor een later en waardevoller zonneoverschot.

Dit wordt gecombineerd met:

- zonneprognose;
- woningverbruik;
- SOC;
- vrije batterijcapaciteit;
- prijsvensters.

---

## 6. Event-driven herplanning

De automatische planner moet niet continu opnieuw rekenen.

Toekomstige triggers voor herplanning zijn betekenisvolle wijzigingen in:

- Solcast;
- bekende stroomprijzen;
- prijsprognose;
- woningverbruiksprognose;
- SOC;
- handmatige overrides;
- planwijzigingen.

De bestaande Source Monitor vormt hiervoor de eerste basis.

---

## 7. Afwezigheidsmodus

Er komt een expliciete **Afwezigheidsmodus**.

Minimaal geplande entiteit:

`switch.anker_ems_absence_mode`

Tijdens afwezigheid:

- wordt uitgegaan van lager huishoudelijk verbruik;
- hoeft minder batterijcapaciteit voor normaal eigen verbruik gereserveerd te worden;
- kan meer capaciteit beschikbaar komen voor prijsgebaseerde handel;
- blijven veiligheidsgrenzen en minimale SOC leidend;
- blijft handmatige noodbediening mogelijk;
- volgen automatische en geplande acties een expliciet afwezigheidsprofiel.

---

## 8. Canoniek woningvermogen

Een toekomstige integratiesensor is gepland:

`sensor.anker_ems_home_power`

Zichtbare naam:

**Woningverbruik actueel**

De config flow moet hiervoor twee bronmodi ondersteunen:

1. een bestaande directe woningvermogenssensor selecteren;
2. woningvermogen laten berekenen uit geselecteerde sensoren voor net, solar en batterij.

De integratie gebruikt daarbij één vaste tekenconventie en voorkomt dubbele telling.

---

## 9. Plan versus werkelijkheid

Er komt een afzonderlijke historische evaluatielaag voor laad- en ontlaadacties.

Deze vergelijkt geplande en werkelijke uitvoering voor zowel automatische als handmatige plannen.

Onder andere:

- geplande versus werkelijke starttijd;
- geplande versus werkelijke eindtijd;
- duur;
- gevraagd versus werkelijk vermogen;
- energie;
- doel-SOC;
- bereikte SOC;
- reden van afwijkingen.

Deze evaluatie staat los van de vooruitkijkende 72-uursplanning.

---

## 10. Meldingen

Een toekomstige notificatielaag kan een dagelijkse EMS-samenvatting geven, bijvoorbeeld rond het avondmoment waarop de volgende planning beschikbaar is.

De melding kan bevatten:

- actuele SOC;
- verwachte zonneproductie;
- verwacht woningverbruik;
- geplande laad- en ontlaadacties;
- belangrijke prijsvensters;
- reservebeslissing;
- reden achter het plan;
- eventuele noodzaak voor handmatige controle.

---

## 11. Minder afhankelijkheid van YAML/Jinja

Een belangrijk langetermijndoel is om EMS-specifieke logica uit zware Home Assistant YAML/Jinja-packages naar de Python-integratie te verplaatsen.

Migratie gebeurt gecontroleerd:

1. equivalente integratiefunctie bouwen;
2. waar nodig oud en nieuw tijdelijk parallel laten draaien;
3. resultaten vergelijken;
4. dashboards en automatiseringen omzetten;
5. oude package-logica pas daarna verwijderen.

Externe databronnen zoals Solcast blijven externe integraties waar dat logisch is.

---

# Wat Dummy OS EMS bewust nog niet is

Dummy OS EMS is momenteel **niet**:

- een volledig afgeronde automatische batterijoptimizer;
- een generieke EMS-integratie voor ieder batterijmerk;
- een vervanger voor de Anker Solix Home Assistant-integratie;
- een garantie op financieel rendement;
- een manier om hardware- of fabrikantveiligheidslimieten te omzeilen.

De eerste ontwikkelfase richt zich bewust op betrouwbare werking met de **Anker SOLIX Solarbank Max AC**.

---

# Installatie

Dummy OS EMS is bedoeld voor installatie via HACS als custom repository.

Voor de huidige alpha is de aanbevolen volgorde:

1. Installeer en configureer Home Assistant 2026.7.0 of nieuwer.
2. Installeer HACS.
3. Installeer en configureer de Anker Solix Integration for Home Assistant.
4. Controleer of de benodigde Anker bron- en bedieningsentiteiten beschikbaar zijn.
5. Installeer Dummy OS EMS via HACS.
6. Herstart Home Assistant.
7. Voeg **Dummy OS EMS** toe via **Instellingen → Apparaten & diensten**.
8. Selecteer de juiste Anker-, net- en overige bronentiteiten.
9. Voeg voor de forecastlaag desgewenst Solcast, EnergyZero en overige forecastbronnen toe.
10. Controleer eerst de diagnose-entiteiten voordat fysieke besturing wordt getest.

Omdat het project nog alpha-software is, moeten fysieke laad- en ontlaadacties zorgvuldig en gecontroleerd worden getest.

---

# Ontwikkelmodel

```text
Bronnen uitlezen
    ↓
Data normaliseren
    ↓
Persistente handmatige plannen
    ↓
Scheduler
    ↓
Safety Guard
    ↓
Action Controller
    ↓
Gecontroleerde fysieke uitvoering
    ↓
Automatische planner
    ↓
Historische evaluatie en optimalisatie
```

Een nieuwe laag wordt pas als betrouwbaar beschouwd wanneer de voorgaande laag functioneel is gevalideerd.

Release-specifieke wijzigingen, bugfixes en versiehistorie horen in **CHANGELOG.md** en in de **GitHub Release notes**.

De README is bewust bedoeld als actueel overzicht van:

- wat Dummy OS EMS is;
- welke integraties en databronnen nodig of ondersteund zijn;
- wat de integratie momenteel bevat;
- hoe de architectuur is opgebouwd;
- wat nog ontwikkeld moet worden.

---

# Onafhankelijkheid en aansprakelijkheid

Dummy OS EMS is een onafhankelijk opensource-communityproject.

Het project is niet gelieerd aan of goedgekeurd door:

- Anker Innovations;
- Home Assistant;
- Nabu Casa;
- andere genoemde hardware- of softwarefabrikanten.

Productnamen en merknamen blijven eigendom van hun rechthebbenden.

Batterijbesturing betreft fysieke elektrische apparatuur. Gebruik van deze software is op eigen risico. Respecteer altijd de veiligheidsgrenzen en voorschriften van batterij, omvormer, elektrische installatie en fabrikant.
