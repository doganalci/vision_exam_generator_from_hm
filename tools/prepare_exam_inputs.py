"""
Per-student exam input bundle hazırlayıcı (CSE 463 — Computer Vision).
=====================================================================
Her öğrencinin raporunu (PDF/DOCX/MD) + kodunu (.py/.ipynb) + sonuç görsellerini
tek bir markdown bundle'ında toplar. Bu bundle bir Claude subagent tarafından
okunup öğrenciye özel sınav üretmek için kullanılır.

Büyük dosyalarla başa çıkma (ön-işleme):
- Rapor PDF: embedded text çıkarılır (OCR yok); text yoksa not düşülür.
- DOCX: python-docx ile paragraf metni (kurulu değilse zip XML fallback).
- Notebook (.ipynb): code + markdown hücreleri + (kısaltılmış) text çıktıları.
- Görseller: küçültülmüş thumbnail'lar `_processed/images/` altına yazılır ve
  bundle'da referanslanır — sınav üreten Claude bunları Read ile görebilir.
  (Markdown'a binary gömülmez; sadece path + meta.)
- Çok büyük data/model dosyaları: sadece isim + boyut listelenir, içerik okunmaz.

Çıktı:
    <submissions>/<student_id>/_exam_input.md
    <submissions>/<student_id>/_processed/images/*.jpg   (sampled thumbnails)

Kullanım:
    python tools/prepare_exam_inputs.py --submissions data/hw1/submissions --hw 1
    [--only 220104004061]   # tek öğrenci
    [--limit 5]             # ilk N (test)
    [--max-images 6]        # bundle'a örneklenen görsel sayısı
"""
import argparse
import json
import sys
from pathlib import Path

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- limitler ---------------------------------------------------------------
MAX_REPORT_CHARS = 25000     # rapordan çıkarılan text tavanı
MAX_CODE_FILES = 8           # bundle'a alınan en fazla kod dosyası
MAX_CODE_CHARS = 9000        # her kod dosyasından max karakter
MAX_NB_OUTPUT_CHARS = 500    # her notebook hücre çıktısından max karakter
THUMB_MAX_PX = 1024          # thumbnail uzun kenar
DEFAULT_MAX_IMAGES = 6       # bundle'a örneklenen görsel sayısı

PREFER_CODE_NAMES = ("main", "model", "train", "solution", "hw", "vision",
                     "detect", "segment", "filter", "feature")


# --- rapor metni ------------------------------------------------------------

def extract_pdf_text(pdf_path: Path, max_chars: int = MAX_REPORT_CHARS) -> str:
    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as e:
        return f"[PDF okunamadı: {e}]"
    chunks: list[str] = []
    total = 0
    for page_idx in range(len(doc)):
        t = doc[page_idx].get_text().strip()
        if not t:
            continue
        chunks.append(f"--- Sayfa {page_idx + 1} ---\n{t}")
        total += len(t)
        if total >= max_chars:
            chunks.append(f"\n[... toplam {max_chars}+ karakter, kalan atlandı]")
            break
    doc.close()
    return "\n\n".join(chunks) if chunks else "[PDF text içermiyor — image-based, OCR gerekir]"


def extract_docx_text(docx_path: Path, max_chars: int = MAX_REPORT_CHARS) -> str:
    try:
        import docx  # python-docx
        d = docx.Document(str(docx_path))
        text = "\n".join(p.text for p in d.paragraphs if p.text.strip())
        return text[:max_chars] if text.strip() else "[DOCX boş veya sadece görsel]"
    except ImportError:
        # Fallback: docx bir zip — word/document.xml'den kaba metin çek
        try:
            from zipfile import ZipFile
            import re
            with ZipFile(docx_path) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars] if text else "[DOCX metni çıkarılamadı]"
        except Exception as e:
            return f"[DOCX okunamadı: {e}]"
    except Exception as e:
        return f"[DOCX okunamadı: {e}]"


def extract_text_file(path: Path, max_chars: int = MAX_REPORT_CHARS) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception as e:
        return f"[okunamadı: {e}]"


