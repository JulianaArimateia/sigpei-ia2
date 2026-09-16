import flet as ft
import os
import json
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import database
import ai_processor
import pei_generator

database.init_db()

# ── Cores ─────────────────────────────────────────────────────────────────────
# Mesma paleta da interface web (app2.0.py), para manter consistência visual.
P       = "#4f46e5"   # índigo primário
VIOLET  = "#7c3aed"
CYAN    = "#0891b2"
EMERALD = "#10b981"
ORANGE  = "#f97316"
PINK    = "#ec4899"
PA  = "#ede9fe"   # lilás claro (fundo de destaque)
SU  = EMERALD     # sucesso
ER  = "#ef4444"   # erro
BG  = "#f5f3ff"   # fundo da tela
SF  = "#ffffff"   # card/superfície
TX  = "#1e1b2e"   # texto
MU  = "#6b7280"   # texto suave

# Cor de destaque por área de habilidade (mesmo mapeamento da web)
HAB_COLORS = {
    "cognitiva": VIOLET, "comunicacao": CYAN, "socializacao": PINK,
    "motora": EMERALD, "autocuidado": ORANGE, "academica": P,
}


# ── Componentes reutilizáveis ─────────────────────────────────────────────────

def card(*controls, padding=16, mb=8):
    return ft.Container(
        content=ft.Column(list(controls), spacing=10),
        bgcolor=SF, border_radius=14, padding=padding,
        margin=ft.Margin.only(bottom=mb),
        shadow=ft.BoxShadow(blur_radius=8, color="#00000012", offset=ft.Offset(0, 2)),
    )


def sec(title: str, color: str = P):
    return ft.Container(
        content=ft.Text(title, color="white", size=12, weight=ft.FontWeight.BOLD),
        bgcolor=color, border_radius=8, padding=ft.Padding.symmetric(vertical=8, horizontal=14),
        margin=ft.Margin.only(top=6, bottom=4),
    )


def tfield(label, value="", multi=False, ref=None, expand=False, accent=None):
    return ft.TextField(
        label=label, value=value or "",
        multiline=multi, min_lines=2 if multi else 1, max_lines=5 if multi else 1,
        border_radius=8, filled=True, fill_color="#f5f3ff" if accent else "#f0f4f8",
        border_color=accent, focused_border_color=accent, border_width=1.4 if accent else 1,
        text_size=14, ref=ref,
        expand=expand,
    )


def btn_primary(text, on_click, icon=None, expand=False):
    return ft.FilledButton(
        text, icon=icon, on_click=on_click, expand=expand,
        style=ft.ButtonStyle(
            bgcolor=P, color="white",
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
        ),
    )


def btn_secondary(text, on_click, expand=False):
    return ft.FilledButton(
        text, on_click=on_click, expand=expand,
        style=ft.ButtonStyle(
            bgcolor=PA, color=VIOLET,
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
        ),
    )


# ── Leitura de arquivo pelo caminho ───────────────────────────────────────────

def read_file_path(path: str) -> str:
    name = path.lower()
    try:
        if name.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
        if name.endswith(".docx"):
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs).strip()
        if name.endswith(".txt"):
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
    except Exception as e:
        return f"[Erro ao ler {os.path.basename(path)}: {e}]"
    return ""


# ── App principal ─────────────────────────────────────────────────────────────

