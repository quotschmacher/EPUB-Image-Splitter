# EPUB Image Splitter

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![VS Code Devcontainer](https://img.shields.io/badge/vscode-devcontainer-007ACC?logo=visual-studio-code)](https://code.visualstudio.com/docs/devcontainers/containers)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Ein Tool, das **EPUB-Dateien neu strukturiert**, indem es jede Bildressource auf eine eigene Seite verschiebt. Zusätzlich werden **zusammenhängende Textabschnitte zwischen den Bildern** als eigenständige Textseiten eingefügt – so bleibt die Lesereihenfolge und der ursprüngliche Kontext erhalten.  

Das Projekt ist für **Batch-Verarbeitung** ausgelegt, läuft sowohl als **VS Code Devcontainer** als auch als **Docker-Container** und eignet sich damit für automatisierte Workflows.

---

## ✨ Features
- 📖 **EPUB-to-EPUB Transformation**: Originaldateien bleiben unverändert, Ergebnis ist ein neues `_imgsplit.epub`.
- 🖼️ **Bildseiten**: Jedes Bild wird auf eine eigene XHTML-Seite gesetzt.  
- ✍️ **Textseiten**: Text zwischen zwei Bildern wird als eigenständige Seite eingefügt (optional deaktivierbar per `--images-only`).  
- 🎨 **CSS-Übernahme**: Alle im Manifest enthaltenen Stylesheets werden kopiert und eingebunden.  
- 🗑️ **Platzhalterfilter**: Mini-Bilder (z. B. 1×1 px PNG-Spacer) werden ignoriert. Schwellwerte (`--min-width`, `--min-height`) konfigurierbar.  
- ⚡ **Batch-fähig**: Mehrere EPUBs im Input-Verzeichnis werden automatisch verarbeitet.  
- 🐳 **Docker-Support**: Einfacher Batch-Run ohne lokale Python-Installation.  
- 🛠️ **VS Code Devcontainer**: Out-of-the-box Entwicklungsumgebung mit allen Abhängigkeiten.  

---

## 📂 Projektstruktur
```
epub-imgsplit-project/
  ├── in/             # Eingabe-EPUBs
  ├── out/            # Ausgabe-EPUBs
  ├── src/epub_split_images.py
  ├── requirements.txt
  ├── .devcontainer/  # VS Code Devcontainer Setup
  ├── docker/         # Runtime-Dockerfile
  ├── .vscode/        # Debug-/Tasks-Konfiguration
  └── README.md
```

---

## 🚀 Schnellstart

### Mit Devcontainer
1. Projekt in **VS Code** öffnen.  
2. Auf „Reopen in Container“ klicken.  
3. EPUBs in `in/` legen.  
4. Run-Config **“Run script (workspace)”** starten → Ergebnisse erscheinen in `out/`.

### Mit Docker (Runtime)
```bash
docker build -t epub-imgsplit .
docker run --rm -v $PWD/in:/in -v $PWD/out:/out epub-imgsplit
```

---

## ⚙️ CLI
```bash
python src/epub_split_images.py --input ./in --output ./out [--images-only] [--min-width 2] [--min-height 2]
```

- `--images-only` → nur Bildseiten erzeugen (keine Textseiten).  
- `--min-width` / `--min-height` → filtert Mini-Platzhalterbilder (Default: 2×2).  

---

## 📖 Anwendungsfälle
- Aufbereitung von **Comic-EPUBs**, damit jede Seite genau ein Panel/Bild enthält.  
- Digitalisate, bei denen **Text und Bilder gemischt** vorliegen, klarer auftrennen.  
- EPUBs für **Reader-Apps oder Tools**, die besser mit einheitlichen Bildseiten umgehen.  

---

## 📜 Lizenz
Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).  
