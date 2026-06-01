"""
CSE 463 Vision Exam Generator — thin web dashboard.
===================================================
CLI/slash-command workflow asıl motordur; bu Streamlit katmanı sadece durumu
görselleştirir ve çıktıları indirilebilir kılar. Soru üretimi Claude Code ile yapılır
(token/kalite), bu arayüz onu tetiklemez — sadece data/ klasörünü okur.

Çalıştırma:
    pip install -r requirements.txt
    streamlit run web/app.py

Gösterdikleri (data/hw{N}/ altından okunur):
- Öğrenci listesi + durum (ingested / bundle ready / exam generated)
- Her öğrenci için: dosya envanteri, exam.pdf indirme, key.md görüntüleme
- Özet istatistikler ve uyarılar
"""
import json
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def list_homeworks() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted([d.name for d in DATA_DIR.iterdir()
                   if d.is_dir() and d.name.lower().startswith("hw")])


def load_index(hw: str) -> dict | None:
    p = DATA_DIR / hw / "submissions" / "_index.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def student_status(hw: str, sid: str) -> dict:
    sub = DATA_DIR / hw / "submissions" / sid
    exam_dir = DATA_DIR / hw / "exams" / sid
    return {
        "ingested": (sub / "_info.json").exists(),
        "bundle": (sub / "_exam_input.md").exists(),
        "exam_json": (exam_dir / "exam.json").exists(),
        "exam_pdf": (exam_dir / "exam.pdf").exists(),
        "key_md": (exam_dir / "key.md").exists(),
    }


def main():
    st.set_page_config(page_title="CSE 463 Vision Exam Generator", layout="wide")
    st.title("🧪 CSE 463 — Per-Student Vision Exam Generator")
    st.caption("Öğrencilerin ödevini okur, kişiselleştirilmiş sınav üretir — "
               "\"LLM ile yaptı ama anladı mı?\" testi. Soru üretimi Claude Code ile, "
               "bu panel sadece durumu/çıktıları gösterir.")

    homeworks = list_homeworks()
    if not homeworks:
        st.warning("Henüz ödev verisi yok. Önce `/ingest <hw> <klasör>` çalıştırın "
                   "(veya `python tools/ingest_submissions.py ...`).")
        st.code("python tools/ingest_submissions.py --input <klasör> --hw 1 "
                "--output data/hw1/submissions --extract-zips")
        return

    hw = st.sidebar.selectbox("Ödev", homeworks)
    index = load_index(hw)
    if not index:
        st.error(f"{hw}/submissions/_index.json bulunamadı — ingest çalıştırılmamış.")
        return

    students = index.get("students", [])
    # --- özet ---
    rows = []
    n_exam = 0
    n_bundle = 0
    n_warn = 0
    for s in students:
        sid = s["id"]
        stt = student_status(hw, sid)
        if stt["exam_pdf"]:
            n_exam += 1
        if stt["bundle"]:
            n_bundle += 1
        if s.get("warnings"):
            n_warn += 1
        rows.append({
            "ID": sid,
            "Report": s["counts"].get("report", 0),
            "Code": s["counts"].get("code", 0),
            "Images": s["counts"].get("image", 0),
            "Size (MB)": s.get("total_mb", 0),
            "Bundle": "✅" if stt["bundle"] else "—",
            "Exam": "✅" if stt["exam_pdf"] else "—",
            "Warnings": ", ".join(s.get("warnings", [])),
        })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Öğrenci", len(students))
    c2.metric("Bundle hazır", n_bundle)
    c3.metric("Sınav üretildi", n_exam)
    c4.metric("Uyarılı", n_warn)

    st.subheader("Öğrenciler")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- öğrenci detay ---
    st.subheader("Öğrenci detayı")
    sid = st.selectbox("Öğrenci seç", [s["id"] for s in students])
    if not sid:
        return
    stt = student_status(hw, sid)
    sub = DATA_DIR / hw / "submissions" / sid
    exam_dir = DATA_DIR / hw / "exams" / sid

    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Durum**")
        st.json(stt)
        info_p = sub / "_info.json"
        if info_p.exists():
            with st.expander("Dosya envanteri (_info.json)"):
                st.json(json.loads(info_p.read_text(encoding="utf-8")))

    with cols[1]:
        st.markdown("**Çıktılar**")
        pdf_p = exam_dir / "exam.pdf"
        if pdf_p.exists():
            st.download_button("📄 exam.pdf indir", pdf_p.read_bytes(),
                               file_name=f"{sid}_exam.pdf", mime="application/pdf")
        key_p = exam_dir / "key.md"
        if key_p.exists():
            with st.expander("🔑 key.md (TA/AI grading)"):
                st.markdown(key_p.read_text(encoding="utf-8"))
        json_p = exam_dir / "exam.json"
        if json_p.exists():
            with st.expander("exam.json"):
                st.json(json.loads(json_p.read_text(encoding="utf-8")))
        if not pdf_p.exists():
            st.info("Bu öğrenci için sınav henüz üretilmedi. Claude Code'da:\n\n"
                    f"`/generate-exam {hw.replace('hw','')} {sid}`")


if __name__ == "__main__":
    main()
