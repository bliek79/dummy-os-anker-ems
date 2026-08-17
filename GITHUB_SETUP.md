# GitHub setup

## 1. Maak de repository

Repositorynaam:

`dummy-os-anker-ems`

Aanbevolen:
- public repository;
- Issues ingeschakeld;
- description invullen;
- topics toevoegen, bijvoorbeeld `home-assistant`, `hacs`, `ems`, `anker`, `battery`.

## 2. Vervang de GitHub-placeholder

Zoek projectbreed op:

`bliek79`

en vervang dit door de echte GitHub-gebruikersnaam.

Dit staat minimaal in:
- `custom_components/anker_ems/manifest.json`.

## 3. Brand asset

Voor HACS-publicatie moet een brand asset worden toegevoegd.

Plaats minimaal:

`custom_components/anker_ems/brand/icon.png`

De definitieve Dummy OS-brand asset is nog niet in deze build opgenomen.

## 4. Licentie

Kies vóór openbare release een opensourcelicentie en vervang `LICENSE_PENDING.md` door `LICENSE`.

## 5. Eerste GitHub release

Na upload:
- controleer GitHub Actions;
- los validatiefouten op;
- maak daarna een echte GitHub Release aan;
- gebruik bijvoorbeeld tag `v0.0.1-alpha.4`.

HACS gebruikt GitHub Releases voor nette versie-selectie en updates wanneer releases aanwezig zijn.

## 6. HACS custom repository

Voeg daarna de repository in HACS toe als:
- type: Integration.

Vanaf dat moment kunnen nieuwe releases via HACS worden bijgewerkt.
