
# EPUB Image Splitter

Ein CLI-Tool, das ein EPUB so umbaut, dass **jedes Bild eine eigene Seite** erhält und
**zusammenhängende Texte zwischen zwei Bildern** als eigene **Textseiten** eingefügt werden.
Originale **CSS**-Dateien werden übernommen. Mini-Platzhalterbilder (z. B. 1×1 PNGs) werden standardmäßig ignoriert.

## Schnellstart (Devcontainer)

1. Öffne diesen Ordner mit **VS Code** und akzeptiere „Reopen in Container“.
2. Lege EPUB-Dateien in `in/`.
3. Führe die Launch-Konfiguration **Run script (workspace)** aus.

## Docker (Runtime)

```bash
docker build -t epub-imgsplit:latest .
docker run --rm -v $PWD/in:/in -v $PWD/out:/out epub-imgsplit:latest
```

## CLI

```bash
python src/epub_split_images.py --input ./in --output ./out [--images-only] [--min-width 2] [--min-height 2]
```

- `--images-only`: erzeugt nur Bildseiten (keine Textseiten).
- `--min-width` / `--min-height`: Filtert Platzhalter-Bilder (Default: 2×2).

## 📂 Input / Output Verzeichnisse

- Lege deine **Original-EPUBs** in den Ordner [`in/`](./in).
- Die **konvertierten EPUBs** landen automatisch im Ordner [`out/`](./out).

> ⚡️ Hinweis: Sowohl im Devcontainer als auch beim Docker-Lauf sind diese Ordner
> nach außen gemountet.  
> Das heißt: Alles was im Container unter `/workspaces/project/out` erzeugt wird,
> erscheint direkt auf deinem Host-System im Ordner `out/` im Projektverzeichnis.