def extract_report(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(path)
    if ext in (".docx", ".doc"):
        return extract_docx_text(path)
    return extract_text_file(path)


# --- kod --------------------------------------------------------------------

def extract_notebook(path: Path, max_chars: int = MAX_CODE_CHARS) -> str:
    """ipynb → code + markdown hücreleri + kısaltılmış text çıktıları."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return f"[notebook parse edilemedi: {e}]"
    out: list[str] = []
    total = 0
    for cell in nb.get("cells", []):
        ctype = cell.get("cell_type")
        src = "".join(cell.get("source", []))
        if not src.strip():
            continue
        if ctype == "markdown":
            block = f"# [markdown]\n{src}"
        elif ctype == "code":
            block = f"# [code]\n{src}"
            # text çıktılarını kısaca ekle
            outs = []
            for o in cell.get("outputs", []):
                txt = ""
                if o.get("output_type") == "stream":
                    txt = "".join(o.get("text", []))
                elif o.get("output_type") in ("execute_result", "display_data"):
                    data = o.get("data", {})
                    if "text/plain" in data:
                        txt = "".join(data["text/plain"])
                elif o.get("output_type") == "error":
                    txt = o.get("ename", "") + ": " + o.get("evalue", "")
                if txt.strip():
                    outs.append(txt.strip()[:MAX_NB_OUTPUT_CHARS])
            if outs:
                block += "\n# [output]\n" + "\n".join(outs)
        else:
            continue
        out.append(block)
        total += len(block)
        if total >= max_chars:
            out.append(f"\n# [... {max_chars}+ karakter, kalan hücreler atlandı]")
            break
    return "\n\n".join(out)


def pick_code_files(files: list[dict]) -> list[dict]:
    """Envanterden en alakalı kod dosyalarını seç (sığ derinlik + anlamlı isim öncelikli)."""
    code = [f for f in files if f["kind"] in ("code", "notebook")]

    def score(f: dict):
        name = Path(f["rel_path"]).stem.lower()
        depth = f["rel_path"].count("/")
        name_bonus = 0 if any(k in name for k in PREFER_CODE_NAMES) else 1
        return (name_bonus, depth, len(f["rel_path"]))

    code.sort(key=score)
    return code[:MAX_CODE_FILES]


# --- görsel ön-işleme -------------------------------------------------------

def make_thumbnails(files: list[dict], out_dir: Path, max_images: int) -> list[dict]:
    """Sonuç görsellerinden örneklem al, küçültülmüş thumbnail üret."""
    images = [f for f in files if f["kind"] == "image"]
    if not images:
        return []
    # Örnekleme: çok fazlaysa eşit aralıklı seç (ilk + son + aradan)
    if len(images) > max_images:
        step = len(images) / max_images
        sampled = [images[int(i * step)] for i in range(max_images)]
    else:
        sampled = images

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for idx, f in enumerate(sampled):
        src = Path(f["abs_path"])
        thumb_name = f"img_{idx:02d}{src.suffix.lower() if src.suffix.lower() in ('.jpg','.jpeg','.png') else '.jpg'}"
        thumb_path = out_dir / thumb_name
        meta = {"original": f["rel_path"], "thumb": None, "note": ""}
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
                im.save(thumb_path, "JPEG", quality=80)
            meta["thumb"] = thumb_path.relative_to(out_dir.parent.parent).as_posix()
        except ImportError:
            # PIL yoksa pymupdf ile dene
            try:
                pix = pymupdf.Pixmap(str(src))
                if pix.width > THUMB_MAX_PX or pix.height > THUMB_MAX_PX:
                    factor = THUMB_MAX_PX / max(pix.width, pix.height)
                    mat = pymupdf.Matrix(factor, factor)
                    pix = pymupdf.Pixmap(pix, 0)  # ensure no alpha
                pix.save(str(thumb_path))
                meta["thumb"] = thumb_path.relative_to(out_dir.parent.parent).as_posix()
            except Exception as e:
                meta["note"] = f"thumbnail üretilemedi (PIL yok): {e}"
        except Exception as e:
            meta["note"] = f"thumbnail üretilemedi: {e}"
        results.append(meta)
    return results


# --- bundle -----------------------------------------------------------------

def render_bundle(student_dir: Path, hw: int, max_images: int) -> str:
    info_path = student_dir / "_info.json"
    if not info_path.exists():
        return f"# HATA: _info.json bulunamadı ({student_dir})"

    info = json.loads(info_path.read_text(encoding="utf-8"))
    sid = info["student_id"]
    files = info["files"]
    counts = info["counts"]

    md: list[str] = []
    md.append(f"# Exam Input Bundle — Student {sid} (HW{hw})")
    md.append("")
    md.append(f"- **Student ID / folder:** {sid}  (`{info.get('source_folder_name', '')}`)")
    md.append(f"- **Homework:** {hw}")
    md.append(f"- **File counts:** " + ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    md.append(f"- **Total size:** {info.get('total_mb', 0)} MB")
    md.append("")

    # --- Rapor ---
    md.append("## Report")
    reports = [f for f in files if f["kind"] == "report" and not f["large"]]
    # PDF/DOCX öncelikli, sonra md/txt
    reports.sort(key=lambda f: (f["ext"] not in (".pdf", ".docx", ".doc"), f["rel_path"].count("/")))
    if reports:
        primary = reports[0]
        md.append(f"*Source: `{primary['rel_path']}` ({primary['size_mb']} MB)*")
        md.append("")
        md.append("```text")
        md.append(extract_report(Path(primary["abs_path"])))
        md.append("```")
        if len(reports) > 1:
            md.append("")
            md.append("*Other report-like files:* " + ", ".join(f"`{f['rel_path']}`" for f in reports[1:]))
    else:
        md.append("*[Rapor bulunamadı — PDF/DOCX/MD yok]*")
    md.append("")

    # --- Kod ---
    md.append("## Code")
    chosen = pick_code_files(files)
    if chosen:
        md.append(f"*Selected {len(chosen)} of {counts.get('code', 0)} code files (most relevant first).*")
        md.append("")
        for f in chosen:
            md.append(f"### `{f['rel_path']}`")
            p = Path(f["abs_path"])
            if f["kind"] == "notebook":
                content = extract_notebook(p)
                lang = "python"
            else:
                content = extract_text_file(p, MAX_CODE_CHARS)
                lang = f["ext"].lstrip(".") or "text"
            md.append(f"```{lang}")
            md.append(content)
            md.append("```")
            md.append("")
    else:
        md.append("*[Kod bulunamadı]*")
        md.append("")

    # --- Görseller (ön-işlenmiş) ---
    md.append("## Result Images (sampled, downscaled)")
    proc_dir = student_dir / "_processed" / "images"
    thumbs = make_thumbnails(files, proc_dir, max_images)
    all_images = [f for f in files if f["kind"] == "image"]
    if all_images:
        md.append(f"*{len(all_images)} image(s) in submission; {len(thumbs)} sampled below. "
                  f"To inspect, Read the thumbnail paths (relative to the student folder).*")
        md.append("")
        for t in thumbs:
            if t["thumb"]:
                md.append(f"- `{t['thumb']}`  (from `{t['original']}`)")
            else:
                md.append(f"- `{t['original']}` — {t['note']}")
        md.append("")
        md.append("*Full image list:*")
        for f in all_images[:40]:
            md.append(f"  - `{f['rel_path']}` ({f['size_mb']} MB)")
        if len(all_images) > 40:
            md.append(f"  - ... +{len(all_images) - 40} more")
    else:
        md.append("*[Sonuç görseli yok]*")
    md.append("")

    # --- Büyük / data dosyaları (sadece listele) ---
    big = [f for f in files if f["large"] or f["kind"] == "data"]
    if big:
        md.append("## Large / data / model files (listed only, not read)")
        for f in big[:40]:
            md.append(f"- `{f['rel_path']}` — {f['size_mb']} MB ({f['kind']})")
        if len(big) > 40:
            md.append(f"- ... +{len(big) - 40} more")
        md.append("")

    if info.get("warnings"):
        md.append("## Ingestion warnings")
        for w in info["warnings"]:
            md.append(f"- {w}")
        md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Per-student CV exam input bundle hazırlayıcı")
    parser.add_argument("--submissions", "-s", type=Path, required=True,
                        help="submissions klasörü (örn. data/hw1/submissions)")
    parser.add_argument("--hw", type=int, required=True, help="Ödev numarası")
    parser.add_argument("--only", type=str, default=None, help="Tek öğrenci ID")
    parser.add_argument("--limit", type=int, default=None, help="İlk N öğrenci (test)")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES,
                        help="Bundle'a örneklenen görsel sayısı")
    args = parser.parse_args()

    if not args.submissions.exists():
        print(f"❌ Klasör bulunamadı: {args.submissions}", file=sys.stderr)
        sys.exit(1)

    student_dirs = sorted([d for d in args.submissions.iterdir()
                           if d.is_dir() and (d / "_info.json").exists()])
    if args.only:
        student_dirs = [d for d in student_dirs if d.name == args.only]
        if not student_dirs:
            print(f"❌ Öğrenci ID bulunamadı: {args.only}", file=sys.stderr)
            sys.exit(1)
    if args.limit:
        student_dirs = student_dirs[: args.limit]

    print(f"🔧 İşlenecek öğrenci: {len(student_dirs)}")
    for sd in student_dirs:
        bundle = render_bundle(sd, args.hw, args.max_images)
        out_path = sd / "_exam_input.md"
        out_path.write_text(bundle, encoding="utf-8")
        size_kb = len(bundle.encode("utf-8")) / 1024
        print(f"   ✓ {sd.name}: {size_kb:.1f} KB")

    print(f"\n✅ Tamamlandı: {len(student_dirs)} bundle yazıldı")


if __name__ == "__main__":
    main()
