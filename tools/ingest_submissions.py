"""
Computer Vision homework submission ingester (CSE 463).
=======================================================
Girdi: içinde **her alt klasörü bir öğrenci** olan bir kök klasör.
    <input_root>/
        <student-folder-1>/      # klasör adı = öğrenci id/isim
            report.pdf
            hw1.ipynb
            src/main.py
            outputs/segmentation.png
            dataset/...            # büyük olabilir
        <student-folder-2>/
        ...

Çıktı: her öğrenci için normalize edilmiş, envanteri çıkarılmış klasör.
    <output>/                      (örn. data/hw1/submissions/)
        <student_id>/
            _info.json             # dosya envanteri + sınıflandırma + uyarılar
            (orijinal dosyalar kopyalanmaz — referans path saklanır)
        _index.json                # tüm öğrenci listesi

Dosya sınıflandırması (uzantıya göre):
    report   : .pdf .docx .doc .md .txt .rtf
    code     : .py .ipynb .m .cpp .c .h .hpp .cu .java
    notebook : .ipynb (code'un alt kümesi — ayrıca işaretlenir)
    image    : .png .jpg .jpeg .bmp .tif .tiff .gif .webp
    data     : .npy .npz .pt .pth .h5 .hdf5 .pkl .mat .csv .zip .tar .gz .onnx .pb .weights .ckpt
    other    : geri kalan

Büyük dosyalar (>LARGE_FILE_MB) kopyalanmaz; sadece path + boyut kaydedilir
(sınav üretiminde içerik gerekmez — token israfını önler).

Kullanım:
    python tools/ingest_submissions.py \
        --input /path/to/raw_submissions \
        --hw 1 \
        --output data/hw1/submissions
    # opsiyonlar:
    #   --copy            dosyaları output altına da kopyala (varsayılan: sadece referans)
    #   --extract-zips    öğrenci klasöründeki kod ziplerini aç (in-place, _extracted/ altına)
    #   --id-from {folder|regex}   öğrenci id'sini nasıl türeteceğini seç
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile, BadZipFile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ----- sınıflandırma tabloları ----------------------------------------------

REPORT_EXTS = {".pdf", ".docx", ".doc", ".md", ".txt", ".rtf"}
CODE_EXTS = {".py", ".ipynb", ".m", ".cpp", ".cc", ".c", ".h", ".hpp",
             ".cu", ".java", ".js", ".ts"}
NOTEBOOK_EXTS = {".ipynb"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp", ".ppm", ".pgm"}
DATA_EXTS = {".npy", ".npz", ".pt", ".pth", ".h5", ".hdf5", ".pkl", ".pickle",
             ".mat", ".csv", ".zip", ".tar", ".gz", ".rar", ".7z",
             ".onnx", ".pb", ".weights", ".ckpt", ".safetensors", ".bin", ".tflite"}

LARGE_FILE_MB = 5.0          # bundan büyük dosyalar kopyalanmaz (sadece referans)
IGNORE_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints", "node_modules",
               ".venv", "venv", ".idea", ".vscode", "__MACOSX"}
IGNORE_FILES = {".DS_Store", "Thumbs.db"}

# Öğrenci id'sini klasör adından çıkarmaya çalışan regex (8-12 haneli numara)
ID_RE = re.compile(r"(\d{6,12})")


def classify(ext: str) -> str:
    ext = ext.lower()
    if ext in REPORT_EXTS:
        return "report"
    if ext in CODE_EXTS:
        return "code"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in DATA_EXTS:
        return "data"
    return "other"


def derive_student_id(folder_name: str, mode: str) -> str:
    """Klasör adından öğrenci id türet."""
    if mode == "regex":
        m = ID_RE.search(folder_name)
        if m:
            return m.group(1)
    # folder modu (veya regex eşleşmedi): klasör adını sanitize et
    sid = re.sub(r"[^0-9A-Za-z._-]+", "_", folder_name.strip()).strip("_")
    return sid or folder_name.strip()


def human_mb(size_bytes: int) -> float:
    return round(size_bytes / (1024 * 1024), 3)


def scan_student_folder(folder: Path) -> dict:
    """Bir öğrenci klasörünü recursive gez, dosya envanteri çıkar."""
    files: list[dict] = []
    counts = {"report": 0, "code": 0, "notebook": 0, "image": 0, "data": 0, "other": 0}
    total_bytes = 0

    for p in sorted(folder.rglob("*")):
        if p.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.name in IGNORE_FILES:
            continue
        ext = p.suffix.lower()
        kind = classify(ext)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        rel = p.relative_to(folder).as_posix()
        is_notebook = ext in NOTEBOOK_EXTS
        entry = {
            "rel_path": rel,
            "abs_path": str(p.resolve()),
            "ext": ext,
            "kind": "notebook" if is_notebook else kind,
            "size_mb": human_mb(size),
            "large": size > LARGE_FILE_MB * 1024 * 1024,
        }
        files.append(entry)
        counts[kind] += 1
        if is_notebook:
            counts["notebook"] += 1
        total_bytes += size

    return {
        "files": files,
        "counts": counts,
        "total_mb": human_mb(total_bytes),
    }


def extract_zips(folder: Path) -> list[str]:
    """Öğrenci klasöründeki kod ziplerini _extracted/ altına aç."""
    notes: list[str] = []
    for zp in list(folder.rglob("*.zip")):
        if "_extracted" in zp.parts:
            continue
        dest = zp.parent / ("_extracted_" + zp.stem)
        if dest.exists():
            continue
        try:
            with ZipFile(zp) as zf:
                # Zip-slip koruması
                for member in zf.namelist():
                    target = (dest / member).resolve()
                    if not str(target).startswith(str(dest.resolve())):
                        notes.append(f"Zip-slip atlandı: {zp.name}:{member}")
                        continue
                zf.extractall(dest)
            notes.append(f"Açıldı: {zp.relative_to(folder)} → {dest.name}/")
        except (BadZipFile, OSError) as e:
            notes.append(f"Zip açılamadı ({zp.name}): {e}")
    return notes


def copy_small_files(scan: dict, student_dir: Path, src_root: Path) -> None:
    """Küçük dosyaları (kopyalanabilir olanları) output klasörüne kopyala."""
    files_root = student_dir / "files"
    for f in scan["files"]:
        if f["large"]:
            continue
        src = Path(f["abs_path"])
        dst = files_root / f["rel_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except OSError:
            pass


def process(input_root: Path, output_dir: Path, hw: int, id_mode: str,
            do_copy: bool, do_extract: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    student_folders = sorted([d for d in input_root.iterdir() if d.is_dir()
                              and d.name not in IGNORE_DIRS])
    print(f"📂 Girdi kökü: {input_root}")
    print(f"   Bulunan öğrenci klasörü: {len(student_folders)}")

    index_students: list[dict] = []
    seen_ids: dict[str, int] = {}

    for folder in student_folders:
        sid = derive_student_id(folder.name, id_mode)
        # id çakışması (aynı id iki klasör) — suffix ekle
        if sid in seen_ids:
            seen_ids[sid] += 1
            sid_final = f"{sid}__{seen_ids[sid]}"
        else:
            seen_ids[sid] = 0
            sid_final = sid

        extract_notes: list[str] = []
        if do_extract:
            extract_notes = extract_zips(folder)

        scan = scan_student_folder(folder)

        student_dir = output_dir / sid_final
        student_dir.mkdir(parents=True, exist_ok=True)

        if do_copy:
            copy_small_files(scan, student_dir, folder)

        warnings: list[str] = []
        if scan["counts"]["report"] == 0:
            warnings.append("Rapor (PDF/DOCX/MD) bulunamadı")
        if scan["counts"]["code"] == 0:
            warnings.append("Kod (.py/.ipynb) bulunamadı")

        info = {
            "student_id": sid_final,
            "source_folder_name": folder.name,
            "source_abs_path": str(folder.resolve()),
            "homework": hw,
            "copied_locally": do_copy,
            "counts": scan["counts"],
            "total_mb": scan["total_mb"],
            "files": scan["files"],
            "extract_notes": extract_notes,
            "warnings": warnings,
        }
        (student_dir / "_info.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        index_students.append({
            "id": sid_final,
            "source_folder": folder.name,
            "counts": scan["counts"],
            "total_mb": scan["total_mb"],
            "warnings": warnings,
        })

    index = {
        "homework": hw,
        "total_students": len(index_students),
        "input_root": str(input_root.resolve()),
        "students": sorted(index_students, key=lambda x: x["id"]),
    }
    index_path = output_dir / "_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    # Özet
    print(f"\n📋 Index yazıldı: {index_path}")
    print(f"\n✅ Tamamlandı: {len(index_students)} öğrenci işlendi")
    incomplete = [s for s in index_students if s["warnings"]]
    if incomplete:
        print(f"\n⚠ Uyarılı öğrenciler ({len(incomplete)}):")
        for s in incomplete[:20]:
            print(f"   {s['id']} ({s['source_folder']}): {', '.join(s['warnings'])}")
        if len(incomplete) > 20:
            print(f"   ... +{len(incomplete) - 20} daha (detay _index.json'da)")

    # Dosya türü dağılımı
    print(f"\n📊 Toplam dosya dağılımı:")
    agg = {"report": 0, "code": 0, "notebook": 0, "image": 0, "data": 0, "other": 0}
    for s in index_students:
        for k, v in s["counts"].items():
            agg[k] += v
    for k, v in agg.items():
        print(f"   {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="CSE 463 CV homework submission ingester (folder-per-student)")
    parser.add_argument("--input", "-i", type=Path, required=True,
                        help="Kök klasör (her alt klasör bir öğrenci)")
    parser.add_argument("--hw", type=int, required=True, help="Ödev numarası (1, 2, ...)")
    parser.add_argument("--output", "-o", type=Path, required=True,
                        help="Çıktı klasörü (örn. data/hw1/submissions)")
    parser.add_argument("--id-from", choices=["folder", "regex"], default="regex",
                        help="Öğrenci id'sini klasör adından mı (folder) yoksa içindeki numaradan mı (regex) türet")
    parser.add_argument("--copy", action="store_true",
                        help="Küçük dosyaları output altına kopyala (varsayılan: sadece referans path)")
    parser.add_argument("--extract-zips", action="store_true",
                        help="Öğrenci klasöründeki kod ziplerini in-place aç")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Girdi klasörü bulunamadı: {args.input}", file=sys.stderr)
        sys.exit(1)

    process(args.input, args.output, args.hw, args.id_from, args.copy, args.extract_zips)


if __name__ == "__main__":
    main()