async def main(page: ft.Page):
    page.title = "SIGPEI-IA"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 0
    page.window.width = 420
    page.window.height = 820

    # Estado global
    st = {
        "pei_data": None,
        "doc_texts": [],
        "raw_input": "",
        "step": 1,
        "saved_id": None,
        "final_pei": None,
        "final_student": None,
    }

    # ── Área de conteúdo ──────────────────────────────────────────────────────
    body = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)

    def render(*controls):
        body.controls.clear()
        body.controls.extend(controls)
        page.update()

    def snack(msg: str, color=P):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color="white"), bgcolor=color, duration=3500
        )
        page.snack_bar.open = True
        page.update()

    def loading(msg="Processando…", sub=""):
        render(ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=48, height=48, color=P),
                    ft.Text(msg, color=TX, size=15, weight=ft.FontWeight.W_600),
                    ft.Text(sub, color=MU, size=13),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
                padding=60,
            ),
        ], alignment=ft.MainAxisAlignment.CENTER, expand=True))

    # ── PASSO 1: Entrada de dados ─────────────────────────────────────────────
    def show_step1():
        st["step"] = 1
        st["doc_texts"] = []
        text_ref    = ft.Ref[ft.TextField]()
        path_ref    = ft.Ref[ft.TextField]()
        doc_status  = ft.Text("Nenhum arquivo carregado", color=MU, size=12)

        def process(e):
            txt  = text_ref.current.value or ""
            docs = list(st.get("doc_texts") or [])
            if not txt.strip() and not docs:
                snack("Escreva ou fale alguma informação sobre o aluno.", ER)
                return
            loading("Analisando com IA…", "Aguarde 20–60 segundos")

            def run():
                try:
                    data = ai_processor.extract_pei_info(txt, "\n\n".join(docs))
                    st["pei_data"] = data
                    st["raw_input"] = txt
                    show_step2()
                except Exception as ex:
                    snack(f"Erro: {ex}", ER)
                    show_step1()

            threading.Thread(target=run, daemon=True).start()

        def start_voice(e):
            snack("Ouvindo… fale agora (máx. 10 s)", P)

            def record():
                try:
                    import sounddevice as sd
                    import io
                    import wave
                    import speech_recognition as sr

                    samplerate = 16000
                    audio = sd.rec(int(10 * samplerate), samplerate=samplerate,
                                   channels=1, dtype="int16")
                    sd.wait()

                    buf = io.BytesIO()
                    with wave.open(buf, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(samplerate)
                        wf.writeframes(audio.tobytes())
                    buf.seek(0)

                    recognizer = sr.Recognizer()
                    with sr.AudioFile(buf) as src:
                        audio_data = recognizer.record(src)
                    text = recognizer.recognize_google(audio_data, language="pt-BR")

                    f = text_ref.current
                    f.value = ((f.value or "") + " " + text).strip()
                    snack(f'Capturado: "{text}"', SU)
                    page.update()
                except Exception as ex:
                    snack(f"Erro no microfone: {ex}", ER)

            threading.Thread(target=record, daemon=True).start()

        def load_file(e):
            path = (path_ref.current.value or "").strip()
            if not path:
                snack("Cole o caminho do arquivo no campo acima.", ER)
                return
            if not os.path.isfile(path):
                snack("Arquivo não encontrado. Verifique o caminho.", ER)
                return

            def read():
                try:
                    text = read_file_path(path)
                    if text.startswith("[Erro"):
                        snack(text, ER)
                        return
                    name = os.path.basename(path)
                    st["doc_texts"].append(f"[Arquivo: {name}]\n{text}")
                    doc_status.value = f"✓ {name}"
                    path_ref.current.value = ""
                    page.update()
                except Exception as ex:
                    snack(f"Erro ao ler arquivo: {ex}", ER)

            threading.Thread(target=read, daemon=True).start()

        render(ft.Container(padding=12, expand=True, content=ft.Column([
            card(
                ft.Row([ft.Icon(ft.Icons.SCHOOL, color=P),
                        ft.Text("Novo PEI", size=18, weight=ft.FontWeight.BOLD, color=TX)], spacing=8),
                ft.Text("Passo 1 de 3 — Informações do Aluno", color=MU, size=13),
            ),
            card(
                ft.Row([ft.Icon(ft.Icons.EDIT_NOTE, color=P),
                        ft.Text("Descreva o aluno", weight=ft.FontWeight.W_600)], spacing=8),
                ft.TextField(
                    ref=text_ref,
                    multiline=True, min_lines=6, max_lines=10,
                    hint_text=(
                        "Ex: Maria Silva, 10 anos, 4º ano A, EMEF São Paulo, turno vespertino.\n"
                        "Diagnóstico: Síndrome de Down (CID Q90). Boa socialização, "
                        "dificuldade em leitura e escrita..."
                    ),
                    border_radius=10, filled=True, fill_color="#f0f4f8", text_size=14,
                ),
                ft.FilledButton(
                    "🎤  Usar microfone",
                    on_click=start_voice,
                    style=ft.ButtonStyle(
                        bgcolor="#e9d8fd", color="#553c9a",
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                ),
            ),
            card(
                ft.Row([ft.Icon(ft.Icons.ATTACH_FILE, color=P),
                        ft.Text("Documentos do aluno (opcional)", weight=ft.FontWeight.W_600)], spacing=8),
                ft.Text(
                    "Cole o caminho completo do arquivo (TXT, PDF ou DOCX) e clique em Carregar:",
                    color=MU, size=12,
                ),
                ft.TextField(
                    ref=path_ref,
                    hint_text=r"Ex: C:\Users\Juliana\Documents\avaliacao.pdf",
                    border_radius=8, filled=True, fill_color="#f0f4f8", text_size=13,
                ),
                ft.FilledButton(
                    "📂  Carregar arquivo",
                    on_click=load_file,
                    style=ft.ButtonStyle(bgcolor=PA, color=P, shape=ft.RoundedRectangleBorder(radius=8)),
                ),
                doc_status,
            ),
            ft.Container(
                content=btn_primary("🤖  Analisar com IA", process, expand=True),
                margin=ft.Margin.only(top=4),
            ),
            ft.Container(height=20),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)))

    # ── PASSO 2: Revisão do formulário ────────────────────────────────────────
    def show_step2():
        st["step"] = 2
        pei = st["pei_data"] or {}
        hab = pei.get("habilidades_atuais") or {}

        def fl(lst):
            if not lst: return ""
            if lst and isinstance(lst[0], dict):
                return "\n".join(f"{g.get('objetivo','')} | {g.get('criterio','')} | {g.get('prazo','')}" for g in lst)
            return "\n".join(str(x) for x in lst)

        # Referências dos campos
        r = {k: ft.Ref[ft.TextField]() for k in [
            "nome","nasc","escola","serie","turma","diag","cid","prof","equipe",
            "hcog","hcom","hsoc","hmot","haut","hacad",
            "olp","ocp","estr","adap","serv","aval","delab","drev",
        ]}

        turno_dd = ft.Dropdown(
            label="Turno", value=pei.get("turno") or "",
            options=[ft.dropdown.Option(t) for t in ["","Matutino","Vespertino","Noturno","Integral"]],
            border_radius=8, filled=True, fill_color="#f0f4f8", expand=True,
        )

        def salvar(e):
            nome = r["nome"].current.value or ""
            if not nome.strip():
                snack("Nome do aluno é obrigatório!", ER); return

            def split(s): return [l.strip() for l in (s or "").splitlines() if l.strip()]

            ocp = []
            for line in split(r["ocp"].current.value):
                parts = [p.strip() for p in line.split("|")]
                ocp.append({"objetivo": parts[0], "criterio": parts[1] if len(parts)>1 else "", "prazo": parts[2] if len(parts)>2 else ""})

            student = {
                "nome": nome, "data_nascimento": r["nasc"].current.value,
                "escola": r["escola"].current.value, "serie": r["serie"].current.value,
                "turma": r["turma"].current.value, "turno": turno_dd.value,
                "diagnostico": r["diag"].current.value, "cid": r["cid"].current.value,
            }
            final = {
                "professor": r["prof"].current.value,
                "equipe": split(r["equipe"].current.value),
                "habilidades_atuais": {
                    "cognitiva": r["hcog"].current.value, "comunicacao": r["hcom"].current.value,
                    "socializacao": r["hsoc"].current.value, "motora": r["hmot"].current.value,
                    "autocuidado": r["haut"].current.value, "academica": r["hacad"].current.value,
                },
                "objetivos_longo_prazo": split(r["olp"].current.value),
                "objetivos_curto_prazo": ocp,
                "estrategias": split(r["estr"].current.value),
                "adaptacoes_curriculares": split(r["adap"].current.value),
                "servicos_apoio": split(r["serv"].current.value),
                "avaliacao": r["aval"].current.value,
                "data_elaboracao": r["delab"].current.value,
                "data_revisao": r["drev"].current.value,
                "raw_input": st["raw_input"],
            }
            loading("Salvando…")

            def do_save():
                try:
                    sid = database.save_student(student)
                    pid = database.save_pei(final, sid)
                    for dt in st["doc_texts"]:
                        database.save_document(pid, dt.split("\n")[0], "document", dt)
                    st["saved_id"] = pid
                    st["final_pei"] = final
                    st["final_student"] = student
                    show_step3()
                except Exception as ex:
                    snack(f"Erro ao salvar: {ex}", ER)
                    show_step2()

            threading.Thread(target=do_save, daemon=True).start()

        render(ft.Container(padding=12, expand=True, content=ft.Column([
            card(
                ft.Row([ft.Icon(ft.Icons.FACT_CHECK, color=P), ft.Text("Revisar PEI", size=18, weight=ft.FontWeight.BOLD, color=TX)], spacing=8),
                ft.Text("Passo 2 de 3 — Confirme e edite os campos", color=MU, size=13),
            ),

            sec("IDENTIFICAÇÃO DO ALUNO", P),
            card(
                tfield("Nome Completo *", pei.get("nome"), ref=r["nome"]),
                ft.Row([tfield("Data de Nasc.", pei.get("data_nascimento"), ref=r["nasc"], expand=True), turno_dd], spacing=8),
                tfield("Escola", pei.get("escola"), ref=r["escola"]),
                ft.Row([tfield("Série/Ano", pei.get("serie"), ref=r["serie"], expand=True), tfield("Turma", pei.get("turma"), ref=r["turma"], expand=True)], spacing=8),
                ft.Row([tfield("Diagnóstico", pei.get("diagnostico"), ref=r["diag"], expand=True), tfield("CID-10", pei.get("cid"), ref=r["cid"], expand=True)], spacing=8),
                tfield("Professor(a) Responsável", pei.get("professor"), ref=r["prof"]),
                tfield("Equipe (um por linha)", "\n".join(pei.get("equipe") or []), multi=True, ref=r["equipe"]),
            ),

            sec("HABILIDADES ATUAIS", PINK),
            card(
                tfield("Cognitiva",     hab.get("cognitiva"),    multi=True, ref=r["hcog"],  accent=HAB_COLORS["cognitiva"]),
                tfield("Comunicação",   hab.get("comunicacao"),  multi=True, ref=r["hcom"],  accent=HAB_COLORS["comunicacao"]),
                tfield("Socialização",  hab.get("socializacao"), multi=True, ref=r["hsoc"],  accent=HAB_COLORS["socializacao"]),
                tfield("Motora",        hab.get("motora"),       multi=True, ref=r["hmot"],  accent=HAB_COLORS["motora"]),
                tfield("Autocuidado",   hab.get("autocuidado"),  multi=True, ref=r["haut"],  accent=HAB_COLORS["autocuidado"]),
                tfield("Acadêmica",     hab.get("academica"),    multi=True, ref=r["hacad"], accent=HAB_COLORS["academica"]),
            ),

            sec("OBJETIVOS", CYAN),
            card(
                tfield("Objetivos de Longo Prazo (um por linha)", fl(pei.get("objetivos_longo_prazo")), multi=True, ref=r["olp"]),
                ft.Text("Curto prazo → Objetivo | Critério | Prazo", color=MU, size=12),
                tfield("Objetivos de Curto Prazo", fl(pei.get("objetivos_curto_prazo")), multi=True, ref=r["ocp"]),
            ),

            sec("ESTRATÉGIAS E SERVIÇOS", ORANGE),
            card(
                tfield("Estratégias Pedagógicas (uma por linha)", fl(pei.get("estrategias")), multi=True, ref=r["estr"]),
                tfield("Adaptações Curriculares (uma por linha)", fl(pei.get("adaptacoes_curriculares")), multi=True, ref=r["adap"]),
                tfield("Serviços de Apoio (um por linha)", fl(pei.get("servicos_apoio")), multi=True, ref=r["serv"]),
                tfield("Método de Avaliação", pei.get("avaliacao"), multi=True, ref=r["aval"]),
            ),

            sec("DATAS", VIOLET),
            card(ft.Row([
                tfield("Elaboração", pei.get("data_elaboracao") or datetime.now().strftime("%d/%m/%Y"), ref=r["delab"], expand=True),
                tfield("Revisão", pei.get("data_revisao"), ref=r["drev"], expand=True),
            ], spacing=8)),

            ft.Row([
                btn_secondary("← Voltar", lambda e: show_step1(), expand=True),
                btn_primary("Salvar ✓", salvar, expand=True),
            ], spacing=8),
            ft.Container(height=24),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)))

    # ── PASSO 3: Sucesso ──────────────────────────────────────────────────────
    def show_step3():
        st["step"] = 3
        nome = (st.get("final_student") or {}).get("nome", "Aluno")
        pid  = st.get("saved_id", "")

        def gen_pdf(e):
            try:
                s = st["final_student"]
                sm = {"name": s.get("nome"), "birth_date": s.get("data_nascimento"),
                      "school": s.get("escola"), "grade": s.get("serie"),
                      "classroom": s.get("turma"), "shift": s.get("turno"),
                      "diagnosis": s.get("diagnostico"), "cid": s.get("cid")}
                pdf = pei_generator.generate_pei_pdf(sm, st["final_pei"])
                fname = f"PEI_{nome.replace(' ','_')}_{datetime.now():%Y%m%d}.pdf"
                dest = os.path.join(os.path.expanduser("~"), "Downloads", fname)
                with open(dest, "wb") as f:
                    f.write(pdf)
                snack(f"PDF salvo em Downloads/{fname}", SU)
            except Exception as ex:
                snack(f"Erro ao gerar PDF: {ex}", ER)

        def novo(e):
            for k in ("pei_data","doc_texts","raw_input","saved_id","final_pei","final_student"):
                st[k] = [] if k == "doc_texts" else None
            st["raw_input"] = ""
            show_step1()

        render(ft.Container(padding=24, expand=True, content=ft.Column([
            ft.Container(height=30),
            ft.Container(content=ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=SU, size=90), alignment=ft.alignment.center),
            ft.Container(height=16),
            ft.Text("PEI Salvo com Sucesso!", size=22, weight=ft.FontWeight.BOLD, color=TX, text_align=ft.TextAlign.CENTER),
            ft.Text(nome, size=17, color=P, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            ft.Text(f"Registro nº {pid}", size=13, color=MU, text_align=ft.TextAlign.CENTER),
            ft.Container(height=32),
            btn_primary("📄  Baixar PDF", gen_pdf, expand=True),
            ft.Container(height=10),
            btn_secondary("➕  Criar Novo PEI", novo, expand=True),
            ft.Container(height=10),
            ft.TextButton("Ver todos os registros →", on_click=lambda e: (nav_bar.__setattr__("selected_index", 1), show_registros(), page.update())),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)))

    # ── TELA: Registros ───────────────────────────────────────────────────────
    def show_registros():
        records = database.get_all_pei_records()
        results = ft.Column(spacing=6)
        search = ft.TextField(
            hint_text="Buscar por nome...", prefix_icon=ft.Icons.SEARCH,
            border_radius=10, filled=True, fill_color=SF,
        )

        def build(recs):
            results.controls.clear()
            if not recs:
                results.controls.append(ft.Container(
                    content=ft.Text("Nenhum PEI encontrado.", color=MU, text_align=ft.TextAlign.CENTER),
                    alignment=ft.alignment.center, padding=40,
                ))
            else:
                for rec in recs:
                    def make(r=rec):
                        def pdf_click(e, rec=r):
                            try:
                                full = database.get_pei_by_id(rec["id"])
                                if not full: return
                                sm = {"name": full.get("student_name"), "birth_date": full.get("birth_date"),
                                      "school": full.get("school"), "grade": full.get("grade"),
                                      "classroom": full.get("classroom"), "shift": full.get("shift"),
                                      "diagnosis": full.get("diagnosis"), "cid": full.get("cid")}
                                pm = {
                                    "professor": full.get("teacher"),
                                    "equipe": json.loads(full.get("team_members") or "[]"),
                                    "habilidades_atuais": json.loads(full.get("current_abilities") or "{}"),
                                    "objetivos_longo_prazo": json.loads(full.get("long_term_goals") or "[]"),
                                    "objetivos_curto_prazo": json.loads(full.get("short_term_goals") or "[]"),
                                    "estrategias": json.loads(full.get("strategies") or "[]"),
                                    "adaptacoes_curriculares": json.loads(full.get("adaptations") or "[]"),
                                    "servicos_apoio": json.loads(full.get("support_services") or "[]"),
                                    "avaliacao": full.get("evaluation_method"),
                                    "data_elaboracao": full.get("elaboration_date"),
                                    "data_revisao": full.get("review_date"),
                                }
                                pdf = pei_generator.generate_pei_pdf(sm, pm)
                                nome = (full.get("student_name") or "aluno").replace(" ", "_")
                                dest = os.path.join(os.path.expanduser("~"), "Downloads", f"PEI_{nome}.pdf")
                                with open(dest, "wb") as f:
                                    f.write(pdf)
                                snack(f"PDF salvo em Downloads/PEI_{nome}.pdf", SU)
                            except Exception as ex:
                                snack(f"Erro: {ex}", ER)

                        return card(
                            ft.Row([
                                ft.CircleAvatar(content=ft.Text((r.get("student_name") or "?")[0].upper(), color="white", weight=ft.FontWeight.BOLD), bgcolor=P, radius=20),
                                ft.Column([
                                    ft.Text(r.get("student_name","—"), weight=ft.FontWeight.BOLD, color=TX, size=14),
                                    ft.Text(f"{r.get('school','—')}  ·  {str(r.get('elaboration_date') or r.get('created_at',''))[:10]}", color=MU, size=12),
                                ], spacing=2, expand=True),
                                ft.IconButton(ft.Icons.PICTURE_AS_PDF, icon_color=P, tooltip="Gerar PDF", on_click=pdf_click),
                            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        )
                    results.controls.append(make())
            page.update()

        def on_search(e):
            q = e.control.value.lower()
            build([r for r in records if q in (r.get("student_name") or "").lower()] if q else records)

        search.on_change = on_search
        build(records)

        render(ft.Container(padding=12, expand=True, content=ft.Column([
            card(ft.Row([ft.Icon(ft.Icons.LIST_ALT, color=P), ft.Text("Registros", size=18, weight=ft.FontWeight.BOLD, color=TX)], spacing=8),
                 ft.Text(f"{len(records)} PEI(s) cadastrado(s)", color=MU, size=13)),
            search,
            results,
            ft.Container(height=20),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)))

    # ── TELA: Painel ──────────────────────────────────────────────────────────
    def show_painel():
        stats = database.get_stats()
        records = database.get_all_pei_records()

        def stat(icon, label, value, color):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, color=color, size=30),
                    ft.Text(str(value), size=30, weight=ft.FontWeight.BOLD, color=TX),
                    ft.Text(label, size=12, color=MU, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                bgcolor=SF, border_radius=14, padding=16, expand=True,
                shadow=ft.BoxShadow(blur_radius=6, color="#00000010", offset=ft.Offset(0,2)),
            )

        recent = ft.Column(spacing=4)
        for r in records[:5]:
            ini = (r.get("student_name") or "?")[0].upper()
            recent.controls.append(ft.ListTile(
                leading=ft.CircleAvatar(content=ft.Text(ini, color="white", weight=ft.FontWeight.BOLD), bgcolor=P, radius=18),
                title=ft.Text(r.get("student_name","—"), weight=ft.FontWeight.W_600, size=14),
                subtitle=ft.Text(r.get("school","—"), color=MU, size=12),
                trailing=ft.Text(str(r.get("created_at",""))[:10], color=MU, size=11),
                content_padding=ft.Padding.symmetric(vertical=0, horizontal=4),
            ))

        render(ft.Container(padding=12, expand=True, content=ft.Column([
            card(ft.Row([ft.Icon(ft.Icons.DASHBOARD, color=P), ft.Text("Painel", size=18, weight=ft.FontWeight.BOLD, color=TX)], spacing=8)),
            ft.Row([
                stat(ft.Icons.DESCRIPTION, "Total de PEIs", stats["total"], P),
                stat(ft.Icons.SCHOOL, "Escolas", stats["schools"], CYAN),
            ], spacing=8),
            ft.Row([stat(ft.Icons.CALENDAR_MONTH, "Este Mês", stats["this_month"], ORANGE)], spacing=8),
            ft.Container(height=4),
            card(
                ft.Text("Recentes", weight=ft.FontWeight.BOLD, color=TX),
                recent if records else ft.Text("Nenhum registro ainda.", color=MU),
            ),
            ft.Container(height=20),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)))

    # ── Navegação ─────────────────────────────────────────────────────────────
    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_OUTLINE, selected_icon=ft.Icons.ADD_CIRCLE, label="Novo PEI"),
            ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT_OUTLINED, selected_icon=ft.Icons.LIST_ALT, label="Registros"),
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Painel"),
        ],
        selected_index=0, bgcolor=SF, indicator_color=PA,
    )

    def on_nav(e):
        [show_novo_pei, show_registros, show_painel][e.control.selected_index]()

    def show_novo_pei():
        if st["step"] == 2 and st["pei_data"]:    show_step2()
        elif st["step"] == 3 and st["saved_id"]:   show_step3()
        else:                                       show_step1()

    nav_bar.on_change = on_nav

    # ── Layout principal ──────────────────────────────────────────────────────
    page.add(ft.Column([
        ft.AppBar(
            title=ft.Text("📋 SIGPEI-IA", weight=ft.FontWeight.BOLD, color="white", size=18),
            bgcolor=P, center_title=True, toolbar_height=56,
        ),
        ft.Container(content=body, expand=True),
        nav_bar,
    ], expand=True, spacing=0))

    show_step1()


ft.run(main, view=ft.AppView.WEB_BROWSER, port=8502)
