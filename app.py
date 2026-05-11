from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    session,
    flash,
)
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, timedelta
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
import random
import smtplib
from email.message import EmailMessage
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent
INDEX_XLSX = BASE_DIR / "index.xlsx"
INDEX_CSV = BASE_DIR / "index.csv"
PDF_BASE = BASE_DIR / "pdfs"
PROGRESS_FILE = BASE_DIR / "progress_web.json"
DB_FILE = BASE_DIR / "app.db"
SLIDES_DIR = BASE_DIR / "static" / "learn" / "slides"
FILES_DIR = BASE_DIR / "static" / "learn" / "files"
ANIMATIONS_DIR = BASE_DIR / "static" / "learn" / "animations"
CONTENT_DIR = BASE_DIR / "content"

FILTER_ALL = "全部"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

LANG_ZH = "zh"
LANG_EN = "en"
SUPPORTED_LANGS = {LANG_ZH, LANG_EN}


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            birth_date TEXT NOT NULL DEFAULT '',
            school TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    migration_columns = {
        "birth_date": "ALTER TABLE users ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''",
        "school": "ALTER TABLE users ADD COLUMN school TEXT NOT NULL DEFAULT ''",
        "email": "ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migration_columns.items():
        if column not in existing_columns:
            conn.execute(sql)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            game_name TEXT NOT NULL,
            difficulty TEXT NOT NULL DEFAULT 'normal',
            score INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    migration_columns = {
        "birth_date": "ALTER TABLE users ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''",
        "school": "ALTER TABLE users ADD COLUMN school TEXT NOT NULL DEFAULT ''",
        "email": "ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migration_columns.items():
        if column not in existing_columns:
            conn.execute(sql)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            game_name TEXT NOT NULL,
            difficulty TEXT NOT NULL DEFAULT 'normal',
            score INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    migration_columns = {
        "birth_date": "ALTER TABLE users ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''",
        "school": "ALTER TABLE users ADD COLUMN school TEXT NOT NULL DEFAULT ''",
        "email": "ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migration_columns.items():
        if column not in existing_columns:
            conn.execute(sql)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            game_name TEXT NOT NULL,
            difficulty TEXT NOT NULL DEFAULT 'normal',
            score INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    migration_columns = {
        "birth_date": "ALTER TABLE users ADD COLUMN birth_date TEXT NOT NULL DEFAULT ''",
        "school": "ALTER TABLE users ADD COLUMN school TEXT NOT NULL DEFAULT ''",
        "email": "ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''",
    }
    for column, sql in migration_columns.items():
        if column not in existing_columns:
            conn.execute(sql)

    score_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(game_scores)").fetchall()
    }
    if "difficulty" not in score_columns:
        conn.execute(
            "ALTER TABLE game_scores ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'normal'"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incense_daily (
            day TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS internal_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            sender_username TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    message_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(internal_messages)").fetchall()
    }
    if "is_read" not in message_columns:
        conn.execute(
            "ALTER TABLE internal_messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
    conn.close()



_db_inited = False


@app.before_request
def ensure_db_initialized():
    global _db_inited
    if not _db_inited:
        init_db()
        _db_inited = True

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            next_path = request.full_path if request.query_string else request.path
            return redirect(url_for("login", next=next_path, lang=get_lang()))
        return view_func(*args, **kwargs)

    return wrapped


def normalize_next_url(next_url: str):
    if not next_url:
        return None
    parts = urlsplit(next_url)
    if parts.scheme or parts.netloc:
        return None
    if not parts.path.startswith("/"):
        return None
    return next_url


def current_username():
    return session.get("username", "")


def list_files_with_suffix(directory: Path, suffix: str):
    if not directory.exists():
        return []
    items = []
    rel_dir = directory.relative_to(BASE_DIR / "static").as_posix()
    for path in sorted(directory.glob(f"*{suffix}"), key=lambda p: p.name.lower()):
        items.append({"name": path.name, "url": url_for("static", filename=f"{rel_dir}/{path.name}")})
    return items


def list_chapter_files(directory: Path, suffix: str):
    if not directory.exists():
        return {}
    rel_root = directory.relative_to(BASE_DIR / "static").as_posix()
    grouped = {}
    for sub in sorted([p for p in directory.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        files = []
        for path in sorted(sub.glob(f"*{suffix}"), key=lambda p: p.name.lower()):
            files.append(
                {
                    "name": path.name,
                    "url": url_for("static", filename=f"{rel_root}/{sub.name}/{path.name}"),
                }
            )
        if files:
            grouped[sub.name] = files
    root_files = []
    for path in sorted(directory.glob(f"*{suffix}"), key=lambda p: p.name.lower()):
        root_files.append({"name": path.name, "url": url_for("static", filename=f"{rel_root}/{path.name}")})
    if root_files:
        grouped["未分章"] = root_files
    return grouped


def load_section_items(filename: str):
    path = CONTENT_DIR / filename
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    items = []
    for row in data:
        if not isinstance(row, dict):
            continue
        items.append(
            {
                "title": str(row.get("title", "")).strip(),
                "summary": str(row.get("summary", "")).strip(),
                "date": str(row.get("date", "")).strip(),
                "link": str(row.get("link", "")).strip(),
                "image": str(row.get("image", "")).strip(),
                "content": str(row.get("content", "")).strip(),
            }
        )
    return [it for it in items if it["title"]]


def has_unread_messages(username: str):
    if not username:
        return False
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT 1
        FROM internal_messages
        WHERE receiver_username = ? AND is_read = 0
        LIMIT 1
        """,
        (username,),
    ).fetchone()
    conn.close()
    return bool(row)


def get_lang():
    query_lang = request.args.get("lang", "").strip().lower()
    if query_lang in SUPPORTED_LANGS:
        session["lang"] = query_lang
        return query_lang
    return session.get("lang", LANG_ZH)


def is_en():
    return get_lang() == LANG_EN


SUPPORTED_GAMES = {
    "2048",
    "tetris",
    "nonogram",
    "sudoku",
    "minesweeper",
    "hanoi",
}
# 兼容旧代码分支中对难度变量的引用，当前版本仅使用 normal。
SUPPORTED_DIFFICULTIES = {"normal"}
TIME_RANK_GAMES = {"sudoku", "nonogram", "minesweeper", "hanoi"}



def load_index():
    if INDEX_XLSX.exists():
        df = pd.read_excel(INDEX_XLSX)
    elif INDEX_CSV.exists():
        df = pd.read_csv(INDEX_CSV)
    else:
        raise FileNotFoundError("请把 index.xlsx 或 index.csv 放到 web_v2 目录下。")

    required = [
        "id",
        "subject",
        "chapter",
        "topic",
        "year",
        "question_pdf",
        "question_page",
        "answer_pdf",
        "answer_page",
        "syllabus_pdf",
        "syllabus_page",
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
        "id",
        "subject",
        "chapter",
        "topic",
        "year",
        "question_pdf",
        "answer_pdf",
        "syllabus_pdf",
        "title",
        "source",
    ]
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in [
        "question_page",
        "answer_page",
        "syllabus_page",
        "question_end_page",
        "answer_end_page",
        "syllabus_end_page",
        "order",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["subject", "chapter", "topic", "year", "order", "id"]).reset_index(
        drop=True
    )


def load_progress_root():
    if not PROGRESS_FILE.exists():
        return {}
    try:
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_progress_root(data):
    PROGRESS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_progress(username):
    root = load_progress_root()
    if username in root and isinstance(root.get(username), dict):
        return root[username]

    # 兼容旧格式：顶层直接是 qid -> {...}
    legacy_like = all(isinstance(v, dict) and ("done" in v or "favorite" in v or "note" in v) for v in root.values())
    if legacy_like and root:
        root = {username: root}
        save_progress_root(root)
        return root[username]

    return {}


def save_progress(username, user_data):
    root = load_progress_root()
    root[username] = user_data
    save_progress_root(root)


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
    vals = sorted(
        v for v in df[col].dropna().astype(str).str.strip().unique().tolist() if v != ""
    )
    return [FILTER_ALL] + vals


def selected_filter_values(name):
    values = list(
        dict.fromkeys(v.strip() for v in request.args.getlist(name) if v.strip())
    )
    if not values:
        return [FILTER_ALL]
    return values


def apply_multi_filter(df, col, values):
    if FILTER_ALL in values:
        return df
    return df[df[col].isin(values)]


@app.route("/register", methods=["GET", "POST"])
def register():
    lang = get_lang()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        birth_date = request.form.get("birth_date", "").strip()
        school = request.form.get("school", "").strip()
        email = request.form.get("email", "").strip()

        if not username or not password or not birth_date or not school or not email:
            flash(
                "Please complete all required fields."
                if is_en()
                else "请完整填写所有必填信息。"
            )
            return render_template("register.html", lang=lang)

        conn = get_db_connection()
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            conn.close()
            flash("Username already exists. Please choose another one." if is_en() else "用户名已存在，请换一个。")
            return render_template("register.html", lang=lang)

        conn.execute(
            """
            INSERT INTO users (username, password_hash, birth_date, school, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                generate_password_hash(password),
                birth_date,
                school,
                email,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        conn.close()
        flash("Registration successful. Please log in." if is_en() else "注册成功，请登录。")
        return redirect(url_for("login", lang=lang))

    return render_template("register.html", lang=lang)


@app.route("/login", methods=["GET", "POST"])
def login():
    lang = get_lang()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password." if is_en() else "用户名或密码错误。")
            return render_template("login.html", lang=lang)

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["lang"] = lang
        next_url = normalize_next_url(request.args.get("next") or request.form.get("next", ""))
        return redirect(next_url or url_for("portal", lang=lang))

    if "user_id" in session:
        return redirect(url_for("portal", lang=lang))
    return render_template("login.html", lang=lang)


@app.post("/logout")
@login_required
def logout():
    lang = get_lang()
    session.clear()
    return redirect(url_for("login", lang=lang))


@app.route("/")
@login_required
def portal():
    lang = get_lang()
    username = current_username()
    return render_template(
        "portal.html",
        lang=lang,
        current_user=username,
        has_unread_messages=has_unread_messages(username),
    )


@app.route("/games")
@login_required
def games_home():
    lang = get_lang()
    return render_template("games_home.html", lang=lang, current_user=current_username())


def load_leaderboard(game_name, difficulty="normal", limit=5, days=None):
    conn = get_db_connection()
    where_extra = ""
    params = [game_name]
    if days is not None:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        where_extra = " AND created_at >= ? "
        params.append(cutoff)
    params.append(limit)
    if game_name in TIME_RANK_GAMES:
        rows = conn.execute(
            """
            SELECT username, MIN(score) AS best_score
            FROM game_scores
            WHERE game_name = ? {where_extra}
            GROUP BY username
            ORDER BY best_score ASC, username ASC
            LIMIT ?
            """.format(where_extra=where_extra),
            tuple(params),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT username, MAX(score) AS best_score
            FROM game_scores
            WHERE game_name = ? {where_extra}
            GROUP BY username
            ORDER BY best_score DESC, username ASC
            LIMIT ?
            """.format(where_extra=where_extra),
            tuple(params),
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_today_incense_count():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    row = conn.execute("SELECT count FROM incense_daily WHERE day = ?", (today,)).fetchone()
    conn.close()
    return int(row["count"]) if row else 0


@app.route("/games/<game_name>")
@login_required
def game_page(game_name):
    if game_name not in SUPPORTED_GAMES:
        return redirect(url_for("games_home", lang=get_lang()))
    lang = get_lang()
    difficulty = request.args.get("difficulty", "normal")
    if difficulty not in SUPPORTED_DIFFICULTIES:
        difficulty = "normal"
    return render_template(
        "game_play.html",
        lang=lang,
        current_user=current_username(),
        game_name=game_name,
        difficulty=difficulty,
        leaderboard_all=load_leaderboard(game_name, difficulty, limit=5),
        leaderboard_week=load_leaderboard(game_name, difficulty, limit=5, days=7),
    )


@app.post("/api/games/<game_name>/score")
@login_required
def submit_game_score(game_name):
    if game_name not in SUPPORTED_GAMES:
        return jsonify({"ok": False, "error": "unsupported game"}), 400
    try:
        payload = request.get_json(force=True) or {}
        score = int(payload.get("score", 0))
        difficulty = str(payload.get("difficulty", "normal")).strip().lower()
    except Exception:
        return jsonify({"ok": False, "error": "invalid score"}), 400

    if score < 0 or difficulty not in SUPPORTED_DIFFICULTIES:
        return jsonify({"ok": False, "error": "invalid score"}), 400

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO game_scores (user_id, username, game_name, difficulty, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session.get("user_id"),
            current_username(),
            game_name,
            "normal",
            score,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "leaderboard_all": load_leaderboard(game_name, difficulty, limit=5),
            "leaderboard_week": load_leaderboard(game_name, difficulty, limit=5, days=7),
        }
    )


@app.route("/practice")
@login_required
def index():
    lang = get_lang()
    all_df = load_index()
    progress = load_progress(current_username())

    subject = selected_filter_values("subject")
    chapter = selected_filter_values("chapter")
    topic = selected_filter_values("topic")
    year = selected_filter_values("year")
    mode = request.args.get("mode", "question")
    selected_id = request.args.get("selected_id", "")

    only_unfinished = request.args.get("only_unfinished", "") == "1"
    only_favorite = request.args.get("only_favorite", "") == "1"

    df = all_df.copy()

    df = apply_multi_filter(df, "subject", subject)
    chapter_options_df = df.copy()

    df = apply_multi_filter(df, "chapter", chapter)
    topic_options_df = df.copy()

    df = apply_multi_filter(df, "topic", topic)
    year_options_df = df.copy()

    df = apply_multi_filter(df, "year", year)

    records = [merge_record(row, progress) for _, row in df.iterrows()]
    if only_unfinished:
        records = [r for r in records if not r["done"]]
    if only_favorite:
        records = [r for r in records if r["favorite"]]

    if records and not selected_id:
        selected_id = records[0]["id"]
    selected = next(
        (r for r in records if r["id"] == selected_id), records[0] if records else None
    )

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
        lang=lang,
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
        current_user=current_username(),
    )


@app.route("/pdfs/<path:filename>")
@login_required
def serve_pdf(filename):
    return send_from_directory(PDF_BASE, filename)


def _toggle_progress_field(qid, field):
    if field not in {"done", "favorite"}:
        return jsonify({"ok": False, "error": "invalid field"}), 400

    username = current_username()
    progress = load_progress(username)
    item = progress.setdefault(qid, {})
    item[field] = not bool(item.get(field, False))
    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_progress(username, progress)
    return jsonify({"ok": True, field: item[field]})


@app.post("/toggle/<path:qid>/<field>")
@login_required
def toggle(qid, field):
    return _toggle_progress_field(qid, field)


@app.post("/toggle")
@login_required
def toggle_by_payload():
    payload = request.get_json(silent=True) or {}
    qid = str(payload.get("qid", "")).strip()
    field = str(payload.get("field", "")).strip()
    if not qid:
        return jsonify({"ok": False, "error": "missing qid"}), 400
    return _toggle_progress_field(qid, field)


@app.post("/note/<path:qid>")
@login_required
def save_note_route(qid):
    username = current_username()
    progress = load_progress(username)
    item = progress.setdefault(qid, {})
    item["note"] = request.form.get("note", "")
    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_progress(username, progress)
    return redirect(request.referrer or url_for("index", lang=get_lang()))


@app.route("/learn")
@login_required
def learn_page():
    lang = get_lang()
    return render_template("learn.html", lang=lang, current_user=current_username())


@app.route("/learn/slides")
@login_required
def learn_slides_page():
    lang = get_lang()
    chapter_map = list_chapter_files(SLIDES_DIR, ".pdf")
    chapters = list(chapter_map.keys())
    selected_chapter = request.args.get("chapter", "").strip()
    if chapters and selected_chapter not in chapter_map:
        selected_chapter = chapters[0]
    slides = chapter_map.get(selected_chapter, []) if selected_chapter else []
    selected = request.args.get("file", "").strip()
    selected_slide = None
    if slides:
        selected_slide = next((it for it in slides if it["name"] == selected), slides[0])
    return render_template(
        "learn_slides.html",
        lang=lang,
        current_user=current_username(),
        chapters=chapters,
        selected_chapter=selected_chapter,
        slides=slides,
        selected_slide=selected_slide,
    )


@app.route("/learn/animations")
@login_required
def learn_animations_page():
    lang = get_lang()
    chapter_map = list_chapter_files(ANIMATIONS_DIR, ".html")
    chapters = list(chapter_map.keys())
    selected_chapter = request.args.get("chapter", "").strip()
    if chapters and selected_chapter not in chapter_map:
        selected_chapter = chapters[0]
    pages = chapter_map.get(selected_chapter, []) if selected_chapter else []
    selected = request.args.get("file", "").strip()
    selected_page = None
    if pages:
        selected_page = next((it for it in pages if it["name"] == selected), pages[0])
    return render_template(
        "learn_animations.html",
        lang=lang,
        current_user=current_username(),
        chapters=chapters,
        selected_chapter=selected_chapter,
        pages=pages,
        selected_page=selected_page,
    )


@app.route("/learn/articles")
@login_required
def learn_articles_page():
    lang = get_lang()
    return render_template(
        "learn_articles.html",
        lang=lang,
        current_user=current_username(),
        items=load_section_items("articles.json"),
    )


@app.route("/learn/projects")
@login_required
def learn_projects_page():
    lang = get_lang()
    return render_template(
        "learn_projects.html",
        lang=lang,
        current_user=current_username(),
        items=load_section_items("projects.json"),
    )


@app.route("/learn/announcements")
@login_required
def learn_announcements_page():
    lang = get_lang()
    return render_template(
        "learn_announcements.html",
        lang=lang,
        current_user=current_username(),
        items=load_section_items("announcements.json"),
    )


@app.route("/learn/files")
@login_required
def learn_files_page():
    lang = get_lang()
    docs = list_files_with_suffix(FILES_DIR, ".pdf")
    selected = request.args.get("file", "").strip()
    selected_doc = None
    if docs:
        selected_doc = next((it for it in docs if it["name"] == selected), docs[0])
    return render_template(
        "learn_files.html",
        lang=lang,
        current_user=current_username(),
        docs=docs,
        selected_doc=selected_doc,
    )


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat_page():
    lang = get_lang()
    current_user = current_username()
    conn = get_db_connection()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        receiver = request.form.get("receiver", "").strip()
        if content and receiver:
            target = conn.execute(
                "SELECT id, username FROM users WHERE username = ?",
                (receiver,),
            ).fetchone()
            if not target:
                flash("Target user not found." if is_en() else "发送对象不存在。")
            else:
                conn.execute(
                    """
                    INSERT INTO internal_messages
                    (sender_id, sender_username, receiver_username, content, is_read, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (
                        session.get("user_id"),
                        current_user,
                        target["username"],
                        content[:2000],
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                conn.commit()
                flash("Sent successfully." if is_en() else "站内信发送成功。")
                conn.close()
                return redirect(url_for("chat_page", lang=lang))

    inbox = conn.execute(
        """
        SELECT id, sender_username, content, is_read, created_at
        FROM internal_messages
        WHERE receiver_username = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (current_user,),
    ).fetchall()
    sent = conn.execute(
        """
        SELECT id, receiver_username, content, created_at
        FROM internal_messages
        WHERE sender_username = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (current_user,),
    ).fetchall()
    unread_ids = [int(row["id"]) for row in inbox if int(row["is_read"]) == 0]
    if unread_ids:
        conn.executemany(
            "UPDATE internal_messages SET is_read = 1 WHERE id = ?",
            [(mid,) for mid in unread_ids],
        )
        conn.commit()
    conn.close()
    return render_template(
        "chat.html",
        lang=lang,
        current_user=current_user,
        inbox=[dict(row) for row in inbox],
        sent=[dict(row) for row in sent],
        has_unread_messages=has_unread_messages(current_user),
    )


@app.route("/code")
@login_required
def code_page():
    lang = get_lang()
    return render_template("code_lab.html", lang=lang, current_user=current_username())


@app.route("/profile")
@login_required
def profile_page():
    lang = get_lang()
    return render_template("profile.html", lang=lang, current_user=current_username(), incense_count=get_today_incense_count())



@app.post("/api/profile/fortune")
@login_required
def draw_fortune():
    import random as _random

    r = _random.random()
    if r < 0.50:
        grade = "A*"
    elif r < 0.80:
        grade = "A"
    elif r < 0.95:
        grade = "B"
    else:
        grade = "C"
    return jsonify({"ok": True, "grade": grade})


@app.post("/api/profile/incense")
@login_required
def burn_incense():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO incense_daily(day, count) VALUES (?, 1)
        ON CONFLICT(day) DO UPDATE SET count = count + 1
        """,
        (today,),
    )
    row = conn.execute("SELECT count FROM incense_daily WHERE day = ?", (today,)).fetchone()
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "count": int(row["count"])})

def run_caie_pseudocode(source: str, inputs=None):
    raw_lines = [ln.rstrip() for ln in source.splitlines() if ln.strip()]
    out = []
    input_queue = list(inputs or [])

    default_by_type = {
        "INTEGER": 0,
        "REAL": 0.0,
        "STRING": "",
        "BOOLEAN": False,
    }
    keyword_tokens = {
        "DIV", "MOD", "AND", "OR", "NOT", "TRUE", "FALSE", "RETURN", "CALL",
        "MIDSTRING", "RAND",
    }

    subroutines = {}
    lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        m_proc = re.match(r"PROCEDURE\s+([A-Za-z_]\w*)\s*\((.*)\)", line, re.I)
        m_func = re.match(r"FUNCTION\s+([A-Za-z_]\w*)\s*\((.*)\)", line, re.I)
        if m_proc or m_func:
            kind = "PROCEDURE" if m_proc else "FUNCTION"
            m = m_proc or m_func
            name = m.group(1)
            params_raw = m.group(2).strip()
            params = [x.strip() for x in params_raw.split(",") if x.strip()] if params_raw else []
            end_token = "ENDPROCEDURE" if kind == "PROCEDURE" else "ENDFUNCTION"
            body = []
            i += 1
            while i < len(raw_lines) and raw_lines[i].strip().upper() != end_token:
                body.append(raw_lines[i].strip())
                i += 1
            if i >= len(raw_lines):
                raise ValueError(f"{kind} '{name}' missing {end_token}")
            subroutines[name] = {"kind": kind, "params": params, "body": body}
        else:
            lines.append(line)
        i += 1

    def infer_type(value):
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "REAL"
        return "STRING"

    def parse_declare(line: str, env, declared, arrays, scalar_types):
        m_scalar = re.match(r"DECLARE\s+([A-Za-z_]\w*)\s*:\s*([A-Za-z]+)", line, re.I)
        m_array = re.match(
            r"DECLARE\s+([A-Za-z_]\w*)\s*:\s*ARRAY\s*\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]\s*OF\s*([A-Za-z]+)",
            line,
            re.I,
        )
        if m_array:
            name = m_array.group(1)
            lower, upper = int(m_array.group(2)), int(m_array.group(3))
            if upper < lower:
                raise ValueError(f"Invalid ARRAY bounds in DECLARE: {line}")
            declared[name] = "array"
            arrays[name] = {
                "lower": lower,
                "upper": upper,
                "values": [0] * (upper - lower + 1),
                "elem_type": m_array.group(4).upper(),
            }
            return True
        if m_scalar:
            name = m_scalar.group(1)
            ptype = m_scalar.group(2).upper()
            declared[name] = "scalar"
            scalar_types[name] = ptype
            env[name] = default_by_type.get(ptype, 0)
            return True
        return False

    def execute_block(block_lines, env, declared, arrays, scalar_types, allow_return=False):
        def ensure_scalar_declared(name: str):
            if name not in declared:
                raise ValueError(f"Variable '{name}' used before DECLARE")
            if declared[name] != "scalar":
                raise ValueError(f"'{name}' is an ARRAY and must be indexed")

        def ensure_array_declared(name: str):
            if name not in declared:
                raise ValueError(f"Array '{name}' used before DECLARE")
            if declared[name] != "array":
                raise ValueError(f"'{name}' is not an ARRAY")

        def cast_input(name: str, raw):
            t = scalar_types.get(name, "STRING")
            if t == "INTEGER":
                return int(raw)
            if t == "REAL":
                return float(raw)
            if t == "BOOLEAN":
                return str(raw).strip().lower() in {"true", "1", "yes", "y"}
            return str(raw)

        def arr_get(name: str, idx: int):
            ensure_array_declared(name)
            spec = arrays[name]
            lower, upper = spec["lower"], spec["upper"]
            if idx < lower or idx > upper:
                raise ValueError(f"Array index out of range: {name}[{idx}]")
            return spec["values"][idx - lower]

        def arr_set(name: str, idx: int, value):
            ensure_array_declared(name)
            spec = arrays[name]
            lower, upper = spec["lower"], spec["upper"]
            if idx < lower or idx > upper:
                raise ValueError(f"Array index out of range: {name}[{idx}]")
            spec["values"][idx - lower] = value

        def midstring(value, start, length):
            s = str(value)
            st = int(start)
            ln = int(length)
            if ln <= 0:
                return ""
            return s[max(0, st - 1): max(0, st - 1) + ln]

        def rand_func(*args):
            if len(args) == 1:
                return random.randint(0, int(args[0]))
            if len(args) == 2:
                return random.randint(int(args[0]), int(args[1]))
            raise ValueError("RAND expects 1 or 2 arguments")

        def call_subroutine(name: str, args, expect_value=False):
            if name not in subroutines:
                raise ValueError(f"Unknown subroutine: {name}")
            sub = subroutines[name]
            if expect_value and sub["kind"] != "FUNCTION":
                raise ValueError(f"{name} is PROCEDURE and cannot be used in expression")
            if not expect_value and sub["kind"] != "PROCEDURE":
                raise ValueError(f"{name} is FUNCTION; use it in expression")
            if len(args) != len(sub["params"]):
                raise ValueError(f"{name} expects {len(sub['params'])} args, got {len(args)}")

            local_env, local_declared, local_arrays, local_scalar_types = {}, {}, {}, {}
            for pname, pval in zip(sub["params"], args):
                local_declared[pname] = "scalar"
                local_env[pname] = pval
                local_scalar_types[pname] = infer_type(pval)
            returned, value = execute_block(
                sub["body"], local_env, local_declared, local_arrays, local_scalar_types, allow_return=sub["kind"] == "FUNCTION"
            )
            if sub["kind"] == "FUNCTION":
                if not returned:
                    raise ValueError(f"FUNCTION {name} must RETURN a value")
                return value
            return None

        def eval_expr(expr: str):
            expr = expr.strip()
            if ".." in expr:
                a, b = expr.split("..", 1)
                return list(range(int(eval_expr(a)), int(eval_expr(b)) + 1))
            expr = re.sub(r"\bDIV\b", "//", expr, flags=re.I)
            expr = re.sub(r"\bMOD\b", "%", expr, flags=re.I)
            expr = re.sub(r"\bTRUE\b", "True", expr, flags=re.I)
            expr = re.sub(r"\bFALSE\b", "False", expr, flags=re.I)

            for token in re.findall(r"\b[A-Za-z_]\w*\b", expr):
                t = token.upper()
                if t in keyword_tokens or token in {"True", "False"}:
                    continue
                if token in subroutines:
                    continue
                if token not in declared:
                    raise ValueError(f"Identifier '{token}' used before DECLARE")

            def replace_array_access(m):
                name = m.group(1)
                idx_expr = m.group(2).strip()
                ensure_array_declared(name)
                return f"__arr_get__('{name}', ({idx_expr}))"

            expr = re.sub(r"\b([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]", replace_array_access, expr)
            local_env = {k: v for k, v in env.items() if declared.get(k) == "scalar"}
            local_env["__arr_get__"] = arr_get
            local_env["MIDSTRING"] = midstring
            local_env["RAND"] = rand_func
            for name in subroutines:
                local_env[name] = (lambda n: (lambda *args: call_subroutine(n, list(args), expect_value=True)))(name)
            return eval(expr, {"__builtins__": {}}, local_env)

        i = 0
        stack = []
        while i < len(block_lines):
            line = block_lines[i].strip()
            upper = line.upper()
            if upper.startswith("DECLARE "):
                if not parse_declare(line, env, declared, arrays, scalar_types):
                    raise ValueError(f"Invalid DECLARE syntax: {line}")
            elif upper.startswith("OUTPUT "):
                out.append(str(eval_expr(line[7:])))
            elif upper.startswith("INPUT "):
                var = line[6:].strip()
                ensure_scalar_declared(var)
                if not input_queue:
                    raise ValueError(f"INPUT required for '{var}' but no input provided")
                env[var] = cast_input(var, input_queue.pop(0))
            elif upper.startswith("CALL "):
                m = re.match(r"CALL\s+([A-Za-z_]\w*)\s*\((.*)\)", line, re.I)
                if not m:
                    raise ValueError(f"Invalid CALL syntax: {line}")
                name = m.group(1)
                args_text = m.group(2).strip()
                args = [eval_expr(x.strip()) for x in args_text.split(",") if x.strip()] if args_text else []
                call_subroutine(name, args, expect_value=False)
            elif upper.startswith("RETURN "):
                if not allow_return:
                    raise ValueError("RETURN is only allowed inside FUNCTION")
                return True, eval_expr(line[7:])
            elif upper.startswith("CASE OF"):
                case_value = eval_expr(line[7:].strip())
                depth, j = 1, i + 1
                while j < len(block_lines):
                    u = block_lines[j].strip().upper()
                    if u.startswith("CASE OF"):
                        depth += 1
                    elif u == "ENDCASE":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if j >= len(block_lines):
                    raise ValueError("CASE missing ENDCASE")

                segments = []
                current_labels = None
                current_body = []
                for k in range(i + 1, j):
                    raw = block_lines[k].strip()
                    m_other = re.match(r"OTHERWISE\s*:", raw, re.I)
                    m_label = re.match(r"(.+?)\s*:", raw)
                    if m_other or m_label:
                        if current_labels is not None:
                            segments.append((current_labels, current_body))
                        current_body = []
                        if m_other:
                            current_labels = "OTHERWISE"
                        else:
                            labels_raw = m_label.group(1)
                            current_labels = [eval_expr(x.strip()) for x in labels_raw.split(",") if x.strip()]
                    else:
                        current_body.append(raw)
                if current_labels is not None:
                    segments.append((current_labels, current_body))

                chosen = None
                for labels, body in segments:
                    if labels == "OTHERWISE":
                        if chosen is None:
                            chosen = body
                    elif case_value in labels:
                        chosen = body
                        break
                if chosen:
                    returned, value = execute_block(chosen, env, declared, arrays, scalar_types, allow_return=allow_return)
                    if returned:
                        return True, value
                i = j
            elif upper.startswith("WHILE ") and upper.endswith(" DO"):
                cond_expr = line[6:-3].strip()
                if bool(eval_expr(cond_expr)):
                    stack.append(("WHILE", cond_expr, i))
                else:
                    depth, j = 1, i + 1
                    while j < len(block_lines):
                        u = block_lines[j].strip().upper()
                        if u.startswith("WHILE ") and u.endswith(" DO"):
                            depth += 1
                        elif u == "ENDWHILE":
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    i = j
            elif upper == "ENDWHILE":
                if not stack or stack[-1][0] != "WHILE":
                    raise ValueError("ENDWHILE without WHILE")
                _, cond_expr, start = stack[-1]
                if bool(eval_expr(cond_expr)):
                    i = start
                else:
                    stack.pop()
            elif upper == "REPEAT":
                stack.append(("REPEAT", i))
            elif upper.startswith("UNTIL "):
                if not stack or stack[-1][0] != "REPEAT":
                    raise ValueError("UNTIL without REPEAT")
                cond_expr = line[6:].strip()
                _, start = stack[-1]
                if bool(eval_expr(cond_expr)):
                    stack.pop()
                else:
                    i = start
            elif upper.startswith("FOR ") and " TO " in upper:
                m = re.match(r"FOR\s+(\w+)\s*<-\s*(.+)\s+TO\s+(.+)", line, re.I)
                if not m:
                    raise ValueError(f"Invalid FOR syntax: {line}")
                var, a, b = m.group(1), eval_expr(m.group(2)), eval_expr(m.group(3))
                ensure_scalar_declared(var)
                env[var] = int(a)
                stack.append(("FOR", var, int(b), i))
            elif "<-" in line:
                var, expr = [x.strip() for x in line.split("<-", 1)]
                arr_ref = re.match(r"^([A-Za-z_]\w*)\s*\[\s*(.+)\s*\]$", var)
                if arr_ref:
                    name = arr_ref.group(1)
                    idx = int(eval_expr(arr_ref.group(2)))
                    arr_set(name, idx, eval_expr(expr))
                else:
                    ensure_scalar_declared(var)
                    env[var] = eval_expr(expr)
            elif upper.startswith("IF ") and upper.endswith("THEN"):
                cond = bool(eval_expr(line[3:-4]))
                stack.append(("IF", cond))
                if not cond:
                    depth, j = 1, i + 1
                    while j < len(block_lines):
                        u = block_lines[j].strip().upper()
                        if u.startswith("IF ") and u.endswith("THEN"):
                            depth += 1
                        elif u == "ENDIF":
                            depth -= 1
                            if depth == 0:
                                break
                        elif u == "ELSE" and depth == 1:
                            break
                        j += 1
                    i = j
            elif upper == "ELSE":
                if stack and stack[-1][0] == "IF" and stack[-1][1]:
                    depth, j = 1, i + 1
                    while j < len(block_lines):
                        u = block_lines[j].strip().upper()
                        if u.startswith("IF ") and u.endswith("THEN"):
                            depth += 1
                        elif u == "ENDIF":
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    i = j
            elif upper == "ENDIF":
                if stack and stack[-1][0] == "IF":
                    stack.pop()
            elif upper.startswith("NEXT"):
                m = re.match(r"NEXT(?:\s+([A-Za-z_]\w*))?$", line, re.I)
                if not m:
                    raise ValueError(f"Invalid NEXT syntax: {line}")
                if not stack or stack[-1][0] != "FOR":
                    raise ValueError("NEXT without FOR")
                _, var, end, start = stack[-1]
                next_var = m.group(1)
                if next_var and next_var != var:
                    raise ValueError(f"NEXT variable mismatch: expected {var}, got {next_var}")
                env[var] += 1
                if env[var] <= end:
                    i = start
                else:
                    stack.pop()
            i += 1
        return False, None

    global_env, global_declared, global_arrays, global_scalar_types = {}, {}, {}, {}
    execute_block(lines, global_env, global_declared, global_arrays, global_scalar_types, allow_return=False)
    return "\n".join(out)


@app.post("/api/code/run")
@login_required
def run_code_route():
    payload = request.get_json(force=True) or {}
    source = str(payload.get("source", ""))
    raw_inputs = payload.get("inputs", [])
    if isinstance(raw_inputs, str):
        inputs = [x for x in raw_inputs.splitlines() if x.strip() != ""]
    elif isinstance(raw_inputs, list):
        inputs = [str(x) for x in raw_inputs]
    else:
        inputs = []
    try:
        result = run_caie_pseudocode(source, inputs=inputs)
        return jsonify({"ok": True, "output": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False, port=8000)
