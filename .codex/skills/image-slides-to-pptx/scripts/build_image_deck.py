#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


SLIDE_W = 9144000
SLIDE_H = 5143500
IMAGE_EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
DEFAULT_THEME_PROFILE = "tech-blue"
THEME_PROFILES = {
    "tech-blue": {
        "font": "Microsoft YaHei", "primary_color": "123B6D", "accent_color": "19A7A0",
        "highlight_color": "D4A64A", "muted_color": "8493A5", "section_number_color": "D9E2EC",
        "cover_eyebrow": "PRESENTATION", "part_label": "PART", "title_position": "top-left",
        "show_page_number": True, "show_section_label": True,
    },
    "financial-red": {
        "font": "Microsoft YaHei", "primary_color": "8F1022", "accent_color": "C8152D",
        "highlight_color": "D4A64A", "muted_color": "777777", "section_number_color": "E8D8DB",
        "cover_eyebrow": "BUSINESS PRESENTATION", "part_label": "PART", "title_position": "top-left",
        "show_page_number": True, "show_section_label": True,
    },
    "consulting-navy": {
        "font": "Arial", "primary_color": "17365D", "accent_color": "4F81BD",
        "highlight_color": "C9A227", "muted_color": "7F8C9A", "section_number_color": "DCE6F1",
        "cover_eyebrow": "EXECUTIVE BRIEFING", "part_label": "SECTION", "title_position": "top-left",
        "show_page_number": True, "show_section_label": True,
    },
    "government-blue": {
        "font": "Microsoft YaHei", "primary_color": "174A7E", "accent_color": "2F75B5",
        "highlight_color": "D6A84B", "muted_color": "74879A", "section_number_color": "D9EAF7",
        "cover_eyebrow": "专题汇报", "part_label": "篇章", "title_position": "top-left",
        "show_page_number": True, "show_section_label": True,
    },
    "minimal-gray": {
        "font": "Microsoft YaHei", "primary_color": "252525", "accent_color": "666666",
        "highlight_color": "B08D57", "muted_color": "8A8A8A", "section_number_color": "E6E6E6",
        "cover_eyebrow": "PRESENTATION", "part_label": "SECTION", "title_position": "top-left",
        "show_page_number": True, "show_section_label": False,
    },
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_theme(profile: str, path: Path | None) -> dict:
    theme = dict(THEME_PROFILES[profile])
    if path:
        overrides = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(overrides, dict):
            fail("Theme JSON must contain an object")
        unknown = sorted(set(overrides) - set(theme))
        if unknown:
            fail(f"Unknown theme keys: {unknown}")
        theme.update(overrides)
    for key in ("primary_color", "accent_color", "highlight_color", "muted_color", "section_number_color"):
        value = str(theme[key]).lstrip("#").upper()
        if not re.fullmatch(r"[0-9A-F]{6}", value):
            fail(f"Theme color '{key}' must be a six-digit hex value")
        theme[key] = value
    if theme["title_position"] not in ("top-left", "top-center"):
        fail("Theme title_position must be 'top-left' or 'top-center'")
    return theme


def discover_images(images_dir: Path) -> list[Path]:
    if not images_dir.is_dir():
        fail(f"Images directory does not exist: {images_dir}")
    numbered: dict[int, Path] = {}
    for path in images_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if not path.stem.isdigit():
            continue
        number = int(path.stem)
        if number in numbered:
            fail(f"Duplicate image number {number}: {numbered[number].name}, {path.name}")
        numbered[number] = path
    if not numbered:
        fail(f"No numbered PNG/JPEG images found in {images_dir}")
    expected = set(range(1, max(numbered) + 1))
    missing = sorted(expected - set(numbered))
    if missing:
        fail(f"Missing image sequence numbers: {missing}")
    return [numbered[index] for index in sorted(numbered)]


def parse_titles(path: Path | None) -> list[dict]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8-sig")
    rows = []
    for line in text.splitlines():
        match = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|$", line)
        if match and match.group(1).isdigit():
            rows.append({
                "page": int(match.group(1)),
                "source": match.group(2).strip(),
                "kind": match.group(3).strip(),
                "title": match.group(4).strip(),
            })
    if rows:
        rows.sort(key=lambda row: row["page"])
        return rows

    for line in text.splitlines():
        match = re.match(r"^\s*(\d+)[.)、]\s*(.+?)\s*$", line)
        if match:
            rows.append({
                "page": int(match.group(1)),
                "source": f"Page {match.group(1)}",
                "kind": "content",
                "title": match.group(2).strip(),
            })
    rows.sort(key=lambda row: row["page"])
    return rows


def is_cover(row: dict, index: int) -> bool:
    return index == 1 and ("封面" in row["kind"] or row["kind"].lower() == "cover")


def is_section(row: dict) -> bool:
    value = f'{row["kind"]} {row["source"]}'.lower()
    return any(token in value for token in ("章节", "过渡", "section", "chapter", "part"))


def text_shape(shape_id, name, text, x, y, w, h, size, color, font, bold=False, align="l"):
    bold_attr = ' b="1"' if bold else ""
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr wrap="none" anchor="ctr"/><a:lstStyle/><a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="zh-CN" sz="{size}"{bold_attr} dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{escape(font)}"/><a:ea typeface="{escape(font)}"/></a:rPr><a:t>{escape(text)}</a:t></a:r><a:endParaRPr lang="zh-CN" sz="{size}"/></a:p></p:txBody></p:sp>'''


def rect_shape(shape_id, name, x, y, w, h, color):
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>'''


def title_font_size(title: str, base: int) -> int:
    if len(title) > 30:
        return max(base - 400, 1600)
    if len(title) > 23:
        return max(base - 200, 1800)
    return base


def decorations(row: dict, page: int, total: int, style: str, section_number: int, theme: dict) -> str:
    if style == "plain":
        return ""
    title = row["title"]
    section = is_section(row)
    cover = is_cover(row, page)
    shapes = []
    font = theme["font"]
    primary = theme["primary_color"]
    accent = theme["accent_color"]
    highlight = theme["highlight_color"]
    title_x, title_w, title_align = (650000, 6900000, "l")
    if theme["title_position"] == "top-center":
        title_x, title_w, title_align = (850000, 7440000, "ctr")
    if style == "title":
        size = title_font_size(title, 2200 if not cover else 3000)
        shapes.append(text_shape(3, "页面标题", title, 650000, 250000, 7900000, 600000, size, primary, font, True))
        return "".join(shapes)
    if cover:
        shapes.append(text_shape(3, "封面眉题", theme["cover_eyebrow"], 650000, 130000, 3000000, 260000, 1200, accent, font, True))
        shapes.append(text_shape(4, "封面主标题", title, 650000, 330000, 7900000, 620000, title_font_size(title, 3000), primary, font, True))
        shapes.append(rect_shape(5, "封面强调短线", 650000, 945000, 820000, 22000, highlight))
        return "".join(shapes)
    if section:
        number = f"{section_number:02d}"
        shapes.append(text_shape(3, "章节浅色大序号", number, 500000, 60000, 1450000, 850000, 6000, theme["section_number_color"], font, True))
        shapes.append(text_shape(4, "章节标签", f'{theme["part_label"]} {number}', 670000, 130000, 2200000, 240000, 1200, accent, font, True))
        shapes.append(text_shape(5, "章节标题", title, 670000, 360000, 7800000, 500000, title_font_size(title, 2600), primary, font, True))
        shapes.append(rect_shape(6, "章节强调短线", 670000, 865000, 900000, 22000, highlight))
        return "".join(shapes)
    if theme["title_position"] == "top-left":
        shapes.append(rect_shape(3, "标题科技青竖线", 510000, 260000, 42000, 390000, accent))
    shapes.append(text_shape(4, "页面标题", title, title_x, 220000, title_w, 480000, title_font_size(title, 2200), primary, font, True, title_align))
    shapes.append(rect_shape(5, "标题强调短线", title_x, 700000, 780000, 18000, highlight))
    if section_number and theme["show_section_label"]:
        shapes.append(text_shape(6, "右上章节标识", f'{theme["part_label"]} {section_number:02d}', 7300000, 200000, 1400000, 260000, 1050, accent, font, True, "r"))
    if theme["show_page_number"]:
        shapes.append(text_shape(7, "右上页码", f"{page:02d} / {total:02d}", 7850000, 455000, 850000, 200000, 900, theme["muted_color"], font, False, "r"))
    return "".join(shapes)


def build_deck(images: list[Path], rows: list[dict], output: Path, style: str, theme: dict) -> None:
    total = len(images)
    if style != "plain" and not rows:
        fail(f"Style '{style}' requires a title file")
    if rows and len(rows) != total:
        fail(f"Title count {len(rows)} does not match image count {total}")
    if rows and [row["page"] for row in rows] != list(range(1, total + 1)):
        fail("Title page numbers must be continuous from 1")
    if not rows:
        rows = [{"page": i, "source": f"Page {i}", "kind": "content", "title": ""} for i in range(1, total + 1)]

    content_types = ['''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="jpeg" ContentType="image/jpeg"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>''']
    content_types.extend(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, total + 1))
    content_types.append("</Types>")

    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 2}"/>' for i in range(1, total + 1))
    presentation = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst><p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle><a:defPPr><a:defRPr lang="zh-CN"/></a:defPPr></p:defaultTextStyle></p:presentation>'''
    presentation_rels = ['''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>''']
    presentation_rels.extend(f'<Relationship Id="rId{i + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, total + 1))
    presentation_rels.append("</Relationships>")

    font = escape(theme["font"])
    theme_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Image Deck"><a:themeElements><a:clrScheme name="Image Deck"><a:dk1><a:srgbClr val="{theme["primary_color"]}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F6F9"/></a:lt2><a:accent1><a:srgbClr val="{theme["primary_color"]}"/></a:accent1><a:accent2><a:srgbClr val="{theme["accent_color"]}"/></a:accent2><a:accent3><a:srgbClr val="{theme["highlight_color"]}"/></a:accent3><a:accent4><a:srgbClr val="C94A4A"/></a:accent4><a:accent5><a:srgbClr val="{theme["muted_color"]}"/></a:accent5><a:accent6><a:srgbClr val="{theme["section_number_color"]}"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="Image Deck"><a:majorFont><a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="Arial"/></a:majorFont><a:minorFont><a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="Arial"/></a:minorFont></a:fontScheme><a:fmtScheme name="Image Deck"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'''
    master = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'''
    master_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>'''
    layout = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'''
    layout_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'''
    app = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Microsoft Office PowerPoint</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>{total}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop><AppVersion>16.0000</AppVersion></Properties>'''
    core = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Image Slide Deck</dc:title><dc:creator>image-slides-to-pptx</dc:creator></cp:coreProperties>'''

    output.parent.mkdir(parents=True, exist_ok=True)
    current_section = 0
    with ZipFile(output, "w", ZIP_DEFLATED) as deck:
        deck.writestr("[Content_Types].xml", "".join(content_types))
        deck.writestr("_rels/.rels", root_rels)
        deck.writestr("docProps/app.xml", app)
        deck.writestr("docProps/core.xml", core)
        deck.writestr("ppt/presentation.xml", presentation)
        deck.writestr("ppt/_rels/presentation.xml.rels", "".join(presentation_rels))
        deck.writestr("ppt/theme/theme1.xml", theme_xml)
        deck.writestr("ppt/slideMasters/slideMaster1.xml", master)
        deck.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        deck.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        deck.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        for index, (image, row) in enumerate(zip(images, rows), 1):
            if is_section(row):
                current_section += 1
            extra = decorations(row, index, total, style, current_section, theme)
            slide = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/><p:pic><p:nvPicPr><p:cNvPr id="2" name="Background Image {index}" descr="{escape(image.name)}"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_W}" cy="{SLIDE_H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>{extra}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''
            extension = image.suffix.lower().lstrip(".")
            media_name = f"image{index}.{extension}"
            rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{media_name}"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>'''
            deck.writestr(f"ppt/slides/slide{index}.xml", slide)
            deck.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", rels)
            deck.write(image, f"ppt/media/{media_name}")


def validate_deck(output: Path, images: list[Path], style: str, titles: int, theme_profile: str) -> dict:
    with ZipFile(output) as deck:
        bad = deck.testzip()
        if bad:
            fail(f"Corrupt PPTX entry: {bad}")
        names = deck.namelist()
        slide_names = [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        media_names = [name for name in names if re.fullmatch(r"ppt/media/image\d+\.(png|jpg|jpeg)", name)]
        for name in names:
            if name.endswith((".xml", ".rels")):
                ET.fromstring(deck.read(name))
        all_match = True
        for index, image in enumerate(images, 1):
            embedded = f"ppt/media/image{index}.{image.suffix.lower().lstrip('.')}"
            all_match &= hashlib.sha256(image.read_bytes()).digest() == hashlib.sha256(deck.read(embedded)).digest()
    return {
        "output": str(output.resolve()),
        "slides": len(slide_names),
        "images": len(media_names),
        "titles": titles,
        "style": style,
        "theme_profile": theme_profile,
        "canvas": "16:9",
        "all_images_match": bool(all_match),
        "zip_valid": True,
        "xml_valid": True,
        "bytes": output.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert numbered slide images into a validated 16:9 PPTX deck")
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--titles", type=Path)
    parser.add_argument("--style", choices=("plain", "title", "decorated"), default="plain")
    parser.add_argument("--theme-profile", choices=tuple(THEME_PROFILES), default=DEFAULT_THEME_PROFILE)
    parser.add_argument("--theme", type=Path, help="Optional JSON overrides for the selected theme profile")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        images = discover_images(args.images_dir)
        rows = parse_titles(args.titles)
        theme = load_theme(args.theme_profile, args.theme)
        build_deck(images, rows, args.output, args.style, theme)
        report = validate_deck(args.output, images, args.style, len(rows), args.theme_profile)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
