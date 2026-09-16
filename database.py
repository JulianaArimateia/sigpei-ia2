import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("sigpei.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_date TEXT,
            school TEXT,
            grade TEXT,
            classroom TEXT,
            shift TEXT,
            diagnosis TEXT,
            cid TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pei_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher TEXT,
            team_members TEXT,
            current_abilities TEXT,
            long_term_goals TEXT,
            short_term_goals TEXT,
            strategies TEXT,
            adaptations TEXT,
            support_services TEXT,
            evaluation_method TEXT,
            review_date TEXT,
            elaboration_date TEXT,
            raw_input TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pei_id INTEGER,
            filename TEXT,
            file_type TEXT,
            content_text TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pei_id) REFERENCES pei_records(id)
        )
    """)

    conn.commit()
    conn.close()


def save_student(data: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT INTO students (name, birth_date, school, grade, classroom, shift, diagnosis, cid)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("nome"), data.get("data_nascimento"), data.get("escola"),
            data.get("serie"), data.get("turma"), data.get("turno"),
            data.get("diagnostico"), data.get("cid"),
        ),
    )
    student_id = c.lastrowid
    conn.commit()
    conn.close()
    return student_id


def save_pei(data: dict, student_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT INTO pei_records (
               student_id, teacher, team_members, current_abilities,
               long_term_goals, short_term_goals, strategies, adaptations,
               support_services, evaluation_method, review_date, elaboration_date, raw_input
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            student_id,
            data.get("professor"),
            json.dumps(data.get("equipe", []), ensure_ascii=False),
            json.dumps(data.get("habilidades_atuais", {}), ensure_ascii=False),
            json.dumps(data.get("objetivos_longo_prazo", []), ensure_ascii=False),
            json.dumps(data.get("objetivos_curto_prazo", []), ensure_ascii=False),
            json.dumps(data.get("estrategias", []), ensure_ascii=False),
            json.dumps(data.get("adaptacoes_curriculares", []), ensure_ascii=False),
            json.dumps(data.get("servicos_apoio", []), ensure_ascii=False),
            data.get("avaliacao"),
            data.get("data_revisao"),
            data.get("data_elaboracao", datetime.now().strftime("%d/%m/%Y")),
            data.get("raw_input", ""),
        ),
    )
    pei_id = c.lastrowid
    conn.commit()
    conn.close()
    return pei_id


def save_document(pei_id: int, filename: str, file_type: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO documents (pei_id, filename, file_type, content_text) VALUES (?, ?, ?, ?)",
        (pei_id, filename, file_type, content),
    )
    conn.commit()
    conn.close()


def get_all_pei_records() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.created_at, p.elaboration_date,
               s.name AS student_name, s.school, s.grade, s.diagnosis
        FROM pei_records p
        JOIN students s ON p.student_id = s.id
        ORDER BY p.created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_pei_by_id(pei_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT p.*, s.name AS student_name, s.birth_date, s.school,
               s.grade, s.classroom, s.shift, s.diagnosis, s.cid
        FROM pei_records p
        JOIN students s ON p.student_id = s.id
        WHERE p.id = ?
    """, (pei_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pei_records")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT school) FROM students")
    schools = c.fetchone()[0]
    month = datetime.now().strftime("%Y-%m")
    c.execute("SELECT COUNT(*) FROM pei_records WHERE created_at LIKE ?", (f"{month}%",))
    this_month = c.fetchone()[0]
    conn.close()
    return {"total": total, "schools": schools, "this_month": this_month}
