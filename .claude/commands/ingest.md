---
description: Bir klasördeki öğrenci ödevlerini (her alt klasör bir öğrenci) işle ve envanterini çıkar
argument-hint: <hw-number> <input-folder>
---

# /ingest $1 $2

CSE 463 ödev teslimini işle. Girdi: içinde **her alt klasörü bir öğrenci** olan bir kök klasör.

## Adımlar

1. Argümanları parse et:
   - `$1` = ödev numarası (1, 2, ...)
   - `$2` = girdi kök klasörü (her alt klasör = bir öğrenci)

2. Script'i çalıştır:
   ```bash
   python tools/ingest_submissions.py \
       --input "$2" \
       --hw $1 \
       --output data/hw$1/submissions \
       --extract-zips
   ```
   - Her öğrenci için `data/hw$1/submissions/<id>/_info.json` (dosya envanteri)
   - `data/hw$1/submissions/_index.json` (tüm liste)

3. Çıktıdan kullanıcıya rapor:
   - Toplam öğrenci sayısı
   - Uyarılı öğrenciler (rapor veya kod bulunamayan)
   - Dosya türü dağılımı (report / code / image / data)

## Notlar
- Büyük dosyalar (>5 MB) kopyalanmaz; sadece referans path saklanır (token tasarrufu).
- Öğrenci ID'si klasör adındaki numaradan (varsa) yoksa klasör adından türetilir.
- Sonraki adım: `/prepare-inputs $1` ile sınav girdisi bundle'larını hazırla.
