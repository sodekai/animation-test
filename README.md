# Animation test

Deux animations de 20 secondes au format vertical 1080×1920 (Reels / TikTok), **générées entièrement en code** : aucun logiciel d'animation, aucune image importée, aucun échantillon sonore. Chaque pixel est dessiné par programme et chaque son est synthétisé mathématiquement.

| Projet | Style | Vidéo |
|---|---|---|
| `sunset-factory/` : une petite usine fabrique un coucher de soleil, jusqu'à ce qu'un bocal d'étoiles tombe | Papier découpé | `videos/usine-couchers-de-soleil.mp4` |
| `yasuo-vs-yone/` : duel au sabre entre les deux frères de League of Legends | Silhouettes à contre-jour, lames lumineuses | `videos/yasuo-vs-yone.mp4` |

## Technologies

| Outil | Rôle |
|---|---|
| **Python 3.11** | Tout le projet |
| **[pycairo](https://pycairo.readthedocs.io/)** (Cairo) | Bibliothèque de dessin vectoriel 2D : formes, courbes de Bézier, dégradés, anticrénelage. Chaque image est dessinée en vectoriel puis rastérisée. |
| **NumPy / SciPy** | Textures procédurales (bruit par FFT), ombres douces et bloom (sous-échantillonnage + flou gaussien), physique des cheveux et du tissu, synthèse audio (sinusoïdes, bruit filtré, réverbération par convolution) |
| **FFmpeg** (via `imageio-ffmpeg`) | Encodage des images brutes en MP4 H.264 + AAC |
| **multiprocessing** | Rendu de 4 images en parallèle |

## Comment ça marche

1. **Timeline par images clés** : tout (positions, angles, couleurs, caméra) est une fonction du temps `t`. La classe `Track` (`core.py`) interpole des clés avec des courbes d'accélération (*easing*).
2. **Personnages articulés** : un squelette 2D dont les bras et les jambes sont résolus par **cinématique inverse à deux os** (IK). On décrit une pose par la position des mains, des pieds et l'angle des lames, et le squelette suit.
3. **Physique** : les queues de cheval, ceintures et pans de manteau sont des chaînes simulées par **intégration de Verlet** (gravité, vent, contraintes de longueur). La simulation est précalculée puis mise en cache.
4. **Rendu par couches** : décor, personnages, effets. Chaque couche est composée avec :
   - des ombres portées douces (effet papier) pour l'usine ;
   - un liseré de contre-jour, du bloom additif et des traînées de lame pour le duel.
5. **Effets** : particules (étincelles, pétales, étoiles), ondes de choc, *hit-stop* (micro-arrêt sur image à chaque impact), secousses et zooms de caméra.
6. **Son** : chaque son est synthétisé avec NumPy et placé aux instants lus dans la chorégraphie. Par exemple, les « whoosh » sont détectés automatiquement à partir de la vitesse réelle de la pointe des lames.
7. **Encodage** : les images brutes (BGRA) sont envoyées directement dans FFmpeg avec la piste audio.

## Structure

```
sunset-factory/
  core.py      maths, easing, keyframes, textures papier, compositing
  world.py     timeline de l'histoire (soleil, grue, pinceaux, bocal, étoiles)
  workers.py   les ouvriers : squelette, IK, expressions, chorégraphie
  scene.py     décor, accessoires et composition de chaque image
  audio.py     bruitages synthétisés
  render.py    rendu parallèle + encodage FFmpeg
  preview.py   planche d'aperçu d'instants choisis
yasuo-vs-yone/
  core.py      (même base que ci-dessus)
  rig.py       squelette de profil, IK, dessin des silhouettes (Yasuo, Yone, lames)
  choreo.py    chorégraphie du combat, clashs, vent, simulation cheveux/tissu
  scene.py     ciel, soleil, montagnes, cerisier, pétales, effets, caméra, compositing
  audio.py     bande-son : taikos, flûte, vent, clashs, dégainés, tornade...
  render.py / preview.py
videos/        les deux MP4 finaux
```

## Lancer le rendu

```bash
pip install -r requirements.txt

cd yasuo-vs-yone
python audio.py audio.wav                       # ~10 s
python render.py yasuo_vs_yone.mp4 audio.wav    # ~2 min sur 4 cœurs
python preview.py apercu.png 5.0 10.5 16.5      # aperçu rapide de quelques instants
```

Même principe dans `sunset-factory/`. Le nombre de processus de rendu est fixé dans `render.py` (`Pool(4)`).

Installation de Cairo :
- **Windows** : `pip install pycairo` suffit (les binaires sont inclus).
- **Linux** : `sudo apt install libcairo2-dev pkg-config python3-dev`.
- **macOS** : `brew install cairo pkg-config`.

## Où modifier quoi (duel)

- **Timing et mouvements** : `choreo.py`. Chaque clé s'écrit `(temps, pose(...))`. Les clashs sont dans `CLASHES`, les arrêts sur image dans `HOLDS`.
- **Couleurs des personnages et des lames** : `rig.py` (`YASUO`, `YONE`, `BLADES`).
- **Caméra** : `scene.py` (`CAM`, secousses `SHAKES`).
- **Son** : `audio.py`, fonction `main()`.

---

Yasuo et Yone sont des personnages de *League of Legends* © Riot Games. Ce projet est du fan art non officiel qui n'utilise aucun élément graphique ou sonore du jeu.
