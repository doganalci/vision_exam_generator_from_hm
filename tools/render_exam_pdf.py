"""
Per-student exam PDF/MD renderer (CSE 463 — Computer Vision).
=============================================================
Bir öğrencinin exam.json'ından iki çıktı üretir:
- exam.pdf : ÖĞRENCİYE basılır — siyah-beyaz, sadece sorular, sağ üstte boş STD_CODE alanı.
             Cevap kutusu YOK — cevaplar ayrı çizgili kağıtlara (answer_sheets) yazılır.
- key.md   : SADECE TA/AI için — expected_answer + rubric markdown formatında.
             AI grading'e direkt yapıştırılır, PDF parsing token israfı yok.

CSE 341 (Concepts of PL) template'inden uyarlandı. Şema aynı (4 soru × 25pt = 100pt),
sadece domain Computer Vision: 'sebesta_chapter' yerine 'reference' alanı kullanılır.

Kullanım:
    python tools/render_exam_pdf.py --exam data/hw1/exams/{id}/exam.json
    # → aynı klasörde exam.pdf ve key.md yazar
"""
import argparse
import json
import sys
from pathlib import Path

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


COURSE_CODE = "CSE 463"  # Computer Vision

# Siyah-beyaz baskı için gri tonları, mavi/renk yok
# Kompakt — 2 sayfaya sığacak (arkalı önlü tek kağıt)
CSS_COMMON = """
body {
    font-family: sans-serif;
    font-size: 8.5pt;
    line-height: 1.2;
    color: #000;
}
.header {
    border-bottom: 1.5px solid #000;
    padding-bottom: 8pt;
    margin-bottom: 10pt;
    position: relative;
}
.header h1 {
    color: #000;
    font-size: 14pt;
    margin: 0 0 4pt 0;
}
.header .meta {
    font-size: 9pt;
    color: #333;
}
.stdcode-line {
    font-size: 11pt;
    font-weight: bold;
    white-space: nowrap;
    letter-spacing: 1pt;
}
.student-info {
    font-size: 10pt;
}
.student-info .name { font-weight: bold; font-size: 10.5pt; }
.question-block {
    margin-top: 14pt;
    page-break-inside: avoid;
}
.question-title {
    background: #d8d8d8;
    color: #000;
    padding: 3pt 6pt;
    font-weight: bold;
    font-size: 10pt;
    margin-bottom: 2pt;
    border: 1px solid #000;
}
.page-break-before {
    page-break-before: always;
}
.question-text {
    margin: 3pt 0;
}
.code-block {
    font-family: monospace;
    font-size: 8pt;
    background: #fff;
    border: 1px solid #000;
    padding: 3pt 5pt;
    margin: 2pt 0;
    white-space: pre-wrap;
    line-height: 1.1;
}
.footer {
    margin-top: 8pt;
    padding-top: 2pt;
    border-top: 1px solid #000;
    text-align: center;
    color: #000;
    font-size: 7.5pt;
}
.instructions {
    background: #fff;
    border: 1px solid #000;
    padding: 4pt 8pt;
    margin: 4pt 0 6pt 0;
    font-size: 8.5pt;
    line-height: 1.25;
}
.answer-note {
    font-size: 8pt;
    font-style: italic;
    margin: 2pt 0 6pt 0;
    color: #000;
}
"""


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


MAX_CODE_LINES = 15  # 2 sayfaya sığması için code_excerpt limiti


_FORCE_PAGE_BREAK = True  # caller override edebilir


