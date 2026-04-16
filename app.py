from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
INDEX_XLSX = BASE_DIR / "index.xlsx"
INDEX_CSV = BASE_DIR / "index.csv"
PDF_BASE = BASE_DIR / "pdfs"
PROGRESS_FILE = BASE_DIR / "progress_web.json"

FILTER_ALL = "全部"

app = Flask(__name__)

def load_index():
    if INDEX_XLSX.exists():
        df = pd.read_excel(INDEX_XLSX)
    elif INDEX_CSV.exists():
        df = pd.read_csv(INDEX_CSV)
    else:
        raise FileNotFoundError("请把 index.xlsx 或 index.csv 放到 web_v2 目录下。")

    required = [
        "id", "subject", "chapter", "topic", "year",
        "question_pdf", "question_page",
        "answer_pdf", "answer_page",
        "syllabus_pdf", "syllabus_page",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"索引缺少字段: {', '.join(missing)}")

    optional_defaults = {
        "title": "",
        "source": "",
        "order": 999999,
        "question_end_page": pd.NA,
        "answer_end_page": pd.NA,
        "syllabus_end_page": pd.NA,
    }
    for col, default in optional_defaults.items():
        if col not in df.columns:
            df[col] = default

    text_cols = [
        "id", "subject", "chapter", "topic", "year",
        "question_pdf", "answer_pdf", "syllabus_pdf",
        "title", "source"
    ]
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in [
        "question_page", "answer_page", "syllabus_page",
        "question_end_page", "answer_end_page", "syllabus_end_page", "order"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["subject", "chapter", "topic", "year", "order", "id"]).reset_index(drop=True)

def load_progress():
    if not PROGRESS_FILE.exists():
        return {}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_progress(data):
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_progress_record(progress, qid):
    item = progress.get(qid, {})
    return {
        "done": bool(item.get("done", False)),
        "favorite": bool(item.get("favorite", False)),
        "note": str(item.get("note", "")),
    }

def merge_record(row, progress):
    record = row.to_dict()
    record.update(get_progress_record(progress, record["id"]))
    return record

def unique_values(df, col):
    vals = sorted(v for v in df[col].dropna().astype(str).str.strip().unique().tolist() if v != "")
    return [FILTER_ALL] + vals

@app.route("/")
def index():
    all_df = load_index()
    progress = load_progress()

    subject = request.args.get("subject", FILTER_ALL)
    chapter = request.args.get("chapter", FILTER_ALL)
    topic = request.args.get("topic", FILTER_ALL)
    year = request.args.get("year", FILTER_ALL)
    mode = request.args.get("mode", "question")
    selected_id = request.args.get("selected_id", "")

    only_unfinished = request.args.get("only_unfinished", "") == "1"
    only_favorite = request.args.get("only_favorite", "") == "1"

    df = all_df.copy()

    if subject != FILTER_ALL:
        df = df[df["subject"] == subject]
    chapter_options_df = df.copy()

    if chapter != FILTER_ALL:
        df = df[df["chapter"] == chapter]
    topic_options_df = df.copy()

    if topic != FILTER_ALL:
        df = df[df["topic"] == topic]
    year_options_df = df.copy()

    if year != FILTER_ALL:
        df = df[df["year"] == year]

    records = [merge_record(row, progress) for _, row in df.iterrows()]
    if only_unfinished:
        records = [r for r in records if not r["done"]]
    if only_favorite:
        records = [r for r in records if r["favorite"]]

    if records and not selected_id:
        selected_id = records[0]["id"]
    selected = next((r for r in records if r["id"] == selected_id), records[0] if records else None)

    pdf_url = None
    pdf_page = None
    if selected:
        field_map = {
            "question": ("question_pdf", "question_page"),
            "answer": ("answer_pdf", "answer_page"),
            "syllabus": ("syllabus_pdf", "syllabus_page"),
        }
        pdf_col, page_col = field_map.get(mode, ("question_pdf", "question_page"))
        pdf_url = url_for("serve_pdf", filename=selected[pdf_col])
        pdf_page = int(selected[page_col])

    return render_template(
        "index.html",
        records=records,
        selected=selected,
        pdf_url=pdf_url,
        pdf_page=pdf_page,
        mode=mode,
        filter_all=FILTER_ALL,
        subject=subject,
        chapter=chapter,
        topic=topic,
        year=year,
        only_unfinished=only_unfinished,
        only_favorite=only_favorite,
        subjects=unique_values(all_df, "subject"),
        chapters=unique_values(chapter_options_df, "chapter"),
        topics=unique_values(topic_options_df, "topic"),
        years=unique_values(year_options_df, "year"),
    )

@app.route("/pdfs/<path:filename>")
def serve_pdf(filename):
    return send_from_directory(PDF_BASE, filename)

@app.post("/toggle/<qid>/<field>")
def toggle(qid, field):
    if field not in {"done", "favorite"}:
        return jsonify({"ok": False, "error": "invalid field"}), 400
    progress = load_progress()
    item = progress.setdefault(qid, {})
    item[field] = not bool(item.get(field, False))
    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_progress(progress)
    return jsonify({"ok": True, field: item[field]})

@app.post("/note/<qid>")
def save_note_route(qid):
    progress = load_progress()
    item = progress.setdefault(qid, {})
    item["note"] = request.form.get("note", "")
    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_progress(progress)
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(debug=True,use_reloader=False, port=8000)
