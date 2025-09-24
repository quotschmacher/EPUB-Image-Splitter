#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB-Umbau (Batch):
- JEDES Bild auf eine eigene Seite
- Optional: Text zwischen Bildern als eigene Seiten (Default: AN)
- Originale CSS-Dateien aus dem Manifest werden übernommen und eingebunden
- Platzhalter-Bilder (z.B. 1x1 PNGs) werden standardmäßig ignoriert

Usage:
  python epub_split_images.py --input /path/to/in --output /path/to/out
  # nur Bildseiten (keine Textseiten):
  python epub_split_images.py -i /in -o /out --images-only
  # minimale Bildgröße anpassen:
  python epub_split_images.py -i /in -o /out --min-width 2 --min-height 2

Benötigt:
  pip install lxml beautifulsoup4 Pillow
"""

import argparse
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from lxml import etree
from PIL import Image, UnidentifiedImageError

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"

def unzip_epub(epub_path: Path, out_dir: Path):
    with zipfile.ZipFile(epub_path, 'r') as zf:
        zf.extractall(out_dir)

def find_opf(root_dir: Path) -> Path:
    container_xml = root_dir / "META-INF" / "container.xml"
    if not container_xml.exists():
        raise RuntimeError("META-INF/container.xml nicht gefunden")
    tree = etree.parse(str(container_xml))
    ns = {"c": CONTAINER_NS}
    el = tree.find(".//c:rootfile", namespaces=ns)
    if el is None or "full-path" not in el.attrib:
        raise RuntimeError("OPF-Pfad in container.xml fehlt")
    return (root_dir / el.attrib["full-path"]).resolve()

def parse_opf(opf_path: Path):
    tree = etree.parse(str(opf_path))
    ns = {"opf": OPF_NS, "dc": DC_NS}
    pkg = tree.getroot()

    metadata = pkg.find("opf:metadata", ns)
    manifest = pkg.find("opf:manifest", ns)
    spine = pkg.find("opf:spine", ns)
    if manifest is None or spine is None:
        raise RuntimeError("Manifest/Spine im OPF fehlt")

    md = {"dc": [], "meta": []}
    if metadata is not None:
        for child in metadata:
            qn = etree.QName(child)
            if qn.namespace == DC_NS:
                md["dc"].append((qn.localname, (child.text or "").strip()))
            elif qn.namespace == OPF_NS and qn.localname == "meta":
                md["meta"].append((child.attrib.get("name"), child.attrib.get("content")))

    items_by_id, items_by_href = {}, {}
    for it in manifest.findall("opf:item", ns):
        iid = it.attrib.get("id")
        href = it.attrib.get("href")
        mt = it.attrib.get("media-type")
        props = it.attrib.get("properties", "")
        if iid and href and mt:
            item = {"id": iid, "href": href, "media-type": mt, "properties": props}
            items_by_id[iid] = item
            items_by_href[href] = item

    spine_ids = [ref.attrib.get("idref") for ref in spine.findall("opf:itemref", ns)]
    spine_hrefs = [items_by_id[sid]["href"] for sid in spine_ids if sid in items_by_id]
    return md, items_by_id, items_by_href, spine_hrefs

def guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in [".xhtml", ".html", ".htm"]: return "application/xhtml+xml"
    if ext == ".css": return "text/css"
    if ext in [".jpg", ".jpeg"]: return "image/jpeg"
    if ext == ".png": return "image/png"
    if ext == ".gif": return "image/gif"
    if ext == ".svg": return "image/svg+xml"
    if ext == ".ttf": return "font/ttf"
    if ext == ".otf": return "font/otf"
    if ext == ".woff": return "font/woff"
    if ext == ".woff2": return "font/woff2"
    return "application/octet-stream"

def slugify(text: str) -> str:
    text = re.sub(r"\s+", "-", text.strip())
    return re.sub(r"[^A-Za-z0-9_\-\.]", "", text) or "untitled"

PAGE_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <meta charset="utf-8" />
{css_links}
</head>
<body>
  <div class="page">
    <img src="../Images/{img_href}" alt="{alt}" />
  </div>
</body>
</html>
"""

TEXT_PAGE_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <meta charset="utf-8" />
{css_links}
</head>
<body>
  <div class="page textpage">
{content}
  </div>