def render_question_block(q: dict, include_key: bool) -> str:
    parts: list[str] = []
    # Q3 başlamadan önce sayfa kır — Q1+Q2 birinci sayfa, Q3+Q4 ikinci sayfa
    extra_class = " page-break-before" if (q.get("number") == 3 and _FORCE_PAGE_BREAK) else ""
    parts.append(f'<div class="question-block{extra_class}">')
    title = f"Question {q['number']} — {html_escape(q['title'])} ({q['points']} pts)"
    parts.append(f'<div class="question-title">{title}</div>')

    parts.append(f'<div class="question-text">{html_escape(q["text"]).replace(chr(10), "<br>")}</div>')

    if q.get("code_excerpt"):
        code = q["code_excerpt"]
        lines = code.split("\n")
        if len(lines) > MAX_CODE_LINES:
            code = "\n".join(lines[:MAX_CODE_LINES]) + f"\n... [+{len(lines) - MAX_CODE_LINES} more lines truncated]"
        parts.append(f'<div class="code-block">{html_escape(code)}</div>')

    parts.append("</div>")
    return "\n".join(parts)


def render_html(exam: dict, include_key: bool) -> str:
    qs = [render_question_block(q, include_key) for q in exam["questions"]]
    title = "ANSWER KEY (TA copy — do not distribute)" if include_key else "VISION EXAM"

    if include_key:
        stdcode_html = f'<span class="stdcode-line">REAL ID: {html_escape(exam["student_id"])}</span>'
    else:
        stdcode_html = '<span class="stdcode-line">STD_CODE: ____________</span>'

    instructions_html = "" if include_key else f"""
<div class="instructions">
<strong>Instructions:</strong> You will receive <strong>{len(exam["questions"])} lined answer sheets</strong>, each printed with a Student Code (top-left) and labeled <em>Question 1</em>…<em>Question {len(exam["questions"])}</em>. Write that <strong>STD_CODE</strong> in the box at the top-right of this page. Answer each question on the matching numbered sheet (use both sides if needed). Time: {exam.get("duration_minutes", 90)} minutes. These questions are about <strong>your own homework submission</strong> — answer based on what you implemented and reported.
</div>
"""

    pair_chunk = ('&nbsp;|&nbsp; <strong>Pair with:</strong> ' + ', '.join(exam.get('pair_partners', []))) if exam.get('is_pair') else ''

    return f"""<html>
<head>
<meta charset="utf-8">
<style>{CSS_COMMON}</style>
</head>
<body>
<table style="width:100%; border:none; border-collapse:collapse; margin-bottom:4pt;">
  <tr>
    <td style="border:none; vertical-align:top; padding:0;">
      <h1 style="color:#000; font-size:14pt; margin:0 0 4pt 0;">{COURSE_CODE} — {title}</h1>
    </td>
    <td style="border:none; vertical-align:top; text-align:right; padding:0 30pt 0 0; width:200pt;">
      {stdcode_html}
    </td>
  </tr>
</table>
<div class="student-info">
  Name: <span class="name">{html_escape(exam["student_name"])}</span>
  &nbsp;|&nbsp; ID: {html_escape(exam["student_id"])}
  {('&nbsp;|&nbsp; Homework: ' + html_escape(str(exam.get("homework_title", "")))) if exam.get("homework_title") else ''}
</div>
<div class="meta" style="margin-top:3pt;">
  <strong>Homework:</strong> HW{exam.get("homework", exam.get("part", 1))} &nbsp;|&nbsp;
  <strong>Duration:</strong> {exam.get("duration_minutes", 90)} min &nbsp;|&nbsp;
  <strong>Total:</strong> {exam["total_points"]} pts &nbsp;|&nbsp;
  <strong>Questions:</strong> {len(exam["questions"])}
  {pair_chunk}
</div>
<hr style="border:none; border-top:1.5px solid #000; margin:6pt 0 6pt 0;">

{instructions_html}

{chr(10).join(qs)}
</body>
</html>"""


