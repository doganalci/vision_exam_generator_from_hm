---
description: Bir ödevin tüm öğrencileri için bulk kişiselleştirilmiş sınav üret (paralel subagent)
argument-hint: <hw-number> [--batch-size N]
---

# /generate-all-exams $1

HW`$1`'in tüm öğrencileri için sınav üret. **Subagent'lar paralel çalıştırılır** — her subagent bir batch öğrenci işler.

## Strateji
- Tüm bundle'ları önce hazırla (Python amele, hızlı)
- Öğrencileri **5-8'lik batch**'lere böl
- Her batch için bir `general-purpose` subagent (Opus, thinking) çağır, paralel
- Her subagent batch'indeki her öğrenciye `exam.json` üretir + render eder

## Adımlar

1. `$1` = ödev no. Batch size varsayılan `6`.

2. Tüm bundle'ları hazırla:
   ```bash
   python tools/prepare_exam_inputs.py --submissions data/hw$1/submissions --hw $1
   ```

3. Öğrenci listesini al: `data/hw$1/submissions/_index.json` oku, ID listesini çek.

4. Batch'lere böl.

5. **Tek mesajda birden çok subagent çağır** (paralel). Subagent prompt şablonu:
   ```
   Generate personalized CSE 463 Computer Vision exams for these students:
   - Student IDs: {batch_ids}
   - Homework: {hw}
   - Repo root: {repo_root}

   For EACH student:
   1. Read data/hw{hw}/submissions/{id}/_exam_input.md (Read informative result-image
      thumbnails it lists before writing questions).
   2. Follow templates/exam/exam-prompt.md EXACTLY: 4 questions, 25 pts each, 100 total,
      2 submission-specific + 2 general-cv, each with expected_answer + rubric (sum 25).
   3. Write data/hw{hw}/exams/{id}/exam.json (schema: templates/exam/exam-schema.json; mkdir if needed).
   4. Render: python tools/render_exam_pdf.py --exam data/hw{hw}/exams/{id}/exam.json

   Quality bar: every submission-specific question must reference the student's OWN
   parameters/code/results by name — never a generic textbook definition. The goal is to
   test whether they truly understand their own submission.

   Report per student: ID, total_points, num_questions, exam_pdf_pages, any errors.
   ```

6. **Sonuçları topla:** üretilen sınav sayısı, hatalı öğrenciler (rapor/kod eksik), her
   öğrenci için `exam.pdf` + `key.md` var mı doğrula.

## Rate-limit uyarısı
- Tek seferde tüm batch'leri paralel çağırma — 5-6'şar batch'le ilerle.
- Kalite düşükse: batch size'ı 4'e indir veya `/generate-exam` ile tek tek üret.

## Çıktı
```
data/hw$1/exams/
├── 220104004061/
│   ├── exam.json
│   ├── exam.pdf   (öğrenci kopyası)
│   └── key.md     (TA/AI grading key)
└── ...
```
