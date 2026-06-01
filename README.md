# vision_exam_generator_from_hm

**CSE 463 (Computer Vision, GTU) — per-student exam generator.**

Öğrencilerin Computer Vision ödevlerini (rapor + kod + sonuç görselleri) okur ve **her
öğrenciye özel bir sınav** üretir. Amaç ödevi notlandırmak değil; öğrencinin teslim ettiği
işi **gerçekten anlayıp anlamadığını** sınamak — birçok öğrenci ödevi LLM ile yaptığı için
sorular, kişinin kendi raporuna/koduna/sonuçlarına atıfta bulunur ve ezbere/kopyala-yapıştır
cevapla geçilemez.

Format: **4 soru × 25 puan = 100 puan, 90 dakika** (2 soru öğrencinin kendi teslimine özel +
2 soru ilgili genel CV kavramları). Sorular İngilizce, TA notları Türkçe.

## Hızlı başlangıç

```bash
pip install -r requirements.txt

# 1) Ödevleri işle (her alt klasör = bir öğrenci)
python tools/ingest_submissions.py --input <ham-klasör> --hw 1 \
    --output data/hw1/submissions --extract-zips

# 2) Sınav girdisi bundle'larını hazırla (rapor+kod+görsel ön-işleme)
python tools/prepare_exam_inputs.py --submissions data/hw1/submissions --hw 1

# 3) Sınav üret — Claude Code içinde (kalite kritik):
#    /generate-exam 1 <id>          (tek öğrenci, tam kalite)
#    /generate-all-exams 1          (tüm öğrenciler, paralel subagent)

# 4) (opsiyonel) Cevap kağıtları
python tools/render_answer_sheets.py --codes 100,102,104 --output data/hw1/answer-sheets

# 5) Durum panosu
streamlit run web/app.py
```

## Kod / veri ayrımı

Kod git'te; **dinamik veri `data/` altında ve gitignore'lu**. Repoyu bir klasöre `pull`
edip ödevleri `data/` altına koyarsınız — büyük teslim dosyaları ve üretilen PDF'ler push
edilmez, pull/push çakışmaz.

## Slash komutları

| Komut | Açıklama |
|-------|----------|
| `/ingest <hw> <klasör>` | Öğrenci klasörlerini işle, envanter çıkar |
| `/prepare-inputs <hw> [id]` | Sınav girdisi bundle'larını hazırla |
| `/generate-exam <hw> <id>` | Tek öğrenci için sınav üret (sen, Opus + thinking) |
| `/generate-all-exams <hw>` | Tüm öğrenciler için paralel sınav üret |

Mimari ve detaylar: [CLAUDE.md](CLAUDE.md). Soru kalite sözleşmesi:
[templates/exam/exam-prompt.md](templates/exam/exam-prompt.md).