</body>
</html>
"""

def build_new_epub(
    temp_src: Path,
    opf_path: Path,
    md,
    items_by_href,
    spine_hrefs,
    out_path: Path,
    images_only: bool = False,
    min_w: int = 2,
    min_h: int = 2,
):
    newroot = Path(tempfile.mkdtemp(prefix="epubbuild_"))
    try:
        (newroot / "META-INF").mkdir(parents=True, exist_ok=True)
        (newroot / "OEBPS" / "Text").mkdir(parents=True, exist_ok=True)
        (newroot / "OEBPS" / "Images").mkdir(parents=True, exist_ok=True)
        (newroot / "OEBPS" / "Styles").mkdir(parents=True, exist_ok=True)

        container_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="{CONTAINER_NS}">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        (newroot / "META-INF" / "container.xml").write_text(container_xml, encoding="utf-8")

        opf_dir = opf_path.parent

        css_files = []
        for href, it in items_by_href.items():
            if it["media-type"] == "text/css":
                src = (opf_dir / href).resolve()
                if src.exists():
                    dst = newroot / "OEBPS" / "Styles" / Path(href).name
                    dst.write_bytes(src.read_bytes())
                    css_files.append("Styles/" + Path(href).name)
        css_links_html = "\n".join(
            f'  <link rel="stylesheet" type="text/css" href="../{css}"/>' for css in css_files
        )

        img_manifest, page_manifest, navpoints = [], [], []
        img_id_counter, page_id_counter, text_seq_counter = 1, 1, 1
        copied_images = {}

        def copy_image(src_path: Path):
            nonlocal img_id_counter
            try:
                with Image.open(src_path) as im:
                    w, h = im.size
                if w < min_w or h < min_h:
                    print(f"    [skip] Platzhalter-Bild ignoriert ({w}x{h}): {src_path.name}")
                    return None
            except (UnidentifiedImageError, OSError):
                pass
            name = f"img{img_id_counter:04d}{src_path.suffix.lower()}"
            img_id_counter += 1
            dest = newroot / "OEBPS" / "Images" / name
            dest.write_bytes(src_path.read_bytes())
            img_manifest.append((f"img{img_id_counter}", f"Images/{name}", guess_mime(dest)))
            return name

        def write_image_page(newname: str, alt_text: str):
            nonlocal page_id_counter
            title = Path(newname).stem
            page_name = f"imgpage{page_id_counter:04d}.xhtml"
            page_id_counter += 1
            content = PAGE_TEMPLATE.format(title=title, img_href=newname, alt=alt_text, css_links=css_links_html)
            (newroot / "OEBPS" / "Text" / page_name).write_text(content, encoding="utf-8")
            page_manifest.append((Path(page_name).stem, f"Text/{page_name}", "application/xhtml+xml"))
            navpoints.append((title, f"Text/{page_name}"))

        def write_text_page(fragment_html: str, suggest_title: str):
            nonlocal page_id_counter, text_seq_counter
            if images_only:
                return
            if not fragment_html or not fragment_html.strip():
                return
            title = f"{suggest_title or 'Text'} {text_seq_counter}"
            text_seq_counter += 1
            page_name = f"textpage{page_id_counter:04d}.xhtml"
            page_id_counter += 1
            content = TEXT_PAGE_TEMPLATE.format(title=title, content=fragment_html, css_links=css_links_html)
            (newroot / "OEBPS" / "Text" / page_name).write_text(content, encoding="utf-8")
            page_manifest.append((Path(page_name).stem, f"Text/{page_name}", "application/xhtml+xml"))
            navpoints.append((title, f"Text/{page_name}"))

        def extract_text_fragment(nodes):
            frag = BeautifulSoup("<div></div>", "lxml")
            root = frag.div
            for node in nodes:
                if getattr(node, "name", None) in ("img", "script", "style"):
                    continue
                clone = BeautifulSoup(str(node), "lxml")
                for im in clone.find_all("img"):
                    im.decompose()
                if clone.get_text(strip=True):
                    root.append(clone)
            return "".join(str(c) for c in root.children)

        html_candidates = [h for h in spine_hrefs if h and h.lower().endswith((".xhtml", ".html", ".htm"))]
        if not html_candidates:
            html_candidates = [href for href, it in items_by_href.items()
                               if it["media-type"] in ("application/xhtml+xml", "text/html")]

        for html_href in html_candidates:
            original_html = (opf_dir / html_href).resolve()
            if not original_html.exists():
                continue
            soup = BeautifulSoup(original_html.read_text(encoding="utf-8", errors="ignore"), "lxml")
            body = soup.body or soup
            base_title = Path(html_href).stem

            pending_text_nodes = []

            def flush_text():
                nonlocal pending_text_nodes
                if not images_only and pending_text_nodes:
                    fragment_html = extract_text_fragment(pending_text_nodes)
                    write_text_page(fragment_html, base_title)
                    pending_text_nodes = []

            for node in body.descendants:
                if getattr(node, "name", None) == "img":
                    flush_text()
                    src = node.get("src")
                    if not src:
                        continue
                    src_path = (original_html.parent / src).resolve()
                    if not src_path.exists():
                        alt_try = (opf_dir / src).resolve()
                        if alt_try.exists():
                            src_path = alt_try
                        else:
                            continue
                    key = str(src_path)
                    if key not in copied_images:
                        newname = copy_image(src_path)
                        if not newname:
                            continue
                        copied_images[key] = newname
                    else:
                        newname = copied_images[key]
                    alt_text = node.get("alt") or Path(newname).stem
                    write_image_page(newname, alt_text)
                else:
                    pending_text_nodes.append(node)
            flush_text()

        if not page_manifest:
            raise RuntimeError("Keine Seiten entstanden – weder Bilder noch Text gefunden.")

        # --- UID/Identifier erzeugen & überall konsistent setzen ---
        # Versuche zuerst einen bestehenden dc:identifier zu finden
        existing_identifier = next((v for k, v in md["dc"] if k == "identifier" and v), None)
        book_uid = existing_identifier or f"urn:uuid:{uuid4()}"

        # toc.ncx
        ncx_path = newroot / "OEBPS" / "toc.ncx"
        ncx_root = etree.Element(f"{{{NCX_NS}}}ncx", nsmap={None: NCX_NS})
        ncx_root.set("version", "2005-1")
        head = etree.SubElement(ncx_root, f"{{{NCX_NS}}}head")
        etree.SubElement(head, f"{{{NCX_NS}}}meta", name="dtb:uid", content=book_uid)  # <-- konsistent!
        etree.SubElement(head, f"{{{NCX_NS}}}meta", name="dtb:depth", content="1")
        doctitle = etree.SubElement(ncx_root, f"{{{NCX_NS}}}docTitle")
        etree.SubElement(doctitle, f"{{{NCX_NS}}}text").text = next((v for k, v in md["dc"] if k == "title"), "Bilder")
        navmap = etree.SubElement(ncx_root, f"{{{NCX_NS}}}navMap")
        for i, (label, src) in enumerate(navpoints, 1):
            np = etree.SubElement(navmap, f"{{{NCX_NS}}}navPoint", id=f"np{i}", playOrder=str(i))
            navlabel = etree.SubElement(np, f"{{{NCX_NS}}}navLabel")
            etree.SubElement(navlabel, f"{{{NCX_NS}}}text").text = label
            etree.SubElement(np, f"{{{NCX_NS}}}content", src=src)
        ncx_path.write_bytes(etree.tostring(ncx_root, encoding="utf-8", xml_declaration=True, pretty_print=True))

        # content.opf
        opf_new = newroot / "OEBPS" / "content.opf"
        pkg = etree.Element(f"{{{OPF_NS}}}package", nsmap={None: OPF_NS, "dc": DC_NS})
        pkg.set("version", "2.0")
        pkg.set("unique-identifier", "BookId")  # <-- verweist auf dc:identifier mit id=BookId

        meta_el = etree.SubElement(pkg, f"{{{OPF_NS}}}metadata")
        # vorhandene dc:* übernehmen
        for k, v in md["dc"]:
            if not v:
                continue
            # wir duplizieren identifier nicht; der "kanonische" kommt gleich
            if k == "identifier":
                continue
            el = etree.SubElement(meta_el, f"{{{DC_NS}}}{k}")
            el.text = v
        # kanonischen Identifier einfügen
        id_el = etree.SubElement(meta_el, f"{{{DC_NS}}}identifier", id="BookId")
        id_el.text = book_uid
        # einfache <meta>-Einträge übernehmen
        for name, content in md["meta"]:
            if name and content:
                etree.SubElement(meta_el, f"{{{OPF_NS}}}meta", name=name, content=content)

        manifest_el = etree.SubElement(pkg, f"{{{OPF_NS}}}manifest")
        etree.SubElement(manifest_el, f"{{{OPF_NS}}}item", id="ncx", href="toc.ncx", **{"media-type": "application/x-dtbncx+xml"})
        for css in css_files:
            etree.SubElement(manifest_el, f"{{{OPF_NS}}}item", id=slugify(Path(css).stem), href=css, **{"media-type": "text/css"})
        for pid, href, mt in page_manifest:
            etree.SubElement(manifest_el, f"{{{OPF_NS}}}item", id=pid, href=href, **{"media-type": mt})
        for iid, href, mt in img_manifest:
            etree.SubElement(manifest_el, f"{{{OPF_NS}}}item", id=slugify(iid), href=href, **{"media-type": mt})

        spine_el = etree.SubElement(pkg, f"{{{OPF_NS}}}spine", toc="ncx")
        for pid, href, mt in page_manifest:
            etree.SubElement(spine_el, f"{{{OPF_NS}}}itemref", idref=pid)

        opf_new.write_bytes(etree.tostring(pkg, encoding="utf-8", xml_declaration=True, pretty_print=True))

        # EPUB packen: mimetype zuerst & unkomprimiert
        with zipfile.ZipFile(out_path, "w") as z:
            z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            for base, _, files in os.walk(newroot):
                for fn in files:
                    rel = os.path.relpath(os.path.join(base, fn), newroot)
                    if rel == "mimetype":
                        continue
                    z.write(os.path.join(base, fn), rel)
    finally:
        shutil.rmtree(newroot, ignore_errors=True)

def process_one(epub_file: Path, out_dir: Path, **kwargs):
    base = epub_file.stem
    out_path = out_dir / f"{base}_imgsplit.epub"
    with tempfile.TemporaryDirectory(prefix="epubwork_") as tmp:
        tmpdir = Path(tmp)
        unzip_epub(epub_file, tmpdir)
        opf_path = find_opf(tmpdir)
        md, items_by_id, items_by_href, spine_hrefs = parse_opf(opf_path)
        build_new_epub(tmpdir, opf_path, md, items_by_href, spine_hrefs, out_path, **kwargs)
    return out_path

def main():
    ap = argparse.ArgumentParser(description="EPUB -> Bildseiten + (optional) Textseiten dazwischen, inkl. CSS-Übernahme.")
    ap.add_argument("--input", "-i", required=True, help="Input-Verzeichnis mit .epub")
    ap.add_argument("--output", "-o", required=True, help="Output-Verzeichnis für *_imgsplit.epub")
    ap.add_argument("--images-only", action="store_true", help="Nur Bildseiten erzeugen (keine Textseiten).")
    ap.add_argument("--min-width", type=int, default=2, help="Minimale Bildbreite; kleinere Bilder werden ignoriert (Default: 2).")
    ap.add_argument("--min-height", type=int, default=2, help="Minimale Bildhöhe; kleinere Bilder werden ignoriert (Default: 2).")
    args = ap.parse_args()

    in_dir = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    epubs = sorted(in_dir.glob("*.epub"))
    if not epubs:
        print(f"Keine EPUBs in {in_dir}")
        return

    ok, fail = 0, 0
    for f in epubs:
        try:
            print(f"[+] Verarbeite: {f.name}")
            outp = process_one(
                f,
                out_dir,
                images_only=args.images_only,
                min_w=args.min_width,
                min_h=args.min_height,
            )
            print(f"    -> {outp.name}")
            ok += 1
        except Exception as e:
            print(f"[!] Fehler bei {f.name}: {e}")
            fail += 1
    print(f"Fertig. Erfolgreich: {ok}, Fehlgeschlagen: {fail}")

if __name__ == "__main__":
    main()
