import os
import json
import tempfile
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SIGPEI-IA",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paleta de cores ───────────────────────────────────────────────────────────
# Baseado no visual do SIGPEI institucional (sigpei.apps.uern.br): azul-marinho
# como cor estrutural dominante (fundo lavanda claro, cards brancos, ícones em
# círculo, textos e ações em azul); laranja aparece só como toque de marca no
# logotipo "SIGPEI-IA", igual ao "PEI" laranja do logo original — não é
# espalhado pela interface.
NAVY, BLUE, BLUE_LIGHT = "#0f2a5c", "#2563eb", "#dbeafe"
ORANGE = "#f97316"          # só no logotipo
EMERALD = "#10b981"         # só no estado "concluído" (uso semântico)
BG_PAGE = "#eef1f7"         # fundo lavanda claro, como no site institucional
HAB_COLORS = {k: NAVY for k in
              ["cognitiva", "comunicacao", "socializacao", "motora", "autocuidado", "academica"]}

# ── Ícones SVG ────────────────────────────────────────────────────────────────
# Substituem os emojis nos lugares em que o Streamlit permite HTML (títulos,
# cards). Widgets nativos (st.button, st.tabs, st.radio) só aceitam um
# subconjunto seguro de markdown — não renderizam <svg>, então continuam com
# emoji nesses pontos específicos.

def _svg(inner: str, size: int = 20, color: str = NAVY, stroke: float = 2) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:middle">{inner}</svg>'
    )


def icon_clipboard(size=20, color=NAVY):
    return _svg(
        '<rect x="6" y="4" width="12" height="16" rx="2"/>'
        '<rect x="9" y="2.5" width="6" height="3" rx="1"/>'
        '<line x1="9" y1="11" x2="15" y2="11"/>'
        '<line x1="9" y1="15" x2="15" y2="15"/>',
        size, color,
    )


def icon_school(size=20, color=NAVY):
    return _svg(
        '<path d="M12 3 3 8l9 5 9-5-9-5z"/>'
        '<path d="M6 10.5V16c0 1.4 2.7 3 6 3s6-1.6 6-3v-5.5"/>',
        size, color,
    )


def icon_check(size=14, color="#ffffff"):
    return _svg('<polyline points="4 12 9 17 20 6"/>', size, color, stroke=3)


def icon_calendar(size=20, color=NAVY):
    return _svg(
        '<rect x="4" y="5" width="16" height="15" rx="2"/>'
        '<line x1="4" y1="10" x2="20" y2="10"/>'
        '<line x1="8" y1="3" x2="8" y2="6.5"/>'
        '<line x1="16" y1="3" x2="16" y2="6.5"/>',
        size, color,
    )


# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    .stApp {{ background: {BG_PAGE}; font-size: 1.15rem; }}
    html {{ font-size: 18px; }}

    .main-title {{ font-size: 2.1rem; font-weight: 800; margin-bottom: 0; }}
    .main-title .brand-navy   {{ color: {NAVY}; }}
    .main-title .brand-orange {{ color: {ORANGE}; }}
    .sub-title  {{ font-size: 1rem; color: #64748b; margin-top: 0; }}

    .step-row {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }}
    .step-active, .step-done, .step-pending {{ white-space: nowrap; flex: none; }}
    .step-active  {{ background: {BLUE}; color: white;
                     padding: 6px 16px; border-radius: 20px; font-size: .85rem; font-weight: 600; }}
    .step-done    {{ background: {EMERALD}; color: white; padding: 6px 16px;
                     border-radius: 20px; font-size: .85rem; font-weight: 600; }}
    .step-pending {{ background: #e2e8f0; color: #64748b; padding: 6px 16px;
                     border-radius: 20px; font-size: .85rem; }}

    .metric-box {{ background: #ffffff; border-left: 4px solid {BLUE};
                   padding: 12px 16px; border-radius: 10px; margin-bottom: 8px;
                   box-shadow: 0 1px 4px rgba(15,42,92,.08); }}

    /* Etiquetas de seção — chip claro com texto azul-marinho, não bloco sólido */
    .sec-badge {{ display: inline-block; color: {NAVY}; font-weight: 700; font-size: .8rem;
                  letter-spacing: .03em; padding: 6px 14px; border-radius: 8px;
                  margin: 6px 0 10px 0; background: {BLUE_LIGHT}; border-left: 3px solid {BLUE}; }}
    .hab-chip {{ display: inline-block; color: {NAVY}; font-weight: 600; font-size: .72rem;
                 padding: 3px 10px; border-radius: 999px; margin-bottom: 4px;
                 background: {BLUE_LIGHT}; }}

    /* Faixa compacta com os 3 números lado a lado (não 3 cards grandes
       empilhados), no estilo do card "UERN" do site institucional. */
    .stat-row {{ display: flex; gap: 10px; }}
    .stat-card {{ background: #ffffff; border-radius: 14px; padding: 14px 8px;
                  text-align: center; box-shadow: 0 2px 10px rgba(15,42,92,.08);
                  border: 1px solid #e6e9f2; flex: 1; min-width: 0; }}
    .stat-card .stat-icon {{ width: 32px; height: 32px; border-radius: 999px;
                  background: {BLUE_LIGHT}; display: flex; align-items: center;
                  justify-content: center; margin: 0 auto 6px; font-size: 1rem; }}
    .stat-card .stat-value {{ font-size: 1.4rem; font-weight: 800; color: {NAVY}; }}
    .stat-card .stat-label {{ font-size: .68rem; color: #64748b; line-height: 1.2; }}

    /* Botões — azul-marinho como cor de ação (laranja fica só no logotipo) */
    .stButton > button[kind="primary"] {{
        background: {BLUE}; border: none; color: white; font-weight: 700;
    }}
    .stButton > button[kind="primary"]:hover {{ background: {NAVY}; }}
    .stButton > button:not([kind="primary"]) {{ border-color: #cbd5e1; color: {NAVY}; }}

    /* Abas (voz / texto / documentos) */
    .stTabs [data-baseweb="tab-list"] {{ gap: 32px; }}
    .stTabs [data-baseweb="tab"] {{ padding-left: 4px; padding-right: 4px; }}
    .stTabs [aria-selected="true"] {{ color: {NAVY} !important; font-weight: 700; }}
    .stTabs [data-baseweb="tab-highlight"] {{ background: {BLUE} !important; }}

    /* Caixas de texto — contorno visível (o padrão do Streamlit é sem borda) */
    [data-testid="stTextInput"] div[data-baseweb="input"],
    [data-testid="stTextArea"] div[data-baseweb="textarea"],
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 8px !important;
        background: #ffffff !important;
    }}
    [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
    [data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {{
        border-color: {BLUE} !important;
    }}

    /* Barra superior do Streamlit — transparente, para não formar uma faixa
       de cor diferente do resto do fundo no topo da página. */
    [data-testid="stHeader"] {{ background: transparent !important; }}

    /* Componente do microfone (audio_recorder_streamlit) — por padrão o
       Streamlit estica o <iframe> dele para 100% da largura do container,
       o que faz o botão pequeno virar uma barra branca enorme e esquisita.
       Aqui só limito a largura ao tamanho real do conteúdo, sem adicionar
       nenhuma borda/moldura por cima — o componente já desenha o próprio
       botão arredondado sozinho. */
    [data-testid="stCustomComponentV1"] {{ max-width: 230px; }}
    [data-testid="stCustomComponentV1"] iframe {{ border: none !important; }}

    /* Barra lateral — branca e neutra, com uma faixa azul-marinho decorativa
       na borda (como a faixa vertical do site institucional), sem pintar o
       fundo inteiro — assim o texto continua com a cor padrão do Streamlit,
       sem precisar forçar contraste. */
    [data-testid="stSidebar"] {{
        background: #ffffff;
        box-shadow: inset 12px 0 0 0 {NAVY};
    }}

    /* ── Responsividade ──────────────────────────────────────────────────
       O layout de colunas do Streamlit (st.columns) já empilha sozinho em
       telas estreitas; aqui só ajusto o que EU adicionei (fontes, cards,
       espaçamentos fixos) para não estourar/ficar apertado em tablet/celular. */
    @media (max-width: 900px) {{
        [data-testid="stCustomComponentV1"] {{ max-width: 100%; }}
    }}

    @media (max-width: 640px) {{
        html {{ font-size: 16px; }}
        .stApp {{ font-size: 1rem; }}
        .main-title {{ font-size: 1.5rem; }}
        .sub-title  {{ font-size: .85rem; }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px; flex-wrap: nowrap; overflow-x: auto;
        }}
        .stTabs [data-baseweb="tab"] {{ font-size: .82rem; flex: none; }}
        .sec-badge {{ font-size: .72rem; padding: 5px 10px; }}
        [data-testid="stSidebar"] {{ box-shadow: inset 6px 0 0 0 {NAVY}; }}
        [data-testid="stHorizontalBlock"] {{ flex-direction: column; }}
        [data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; }}
    }}

    /* Nunca deixar nada forçar rolagem horizontal na página inteira */
    .stApp, .main .block-container {{ overflow-x: hidden; max-width: 100vw; }}
    img, svg, iframe {{ max-width: 100%; }}
</style>
""", unsafe_allow_html=True)

# ── Lazy imports ─────────────────────────────────────────────────────────────
import database
import ai_processor
import pei_generator

database.init_db()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _patch_audio_recorder_bg():
    """audio_recorder_streamlit roda num <iframe>; o HTML dele vem com fundo
    branco fixo, que não dá pra sobrescrever via CSS da página (documentos
    diferentes). Em vez de deixar isso como um passo manual que se perde a
    cada `uv sync`, o app corrige o próprio arquivo instalado sozinho, de
    forma idempotente (só mexe se a correção ainda não estiver lá)."""
    try:
        import audio_recorder_streamlit
        index_path = os.path.join(
            os.path.dirname(audio_recorder_streamlit.__file__),
            "frontend", "build", "index.html",
        )
        marker = "background:transparent!important"
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        if marker not in html:
            style_tag = (
                "<style>"
                f"html,body{{{marker};background-color:transparent!important}}"
                "</style></head>"
            )
            patched = html.replace("</head>", style_tag, 1)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(patched)
    except Exception:
        pass  # correção cosmética — nunca deve travar o app


def extract_text_from_file(f) -> str:
    name = f.name.lower()
    try:
        if name.endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(f) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
        if name.endswith(".docx"):
            from docx import Document
            doc = Document(f)
            return "\n".join(p.text for p in doc.paragraphs).strip()
        if name.endswith(".txt"):
            return f.read().decode("utf-8", errors="ignore").strip()
        if name.endswith((".png", ".jpg", ".jpeg")):
            try:
                import pytesseract
                from PIL import Image
                return pytesseract.image_to_string(Image.open(f), lang="por").strip()
            except Exception:
                st.warning(f"OCR indisponível para {f.name}. Instale pytesseract + Tesseract.")
    except Exception as e:
        st.warning(f"Erro ao processar {f.name}: {e}")
    return ""


def transcribe_audio(audio_bytes: bytes) -> str:
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with sr.AudioFile(tmp_path) as src:
            audio_data = recognizer.record(src)
        os.unlink(tmp_path)
        return recognizer.recognize_google(audio_data, language="pt-BR")
    except Exception as e:
        return f"ERRO: {e}"


def _ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _clear_pei():
    for k in ["pei_data", "confirmed", "doc_texts", "raw_input",
              "saved_pei_id", "final_student", "final_pei"]:
        st.session_state.pop(k, None)


def sec_badge(text: str):
    st.markdown(f'<span class="sec-badge">{text}</span>', unsafe_allow_html=True)


def hab_label(text: str, key: str):
    st.markdown(f'<span class="hab-chip">{text}</span>', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown(
            f'<p class="main-title">{icon_clipboard(26, NAVY)} <span class="brand-navy">SIGPEI</span>'
            '<span class="brand-orange">-IA</span></p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="sub-title">Sistema Inteligente de Gestão do PEI</p>', unsafe_allow_html=True)
        st.divider()
        page = st.radio(
            "Menu",
            [":material/edit_note: Novo PEI", ":material/inventory_2: Registros", ":material/bar_chart: Painel"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("**Como usar:**")
        st.markdown("1. Fale, escreva ou carregue documentos\n2. Confirme os dados extraídos\n3. Salve e exporte o PEI em PDF")

        configured = [
            name for name, key in [
                ("Groq", os.getenv("GROQ_API_KEY")),
                ("Mistral", os.getenv("MISTRAL_API_KEY")),
                ("OpenRouter", os.getenv("OPENROUTER_API_KEY")),
            ] if key
        ]
        if configured:
            st.success(f"IA em nuvem conectada ✓ ({', '.join(configured)})")
        else:
            st.error("Nenhuma chave de IA configurada — veja o .env.example")
    return page


# ── Step indicator ────────────────────────────────────────────────────────────

def _step_indicator(current: int):
    # HTML/flex próprio (não st.columns) — continua em linha em qualquer
    # largura de tela, com rolagem horizontal como saída de emergência em
    # telas muito estreitas, em vez de empilhar verticalmente.
    labels = ["1 · Entrada", "2 · Confirmação", "3 · Salvar"]
    spans = []
    for i, lbl in enumerate(labels):
        if i + 1 < current:
            spans.append(f'<span class="step-done">{icon_check()} {lbl}</span>')
        elif i + 1 == current:
            spans.append(f'<span class="step-active">{lbl}</span>')
        else:
            spans.append(f'<span class="step-pending">{lbl}</span>')
    st.markdown(
        '<div class="step-row">' + "".join(spans) + "</div>",
        unsafe_allow_html=True,
    )
    st.divider()


# ── Page: Novo PEI ────────────────────────────────────────────────────────────

def page_novo_pei():
    st.markdown("## Novo Plano Educacional Individualizado")

    _ss("doc_texts", [])
    _ss("pei_data", None)
    _ss("confirmed", False)

    confirmed = st.session_state.confirmed
    pei_data = st.session_state.pei_data

    if confirmed:
        step = 3
    elif pei_data:
        step = 2
    else:
        step = 1

    _step_indicator(step)

    # ── Step 1 ────────────────────────────────────────────────────────────────
    if step == 1:
        st.subheader("Forneça as informações do aluno")
        tab_voice, tab_text, tab_doc = st.tabs([
            ":material/mic: Gravar voz",
            ":material/keyboard: Digitar texto",
            ":material/description: Carregar documentos",
        ])

        with tab_voice:
            st.info("Fale livremente sobre o aluno: nome, diagnóstico, habilidades, objetivos e estratégias.")
            recorder_available = False
            try:
                from audio_recorder_streamlit import audio_recorder
                _patch_audio_recorder_bg()
                recorder_available = True
            except ImportError:
                pass

            if recorder_available:
                audio_bytes = audio_recorder(
                    text="Clique para gravar",
                    recording_color="#e53e3e",
                    neutral_color=NAVY,
                    icon_name="microphone",
                    icon_size="2x",
                    pause_threshold=2.5,
                )
                if audio_bytes and len(audio_bytes) > 1000:
                    st.audio(audio_bytes, format="audio/wav")
                    with st.spinner("Transcrevendo..."):
                        raw = transcribe_audio(audio_bytes)
                    if raw.startswith("ERRO"):
                        st.error(raw)
                    else:
                        with st.spinner("Aprimorando com IA..."):
                            improved = ai_processor.improve_transcription(raw)
                        st.text_area(
                            "Transcrição (edite se necessário):",
                            value=improved,
                            height=160,
                            key="voice_text",
                        )
            else:
                st.warning("Instale `audio-recorder-streamlit` para gravar diretamente. Por enquanto, carregue um arquivo de áudio.")
                audio_file = st.file_uploader("Arquivo de áudio (WAV):", type=["wav"], key="audio_up")
                if audio_file:
                    with st.spinner("Transcrevendo..."):
                        raw = transcribe_audio(audio_file.read())
                    if not raw.startswith("ERRO"):
                        st.text_area("Transcrição:", value=raw, height=160, key="voice_text2")
                    else:
                        st.error(raw)

        with tab_text:
            st.markdown("""Escreva livremente. Inclua tudo que souber:
- Nome, data de nascimento, escola, série
- Diagnóstico (ex: TEA, TDAH, DI) e CID
- Habilidades atuais em diferentes áreas
- Objetivos e estratégias pedagógicas""")
            st.text_area(
                "Informações do aluno:",
                height=260,
                placeholder=(
                    "Ex: João da Silva, nascido em 10/03/2017, aluno do 2º ano B da EMEF Monteiro Lobato, "
                    "turno matutino. Diagnóstico de TEA nível 2 (CID F84.0). "
                    "Tem comunicação funcional limitada, usa CAA. Bom desempenho em atividades visuais. "
                    "Objetivo: ampliar vocabulário funcional para 50 palavras até dezembro..."
                ),
                key="main_text",
            )

        with tab_doc:
            st.markdown("Suporta: **PDF, DOCX, TXT, PNG, JPG**")
            files = st.file_uploader(
                "Selecione arquivos:",
                type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
                key="docs",
            )
            if files:
                doc_texts = []
                for f in files:
                    with st.spinner(f"Processando {f.name}..."):
                        text = extract_text_from_file(f)
                    if text:
                        doc_texts.append(f"[Arquivo: {f.name}]\n{text}")
                        st.success(f"✓ {f.name} — {len(text):,} caracteres extraídos")
                    else:
                        st.warning(f"⚠ {f.name} — sem texto")
                st.session_state.doc_texts = doc_texts
                if doc_texts:
                    with st.expander("Prévia do texto extraído"):
                        for dt in doc_texts:
                            st.text(dt[:600] + ("…" if len(dt) > 600 else ""))
                            st.divider()

        st.divider()
        voice_part = st.session_state.get("voice_text") or st.session_state.get("voice_text2") or ""
        text_part = st.session_state.get("main_text") or ""
        all_parts = [p for p in [voice_part, text_part] if p.strip()] + st.session_state.doc_texts

        if all_parts:
            st.success(f"{len(all_parts)} fonte(s) disponível(is) para análise.")
            if st.button("Analisar com IA e extrair campos do PEI", icon=":material/smart_toy:",
                         type="primary", use_container_width=True):
                full_text = "\n\n".join(all_parts)
                with st.spinner("Analisando com IA… aguarde alguns segundos."):
                    try:
                        pei_data = ai_processor.extract_pei_info(full_text)
                        st.session_state.pei_data = pei_data
                        st.session_state.raw_input = full_text
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro na análise: {e}")
                        st.info("Verifique se ao menos uma chave de IA está configurada no .env.")
        else:
            st.info("Forneça informações via voz, texto ou documentos para continuar.")

    # ── Step 2 ────────────────────────────────────────────────────────────────
    elif step == 2:
        st.subheader("Revise e confirme os dados extraídos pela IA")
        st.info("Edite qualquer campo abaixo antes de salvar. Campos obrigatórios marcados com *")

        pei = st.session_state.pei_data

        with st.form("pei_form", clear_on_submit=False):
            # Identificação
            sec_badge("IDENTIFICAÇÃO DO ALUNO")
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome Completo *", value=pei.get("nome") or "")
                data_nasc = st.text_input("Data de Nascimento", value=pei.get("data_nascimento") or "")
                escola = st.text_input("Escola", value=pei.get("escola") or "")
                serie = st.text_input("Série/Ano", value=pei.get("serie") or "")
            with c2:
                turma = st.text_input("Turma", value=pei.get("turma") or "")
                turno_opts = ["", "Matutino", "Vespertino", "Noturno", "Integral"]
                turno_val = pei.get("turno") or ""
                turno_idx = turno_opts.index(turno_val) if turno_val in turno_opts else 0
                turno = st.selectbox("Turno", turno_opts, index=turno_idx)
                diagnostico = st.text_input("Diagnóstico", value=pei.get("diagnostico") or "")
                cid = st.text_input("CID-10", value=pei.get("cid") or "")

            st.divider()
            sec_badge("EQUIPE")
            c3, c4 = st.columns(2)
            with c3:
                professor = st.text_input("Professor(a) Responsável", value=pei.get("professor") or "")
                equipe_str = st.text_area(
                    "Equipe Multidisciplinar (um por linha)",
                    value="\n".join(pei.get("equipe") or []),
                    height=80,
                )
            with c4:
                data_elab = st.text_input("Data de Elaboração", value=pei.get("data_elaboracao") or datetime.now().strftime("%d/%m/%Y"))
                data_rev = st.text_input("Data de Revisão Prevista", value=pei.get("data_revisao") or "")

            st.divider()
            sec_badge("HABILIDADES ATUAIS")
            hab = pei.get("habilidades_atuais") or {}
            c5, c6 = st.columns(2)
            with c5:
                hab_label("Cognitiva", "cognitiva")
                h_cog  = st.text_area("Cognitiva", value=hab.get("cognitiva") or "", height=90, label_visibility="collapsed")
                hab_label("Comunicação/Linguagem", "comunicacao")
                h_com  = st.text_area("Comunicação/Linguagem", value=hab.get("comunicacao") or "", height=90, label_visibility="collapsed")
                hab_label("Socialização", "socializacao")
                h_soc  = st.text_area("Socialização", value=hab.get("socializacao") or "", height=90, label_visibility="collapsed")
            with c6:
                hab_label("Motora", "motora")
                h_mot  = st.text_area("Motora", value=hab.get("motora") or "", height=90, label_visibility="collapsed")
                hab_label("Autocuidado", "autocuidado")
                h_auto = st.text_area("Autocuidado", value=hab.get("autocuidado") or "", height=90, label_visibility="collapsed")
                hab_label("Acadêmica", "academica")
                h_acad = st.text_area("Acadêmica", value=hab.get("academica") or "", height=90, label_visibility="collapsed")

            st.divider()
            sec_badge("OBJETIVOS")
            long_goals_str = st.text_area(
                "Objetivos de Longo Prazo (um por linha)",
                value="\n".join(pei.get("objetivos_longo_prazo") or []),
                height=90,
            )
            st.markdown("**Objetivos de Curto Prazo** — formato: `Objetivo | Critério | Prazo` (um por linha)")
            short_raw = pei.get("objetivos_curto_prazo") or []
            short_lines = []
            for g in short_raw:
                if isinstance(g, dict):
                    short_lines.append(f"{g.get('objetivo','')} | {g.get('criterio','')} | {g.get('prazo','')}")
                else:
                    short_lines.append(str(g))
            short_goals_str = st.text_area("Objetivos de curto prazo:", value="\n".join(short_lines), height=90)

            st.divider()
            sec_badge("ESTRATÉGIAS, ADAPTAÇÕES E SERVIÇOS")
            c7, c8 = st.columns(2)
            with c7:
                estrategias_str = st.text_area(
                    "Estratégias Pedagógicas (uma por linha)",
                    value="\n".join(pei.get("estrategias") or []),
                    height=100,
                )
                adaptacoes_str = st.text_area(
                    "Adaptações Curriculares (uma por linha)",
                    value="\n".join(pei.get("adaptacoes_curriculares") or []),
                    height=100,
                )
            with c8:
                servicos_str = st.text_area(
                    "Serviços de Apoio (um por linha)",
                    value="\n".join(pei.get("servicos_apoio") or []),
                    height=100,
                )
                avaliacao = st.text_area(
                    "Método de Avaliação",
                    value=pei.get("avaliacao") or "",
                    height=100,
                )

            st.divider()
            b1, b2 = st.columns(2)
            with b1:
                voltar = st.form_submit_button("Voltar", icon=":material/arrow_back:", use_container_width=True)
            with b2:
                salvar = st.form_submit_button("Confirmar e Salvar", icon=":material/check_circle:",
                                                type="primary", use_container_width=True)

            if voltar:
                st.session_state.pei_data = None
                st.rerun()

            if salvar:
                if not nome.strip():
                    st.error("O nome do aluno é obrigatório.")
                else:
                    # Parse short-term goals
                    short_goals_parsed = []
                    for line in short_goals_str.strip().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        if "|" in line:
                            parts = [p.strip() for p in line.split("|")]
                            short_goals_parsed.append({
                                "objetivo": parts[0],
                                "criterio": parts[1] if len(parts) > 1 else "",
                                "prazo": parts[2] if len(parts) > 2 else "",
                            })
                        else:
                            short_goals_parsed.append({"objetivo": line, "criterio": "", "prazo": ""})

                    def split_lines(s):
                        return [l.strip() for l in s.strip().splitlines() if l.strip()]

                    student_data = {
                        "nome": nome.strip(), "data_nascimento": data_nasc,
                        "escola": escola, "serie": serie, "turma": turma,
                        "turno": turno, "diagnostico": diagnostico, "cid": cid,
                    }
                    final_pei = {
                        "professor": professor,
                        "equipe": split_lines(equipe_str),
                        "habilidades_atuais": {
                            "cognitiva": h_cog, "comunicacao": h_com,
                            "socializacao": h_soc, "motora": h_mot,
                            "autocuidado": h_auto, "academica": h_acad,
                        },
                        "objetivos_longo_prazo": split_lines(long_goals_str),
                        "objetivos_curto_prazo": short_goals_parsed,
                        "estrategias": split_lines(estrategias_str),
                        "adaptacoes_curriculares": split_lines(adaptacoes_str),
                        "servicos_apoio": split_lines(servicos_str),
                        "avaliacao": avaliacao,
                        "data_elaboracao": data_elab,
                        "data_revisao": data_rev,
                        "raw_input": st.session_state.get("raw_input", ""),
                    }

                    try:
                        sid = database.save_student(student_data)
                        pid = database.save_pei(final_pei, sid)
                        for dt in st.session_state.get("doc_texts", []):
                            doc_name = dt.split("\n")[0].replace("[Arquivo: ", "").replace("]", "")
                            database.save_document(pid, doc_name, "document", dt)

                        st.session_state.confirmed = True
                        st.session_state.saved_pei_id = pid
                        st.session_state.final_student = student_data
                        st.session_state.final_pei = final_pei
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    # ── Step 3 ────────────────────────────────────────────────────────────────
    elif step == 3:
        student_name = st.session_state.get("final_student", {}).get("nome", "Aluno")
        pid = st.session_state.get("saved_pei_id", "")

        st.success(f"PEI de **{student_name}** salvo com sucesso! (ID #{pid})")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Gerar e Baixar PDF", icon=":material/picture_as_pdf:",
                         type="primary", use_container_width=True):
                with st.spinner("Gerando PDF..."):
                    try:
                        s = st.session_state.final_student
                        student_map = {
                            "name": s.get("nome"), "birth_date": s.get("data_nascimento"),
                            "school": s.get("escola"), "grade": s.get("serie"),
                            "classroom": s.get("turma"), "shift": s.get("turno"),
                            "diagnosis": s.get("diagnostico"), "cid": s.get("cid"),
                        }
                        pdf_bytes = pei_generator.generate_pei_pdf(student_map, st.session_state.final_pei)
                        fname = f"PEI_{student_name.replace(' ','_')}_{datetime.now():%Y%m%d}.pdf"
                        st.download_button("Clique para baixar", pdf_bytes, fname, "application/pdf",
                                            icon=":material/download:", use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
        with c2:
            if st.button("Ver todos os registros", icon=":material/inventory_2:", use_container_width=True):
                _clear_pei()
                st.session_state["_goto"] = "records"
                st.rerun()
        with c3:
            if st.button("Criar novo PEI", icon=":material/add:", use_container_width=True):
                _clear_pei()
                st.rerun()

        with st.expander("Visualizar dados salvos (JSON)"):
            st.json(st.session_state.final_pei)


# ── Page: Registros ───────────────────────────────────────────────────────────

def page_registros():
    st.markdown("## Registros de PEIs")

    records = database.get_all_pei_records()
    if not records:
        st.info("Nenhum PEI registrado ainda.")
        return

    search = st.text_input("Buscar por nome do aluno:", icon=":material/search:")
    if search:
        records = [r for r in records if search.lower() in (r.get("student_name") or "").lower()]

    st.markdown(f"**{len(records)} registro(s) encontrado(s)**")

    for r in records:
        with st.expander(
            f"{r.get('student_name','—')}  ·  {r.get('school','—')}  ·  {str(r.get('elaboration_date') or r.get('created_at',''))[:10]}",
            icon=":material/description:",
        ):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Escola:** {r.get('school','—')}")
            c2.markdown(f"**Série:** {r.get('grade','—')}")
            c3.markdown(f"**Diagnóstico:** {r.get('diagnosis','—')}")

            if st.button("Gerar PDF deste PEI", icon=":material/picture_as_pdf:", key=f"pdf_{r['id']}"):
                full = database.get_pei_by_id(r["id"])
                if full:
                    with st.spinner("Gerando PDF..."):
                        try:
                            student_map = {
                                "name": full.get("student_name"), "birth_date": full.get("birth_date"),
                                "school": full.get("school"), "grade": full.get("grade"),
                                "classroom": full.get("classroom"), "shift": full.get("shift"),
                                "diagnosis": full.get("diagnosis"), "cid": full.get("cid"),
                            }
                            pei_map = {
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
                            pdf = pei_generator.generate_pei_pdf(student_map, pei_map)
                            fname = f"PEI_{(full.get('student_name') or 'aluno').replace(' ','_')}.pdf"
                            st.download_button("Baixar PDF", pdf, fname, "application/pdf",
                                                icon=":material/download:", key=f"dl_{r['id']}")
                        except Exception as e:
                            st.error(f"Erro: {e}")


# ── Page: Painel ─────────────────────────────────────────────────────────────

def page_painel():
    st.markdown("## Painel de Acompanhamento")

    stats = database.get_stats()

    def stat_card(icon, label, value):
        return f"""
        <div class="stat-card">
            <div class="stat-icon">{icon}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-label">{label}</div>
        </div>
        """

    # HTML/flex próprio (não st.columns) — os 3 fica lado a lado numa faixa
    # compacta em qualquer largura de tela, em vez de 3 cards grandes
    # empilhados no celular.
    st.markdown(
        '<div class="stat-row">'
        + stat_card(icon_clipboard(20, BLUE), "Total de PEIs", stats["total"])
        + stat_card(icon_school(20, BLUE), "Escolas Atendidas", stats["schools"])
        + stat_card(icon_calendar(20, BLUE), "PEIs este Mês", stats["this_month"])
        + "</div>",
        unsafe_allow_html=True,
    )

    records = database.get_all_pei_records()
    if not records:
        st.info("Nenhum registro ainda.")
        return

    st.divider()
    st.subheader("Registros Recentes")

    try:
        import pandas as pd
        df = pd.DataFrame([{
            "ID": r["id"],
            "Aluno": r.get("student_name", ""),
            "Escola": r.get("school", ""),
            "Série": r.get("grade", ""),
            "Diagnóstico": r.get("diagnosis", ""),
            "Data": str(r.get("elaboration_date") or r.get("created_at", ""))[:10],
        } for r in records])
        st.dataframe(df, use_container_width=True, hide_index=True)
    except ImportError:
        for r in records:
            st.markdown(f"- **{r.get('student_name')}** — {r.get('school')} — {str(r.get('created_at',''))[:10]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    page = sidebar()

    goto = st.session_state.pop("_goto", None)
    if goto == "records":
        page = ":material/inventory_2: Registros"

    if "Novo PEI" in page:
        page_novo_pei()
    elif "Registros" in page:
        page_registros()
    else:
        page_painel()


if __name__ == "__main__":
    main()
