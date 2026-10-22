# ScannerAMZ 2.0.1 — installateur Windows

Outil de vendeur Amazon FBA France : coûts, garde-fous de marge et prix par
SKU. **Il modifie de vrais prix sur votre compte Amazon**, toujours après
votre confirmation.

## Télécharger

[**ScannerAMZ-2.0.1.zip**](https://github.com/sodekai/animation-test/raw/scanneramz-installateur/ScannerAMZ-2.0.1.zip)
(20 Mo) : `Setup-ScannerAMZ-2.0.1.exe`, `Guide-installation.pdf`, `LISEZ-MOI.txt`.

## Installer

Il faut Windows 10 ou 11 (64 bits), rien d'autre : ni Python, ni droits
administrateur. Pour s'en servir, il faut aussi ses propres identifiants
Amazon SP-API (voir le guide, étape 1).

1. Clic droit sur le zip téléchargé → **Propriétés** → cochez **Débloquer** → **OK**.
2. Clic droit → **Extraire tout** → **Extraire**.
3. Double-clic sur `Setup-ScannerAMZ-2.0.1.exe` → **Suivant** → **Installer** → **Terminer**.

L'installateur n'est pas signé. Si Windows affiche « Windows a protégé votre
ordinateur » : **Informations complémentaires** → **Exécuter quand même**. Si
Smart App Control est activé sur le PC, Windows le bloque sans recours.

## Vérifier le fichier

- SHA-256 du zip : `614c5b5a7344e6edebbad99cde930f35d4d5dc991462071fab638697d4019163`
- SHA-256 de `Setup-ScannerAMZ-2.0.1.exe` : `9b6be3ec0083ae12ff3426eae9c96a9985f75c61a7d91417eca47ba3f698ca13`

Version 2.0.1, construite depuis le commit `f8fc469` du dépôt source.
