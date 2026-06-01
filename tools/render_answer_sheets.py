"""
Lined answer-sheet generator (CSE 463).
=======================================
Her std_code için çizgili boş cevap kağıdı paketi üretir:
- N sayfa (her soru için bir sayfa, varsayılan 4)
- Her sayfada: sol üstte basılı **Student Code**, başlıkta **Question N**, altında çizgiler
- Sınava girişte öğrenciye geliş sırasıyla rastgele dağıtılır (anonimleştirme)

Kullanım:
    python tools/render_answer_sheets.py --codes 100,102,104 --output data/hw1/answer-sheets
    python tools/render_answer_sheets.py --codes-file codes.txt --pages 4 --output ...
"""
import argparse
import sys
from pathlib import Path

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COURSE_CODE = "CSE 463"

CSS = """
body { font-family: sans-serif; color: #000; }
.sheet-header {
    border-bottom: 1.5px solid #000;
    padding-bottom: 6pt;
    margin-bottom: 4pt;
}
.code-box {
    font-size: 13pt;
    font-weight: bold;
    letter-spacing: 1pt;
}
.qtitle {
    font-size: 12pt;
    font-weight: bold;
    margin: 4pt 0;
}
.meta { font-size: 9pt; color: #333; }
.line {
    border-bottom: 1px solid #999;
    height: 26pt;
}
"""


def render_sheet_html(code: str, q_num: int, n_lines: int = 24) -> str:
    lines = "".join('<div class="line"></div>' for _ in range(n_lines))
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<table style="width:100%; border:none; border-collapse:collapse;">
  <tr>
    <td style="border:none; vertical-align:top; padding:0;">
      <span class="code-box">Student Code: {code}</span>
    </td>
    <td style="border:none; vertical-align:top; text-align:right; padding:0;">
      <span class="meta">{COURSE_CODE} — Answer Sheet</span>
    </td>
  </tr>
</table>
<div class="sheet-header"></div>
<div class="qtitle">Question {q_num}</div>
{lines}
</body></html>"""


def render_packet(code: str, out_path: Path, pages: int) -> None:
    mediabox = pymupdf.paper_rect("a4")
    margin = 36
    where = pymupdf.Rect(margin, margin, mediabox.x1 - margin, mediabox.y1 - margin)
    writer = pymupdf.DocumentWriter(str(out_path))
    for q in range(1, pages + 1):
        html = render_sheet_html(code, q)
        story = pymupdf.Story(html=html)
        more = 1
        while more:
            dev = writer.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(dev, where)
            writer.end_page()
    writer.close()


def main():
    parser = argparse.ArgumentParser(description="Lined answer-sheet packet generator")
    parser.add_argument("--codes", type=str, default=None, help="Virgülle ayrılmış std_code listesi")
    parser.add_argument("--codes-file", type=Path, default=None, help="Her satırda bir std_code olan dosya")
    parser.add_argument("--pages", type=int, default=4, help="Soru/sayfa sayısı (varsayılan 4)")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Çıktı klasörü")
    args = parser.parse_args()

    codes: list[str] = []
    if args.codes:
        codes += [c.strip() for c in args.codes.split(",") if c.strip()]
    if args.codes_file and args.codes_file.exists():
        codes += [ln.strip() for ln in args.codes_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not codes:
        print("❌ Hiç std_code verilmedi (--codes veya --codes-file).", file=sys.stderr)
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    for code in codes:
        out_path = args.output / f"answer_sheets_{code}.pdf"
        render_packet(code, out_path, args.pages)
        print(f"✓ {out_path.name} ({args.pages} sayfa)")

    print(f"\n✅ {len(codes)} cevap kağıdı paketi → {args.output}")


if __name__ == "__main__":
    main()