def render_key_md(exam: dict) -> str:
    """AI/TA grading için kompakt markdown — exam.json'dan üretilir."""
    parts: list[str] = []
    parts.append(f"# Grading Key — {exam['student_id']} ({exam['student_name']})")
    parts.append("")
    pair_info = f" | **Pair with:** {', '.join(exam.get('pair_partners', []))}" if exam.get('is_pair') else ""
    hw = exam.get("homework", exam.get("part", 1))
    parts.append(f"**Course:** {COURSE_CODE} | **Homework:** HW{hw} | **Total:** {exam['total_points']} pts | **Questions:** {len(exam['questions'])}{pair_info}")
    parts.append("")
    parts.append("> AI grading: For each question, score the student's answer against the rubric below. Use partial credit per rubric line. Cite the specific rubric item when deducting points. The 'Expected answer' is a guide — do not penalise students for phrasing differences if the core idea matches. These questions probe whether the student genuinely understands their own submission, so reward concrete, submission-specific reasoning and penalise vague generic answers.")
    parts.append("")

    for q in exam["questions"]:
        parts.append(f"## Q{q['number']} — {q['title']} ({q['points']} pts)")
        parts.append("")
        parts.append(f"**Category:** {q.get('category', '—')} | **Reference:** {q.get('reference', q.get('sebesta_chapter', '—'))}")
        parts.append("")
        parts.append("**Question:**")
        parts.append("")
        parts.append(q["text"])
        parts.append("")
        if q.get("code_excerpt"):
            parts.append("**Code excerpt given in question:**")
            parts.append("```")
            parts.append(q["code_excerpt"])
            parts.append("```")
            parts.append("")
        parts.append("**Expected answer:**")
        parts.append("")
        parts.append(q["expected_answer"])
        parts.append("")
        if q.get("rubric"):
            parts.append("**Rubric:**")
            for r in q["rubric"]:
                parts.append(f"- {r}")
            parts.append("")
        parts.append("---")
        parts.append("")

    return "\n".join(parts)


def render_pdf(html: str, out_path: Path) -> int:
    mediabox = pymupdf.paper_rect("a4")
    margin = 20  # kompakt — 2 sayfaya sığması için
    where = pymupdf.Rect(margin, margin, mediabox.x1 - margin, mediabox.y1 - margin)
    writer = pymupdf.DocumentWriter(str(out_path))
    story = pymupdf.Story(html=html)
    more = 1
    page_count = 0
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev, where)
        writer.end_page()
        page_count += 1
    writer.close()
    return page_count


def main():
    parser = argparse.ArgumentParser(description="Per-student exam JSON → exam.pdf (student) + key.md (TA/AI)")
    parser.add_argument("--exam", "-e", type=Path, required=True, help="exam.json dosya yolu")
    parser.add_argument("--output-dir", "-o", type=Path, default=None,
                        help="Çıktıların yazılacağı klasör (varsayılan: exam.json ile aynı klasör)")
    parser.add_argument("--no-key", action="store_true", help="Sadece exam.pdf, key.md üretme")
    parser.add_argument("--no-page-break", action="store_true",
                        help="Q3 öncesi zorunlu sayfa kırmayı KAPAT (kompakt akış)")
    args = parser.parse_args()

    global _FORCE_PAGE_BREAK
    _FORCE_PAGE_BREAK = not args.no_page_break

    if not args.exam.exists():
        print(f"❌ exam.json bulunamadı: {args.exam}", file=sys.stderr)
        sys.exit(1)

    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    out_dir = args.output_dir or args.exam.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Soru sayısı validation
    if len(exam["questions"]) != 4:
        print(f"⚠ Uyarı: {args.exam.name} {len(exam['questions'])} soru içeriyor (beklenen: 4).", file=sys.stderr)

    # Student copy (no answers, blank STD_CODE)
    html_student = render_html(exam, include_key=False)
    student_pdf = out_dir / "exam.pdf"
    p_student = render_pdf(html_student, student_pdf)
    print(f"✓ exam.pdf ({p_student} sayfa) → {student_pdf}")

    # TA/AI grading key (markdown — token-friendly)
    if not args.no_key:
        key_md = out_dir / "key.md"
        key_md.write_text(render_key_md(exam), encoding="utf-8")
        size_kb = key_md.stat().st_size / 1024
        print(f"✓ key.md ({size_kb:.1f} KB) → {key_md}")

    # Eski key.pdf varsa sil
    old_key_pdf = out_dir / "key.pdf"
    if old_key_pdf.exists():
        old_key_pdf.unlink()


if __name__ == "__main__":
    main()
