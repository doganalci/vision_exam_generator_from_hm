---
description: Tek bir öğrenci için kişiselleştirilmiş CV sınavı üret (raporu + koduna dayalı)
argument-hint: <hw-number> <student_id>
---

# /generate-exam $1 $2

Öğrenci `$2` için HW`$1` kişiselleştirilmiş Computer Vision sınavı üret.
**En yüksek modelde (Opus, thinking açık) SEN kendin yap** — bu kritik kalite işi, subagent değil.

## Adımlar

1. Argümanları parse et: `$1` = ödev no, `$2` = öğrenci ID.

2. Path kontrolü:
   - `data/hw$1/submissions/$2/_info.json` var mı? Yoksa önce `/ingest` çalıştır.
   - `data/hw$1/submissions/$2/_exam_input.md` var mı? Yoksa önce hazırla:
     ```bash
     python tools/prepare_exam_inputs.py --submissions data/hw$1/submissions --hw $1 --only $2
     ```

3. **Bundle'ı oku** (`_exam_input.md`). Görsel thumbnail'ları listeleniyorsa, en bilgilendirici
   olanları **Read ile gör** — sorular öğrencinin gerçek sonuçlarına atıfta bulunmalı.

4. **`templates/exam/exam-prompt.md`'i talimat olarak takip et** — özet:
   - TAM 4 soru, her biri 25pt, toplam 100pt, 90 dk
   - 2 soru `submission-specific` (öğrencinin kendi rapor/kod/sonucuna dayalı — kendi
     parametre/değişken/sonuç adlarına atıfla)
   - 2 soru `general-cv` (ödevin dokunduğu standart CV kavramları)
   - Her sorunun `expected_answer` + rubric'i (toplamı 25) olmalı

5. **`exam.json` yaz:** `data/hw$1/exams/$2/exam.json` (schema: `templates/exam/exam-schema.json`)

6. **PDF render et:**
   ```bash
   python tools/render_exam_pdf.py --exam data/hw$1/exams/$2/exam.json
   ```
   - Çıktı: `exam.pdf` (öğrenci) + `key.md` (TA/AI grading)

7. **Kullanıcıya rapor:** soru sayısı, kategori dağılımı, toplam puan, exam.pdf sayfa sayısı, path'ler.

## Kalite kontrolü (üretirken KENDİN sorgula)
- ❌ "Convolution nedir?" gibi generic tanım sorusu yok
- ✓ Her submission-specific soru öğrencinin ÖZGÜN seçimine atıf (kendi kernel size'ı, eşik
  değeri, renk uzayı, katman, loss fonksiyonu, kendi kod parçası veya sonuç görseli)
- ✓ Trade-off / alternatif / "neden X değil Y" / hata analizi sorularını tercih et
- ✓ Rapor ile kod arasında tutarsızlık fark ettin mi → onu test eden soru sor
- ✓ En az bir soruda öğrencinin kendi kodundan `code_excerpt` veya bir sonuç görseline atıf
