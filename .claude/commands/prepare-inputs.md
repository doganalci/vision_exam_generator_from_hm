---
description: Her öğrenci için sınav girdisi bundle'ı (_exam_input.md) hazırla — rapor + kod + görsel ön-işleme
argument-hint: <hw-number> [student-id]
---

# /prepare-inputs $1

Her öğrencinin rapor + kod + sonuç görsellerini tek bir `_exam_input.md` bundle'ında topla.
Bu bundle sınav üretiminde kullanılır.

## Adımlar

1. `$1` = ödev numarası. `$2` = (opsiyonel) tek öğrenci ID.

2. Script'i çalıştır:
   ```bash
   # Tüm öğrenciler:
   python tools/prepare_exam_inputs.py --submissions data/hw$1/submissions --hw $1
   # Tek öğrenci:
   python tools/prepare_exam_inputs.py --submissions data/hw$1/submissions --hw $1 --only $2
   ```

3. Her öğrenci için üretilenler:
   - `_exam_input.md` — PDF/DOCX rapor metni, kod (.py/.ipynb hücreleri), örneklenmiş görsel listesi
   - `_processed/images/*.jpg` — küçültülmüş thumbnail'lar (sınav üretirken Read edilebilir)

4. Kullanıcıya kaç bundle yazıldığını ve ortalama boyutlarını raporla.

## Notlar
- Büyük data/model dosyaları okunmaz, sadece listelenir.
- Görseller `--max-images N` ile ayarlanır (varsayılan 6).
- Sonraki adım: `/generate-exam <id>` veya `/generate-all-exams`.
