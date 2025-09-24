# 1) Build (einmalig oder bei Änderungen)
docker compose build

# 2) Standardlauf (Textseiten + Bildseiten)
docker compose up epub-imgsplit

# 3) Nur Bildseiten
docker compose up epub-imgsplit-images-only

# 4) Strenger Bild-Filter (z.B. 1x1/2x2-Platzhalter raus)
docker compose up epub-imgsplit-strict-filter
