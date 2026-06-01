# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## What this repository is

**CSE 463 (Computer Vision, Gebze Technical University) — per-student exam generator.**

Students submit Computer Vision homeworks (report + code + result images). Many produced
them with the help of LLMs. The goal of this tool is **not** to grade the homework — it is
to generate a **personalized exam per student** that tests whether they *actually
understand* the work they handed in. Each student gets 4 questions tied to their own
report, code, and results, plus general CV questions on the concepts their homework uses.

This is adapted from a sibling CSE 341 (Concepts of Programming Languages) TA workspace:
the exam JSON schema, render pipeline, and 4×25=100pt format are the same; the domain
(PL → Computer Vision) and the ingestion (Teams D1–D6 zip → folder-per-student) differ.

## Code vs data separation (load-bearing)

**Code lives in git; dynamic data does NOT.** You clone this repo into a folder and drop
homework data under `data/`. `.gitignore` excludes everything under `data/` except the
structure stub, so `git pull`/`push` never conflicts with large submission files or
generated PDFs.

```
vision_exam_generator_from_hm/
├── tools/                       # Python CLI tools (year/hw-agnostic)
│   ├── ingest_submissions.py    # folder-per-student → inventoried _info.json
│   ├── prepare_exam_inputs.py   # report+code+images → _exam_input.md bundle (+thumbnails)
│   ├── render_exam_pdf.py       # exam.json → exam.pdf (student) + key.md (TA/AI)
│   └── render_answer_sheets.py  # lined answer-sheet packets per std_code
├── templates/exam/
│   ├── exam-prompt.md           # question-generation instructions (the quality contract)
│   └── exam-schema.json         # exam.json JSON schema
├── .claude/commands/            # slash commands (workflow shortcuts)
├── web/app.py                   # thin Streamlit dashboard (status + downloads, read-only)
├── requirements.txt
└── data/                        # GITIGNORED dynamic data
    └── hw1/, hw2/, ...
        ├── submissions/<id>/    # _info.json, _exam_input.md, _processed/images/
        │   └── _index.json
        ├── exams/<id>/          # exam.json, exam.pdf, key.md
        └── answer-sheets/       # answer_sheets_<code>.pdf
```

## End-to-end workflow

1. **Ingest** — drop raw submissions in a folder (each subfolder = one student), then:
   ```bash
   python tools/ingest_submissions.py --input <raw-folder> --hw 1 \
       --output data/hw1/submissions --extract-zips
   ```
   Or `/ingest 1 <raw-folder>`. Produces `_info.json` per student + `_index.json`.

2. **Prepare inputs** — build the per-student bundle (PDF/DOCX text, code, image thumbnails):
   ```bash
   python tools/prepare_exam_inputs.py --submissions data/hw1/submissions --hw 1
   ```
   Or `/prepare-inputs 1`. Produces `_exam_input.md` + `_processed/images/*.jpg`.

3. **Generate exams** — this is the quality-critical step, done by Claude (not a script):
   - One student, full quality: `/generate-exam 1 <id>` (you, Opus + thinking).
   - All students, parallel: `/generate-all-exams 1` (batched subagents).
   - Each writes `exam.json` then renders `exam.pdf` + `key.md`.

4. **(Optional) answer sheets** — anonymized lined sheets for the exam session:
   ```bash
   python tools/render_answer_sheets.py --codes 100,102,104 --output data/hw1/answer-sheets
   ```

5. **Dashboard** — `streamlit run web/app.py` to see status and download outputs.

## Exam format (fixed — schema enforces it)

- **EXACTLY 4 questions, 25 pts each, 100 pts total, 90 minutes.**
- **2 `submission-specific`** + **2 `general-cv`** questions.
- Questions in **English**; TA-facing notes/code comments may be **Turkish**.
- `exam.pdf` = student copy (black-and-white, blank `STD_CODE` box top-right, no answer
  boxes — answers go on separate lined sheets). `key.md` = TA/AI grading key (markdown,
  token-friendly, **never** distributed). No `key.pdf` is produced.

The whole point is **anti-LLM-bluff**: submission-specific questions must reference the
student's OWN parameters/variables/results by name. A generic textbook definition must
never earn full marks. See `templates/exam/exam-prompt.md` for the full quality contract —
**read it before generating any exam.**

## Ingestion details that aren't obvious

- **Each immediate subfolder of `--input` is one student.** Student ID is taken from a
  6–12 digit number in the folder name if present (`--id-from regex`, default), else the
  sanitized folder name (`--id-from folder`).
- Files are classified by extension into `report` (pdf/docx/md/txt), `code`
  (py/ipynb/cpp/m/...), `image`, `data` (npy/pt/h5/zip/onnx/weights...), `other`.
- **Large files (>5 MB) are inventoried but never read** into bundles — saves tokens. Data
  and model files are listed by name/size only.
- `--extract-zips` extracts code zips in-place (`_extracted_<name>/`, with zip-slip
  guard) so their `.py` files get inventoried.
- Bundles cap report text at ~25k chars, pick the ~8 most relevant code files (shallow
  depth + meaningful names like `main`/`model`/`detect`/`segment`), and parse `.ipynb`
  cells (code + markdown + truncated outputs).
- Result images are **downscaled to ≤1024px thumbnails** and sampled (default 6, evenly
  spaced) into `_processed/images/`. The bundle lists their paths; when generating an exam,
  **Read the informative thumbnails** so questions can reference what the results show.

## Reference / further notes

- Python 3.11. Deps: `pymupdf`, `pillow`, `python-docx`, `streamlit` (see
  `requirements.txt`). `python-docx` and `pillow` have graceful fallbacks if missing.
- The web dashboard is intentionally **read-only** — it never calls the LLM. Generation
  stays in Claude Code for cost/quality control (large submissions hit limits in the
  hosted UI; run locally per the CSE 341 lesson).
- When changing the exam format, update **all three**: `exam-schema.json`,
  `render_exam_pdf.py` (validation + layout), and `exam-prompt.md` (instructions).
