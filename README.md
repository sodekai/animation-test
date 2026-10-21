# ScannerAMZ 2.0.0 — installateur Windows

Outil de vendeur Amazon FBA France : coûts, garde-fous de marge et prix par
SKU. **Il modifie de vrais prix sur votre compte Amazon**, toujours après
votre confirmation.

## Télécharger

[**ScannerAMZ-2.0.0.zip**](https://github.com/sodekai/animation-test/raw/scanneramz-installateur/ScannerAMZ-2.0.0.zip)
(31 Mo) : `Setup-ScannerAMZ-2.0.0.exe`, `Guide-installation.pdf`, `LISEZ-MOI.txt`.

## Installer

Il faut Windows 10 ou 11 (64 bits), rien d'autre : ni Python, ni droits
administrateur. Pour s'en servir, il faut aussi ses propres identifiants
Amazon SP-API (voir le guide, étape 1).

1. Clic droit sur le zip téléchargé → **Propriétés** → cochez **Débloquer** → **OK**.
2. Clic droit → **Extraire tout** → **Extraire**.
3. Double-clic sur `Setup-ScannerAMZ-2.0.0.exe` → **Suivant** → **Installer** → **Terminer**.

L'installateur n'est pas signé. Si Windows affiche « Windows a protégé votre
ordinateur » : **Informations complémentaires** → **Exécuter quand même**. Si
Smart App Control est activé sur le PC, Windows le bloque sans recours.

## Vérifier le fichier

- SHA-256 du zip : `69ae62793fb85b6b61553a52ddb67e866cf427d9f6119ff890d0cab9efb2d641`
- SHA-256 de `Setup-ScannerAMZ-2.0.0.exe` : `1acd041c44425c647996e4038bd424ab08fd959397b04407f82fdcdc4455ec0a`

Version 2.0.0, construite depuis le commit `7fef64b` du dépôt source.
