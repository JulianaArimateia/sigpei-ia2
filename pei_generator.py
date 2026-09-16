from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

_BLUE = colors.HexColor("#2c5282")
_LIGHT = colors.HexColor("#edf2f7")
_BORDER = colors.HexColor("#e2e8f0")
_GRAY = colors.HexColor("#718096")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T", parent=base["Normal"], fontSize=18,
                                 alignment=TA_CENTER, textColor=_BLUE,
                                 fontName="Helvetica-Bold", spaceAfter=2),
        "subtitle": ParagraphStyle("S", parent=base["Normal"], fontSize=11,
                                    alignment=TA_CENTER, textColor=_GRAY,
                                    spaceAfter=4),
        "section": ParagraphStyle("SEC", parent=base["Normal"], fontSize=10,
                                   fontName="Helvetica-Bold", textColor=colors.white,
                                   backColor=_BLUE, leftIndent=-6, rightIndent=-6,
                                   borderPad=5, spaceBefore=10, spaceAfter=4),
        "label": ParagraphStyle("LB", parent=base["Normal"], fontSize=8,
                                  textColor=_GRAY, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("BD", parent=base["Normal"], fontSize=9,
                                spaceAfter=3, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("BU", parent=base["Normal"], fontSize=9,
                                  leftIndent=12, spaceAfter=2),
        "footer": ParagraphStyle("FT", parent=base["Normal"], fontSize=7,
                                   alignment=TA_CENTER, textColor=_GRAY),
    }


def _row(label, value, label2="", value2=""):
    return [
        Paragraph(f"<b>{label}</b>", ParagraphStyle("x", fontSize=8, textColor=_GRAY, fontName="Helvetica-Bold")),
        Paragraph(str(value or ""), ParagraphStyle("x", fontSize=9)),
        Paragraph(f"<b>{label2}</b>", ParagraphStyle("x", fontSize=8, textColor=_GRAY, fontName="Helvetica-Bold")),
        Paragraph(str(value2 or ""), ParagraphStyle("x", fontSize=9)),
    ]


def generate_pei_pdf(student: dict, pei: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    st = _styles()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story += [
        Paragraph("PLANO EDUCACIONAL INDIVIDUALIZADO", st["title"]),
        Paragraph("PEI — Educação Inclusiva", st["subtitle"]),
        HRFlowable(width="100%", thickness=2, color=_BLUE),
        Spacer(1, 0.4*cm),
    ]

    # ── 1. Identificação ────────────────────────────────────────────────────
    story.append(Paragraph("1. IDENTIFICAÇÃO DO ALUNO", st["section"]))
    id_table = Table(
        [
            _row("Nome Completo", student.get("name"), "Data de Nascimento", student.get("birth_date")),
            _row("Escola", student.get("school"), "Série/Ano", student.get("grade")),
            _row("Turma", student.get("classroom"), "Turno", student.get("shift")),
            _row("Diagnóstico", student.get("diagnosis"), "CID-10", student.get("cid")),
            _row("Professor(a)", pei.get("professor"),
                 "Data de Elaboração", pei.get("data_elaboracao")),
        ],
        colWidths=[3.5*cm, 6.5*cm, 3.5*cm, 3.5*cm],
    )
    id_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("BACKGROUND", (0, 0), (0, -1), _LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), _LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(id_table)

    team = pei.get("equipe") or []
    if team:
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(f"<b>Equipe Multidisciplinar:</b> {', '.join(team)}", st["body"]))

    # ── 2. Habilidades Atuais ───────────────────────────────────────────────
    story.append(Paragraph("2. AVALIAÇÃO DAS HABILIDADES ATUAIS", st["section"]))
    areas = [
        ("Cognitiva", "cognitiva"), ("Comunicação / Linguagem", "comunicacao"),
        ("Socialização", "socializacao"), ("Motora", "motora"),
        ("Autocuidado", "autocuidado"), ("Acadêmica", "academica"),
    ]
    hab = pei.get("habilidades_atuais") or {}
    hab_rows = []
    for label, key in areas:
        value = hab.get(key) or "Não avaliado"
        hab_rows.append([
            Paragraph(f"<b>{label}</b>", ParagraphStyle("x", fontSize=8, fontName="Helvetica-Bold", textColor=_GRAY)),
            Paragraph(value, ParagraphStyle("x", fontSize=9)),
        ])
    hab_table = Table(hab_rows, colWidths=[4.5*cm, 12.5*cm])
    hab_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("BACKGROUND", (0, 0), (0, -1), _LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(hab_table)

    # ── 3. Objetivos ────────────────────────────────────────────────────────
    story.append(Paragraph("3. OBJETIVOS", st["section"]))

    long_goals = pei.get("objetivos_longo_prazo") or []
    if long_goals:
        story.append(Paragraph("<b>Objetivos de Longo Prazo:</b>", st["body"]))
        for i, g in enumerate(long_goals, 1):
            story.append(Paragraph(f"{i}. {g}", st["bullet"]))

    short_goals = pei.get("objetivos_curto_prazo") or []
    if short_goals:
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("<b>Objetivos de Curto Prazo:</b>", st["body"]))
        header = [
            Paragraph("<b>Objetivo</b>", ParagraphStyle("x", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
            Paragraph("<b>Critério de Avaliação</b>", ParagraphStyle("x", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
            Paragraph("<b>Prazo</b>", ParagraphStyle("x", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
        ]
        rows = [header]
        for g in short_goals:
            if isinstance(g, dict):
                rows.append([
                    Paragraph(g.get("objetivo", ""), ParagraphStyle("x", fontSize=9)),
                    Paragraph(g.get("criterio", ""), ParagraphStyle("x", fontSize=9)),
                    Paragraph(g.get("prazo", ""), ParagraphStyle("x", fontSize=9)),
                ])
            else:
                rows.append([Paragraph(str(g), ParagraphStyle("x", fontSize=9)), Paragraph("", ParagraphStyle("x")), Paragraph("", ParagraphStyle("x"))])
        sg_table = Table(rows, colWidths=[7*cm, 6.5*cm, 3.5*cm])
        sg_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _BLUE),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
        ]))
        story.append(sg_table)

    # ── 4. Estratégias ──────────────────────────────────────────────────────
    story.append(Paragraph("4. ESTRATÉGIAS E ADAPTAÇÕES", st["section"]))
    strategies = pei.get("estrategias") or []
    if strategies:
        story.append(Paragraph("<b>Estratégias Pedagógicas:</b>", st["body"]))
        for s in strategies:
            story.append(Paragraph(f"• {s}", st["bullet"]))

    adaptations = pei.get("adaptacoes_curriculares") or []
    if adaptations:
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("<b>Adaptações Curriculares:</b>", st["body"]))
        for a in adaptations:
            story.append(Paragraph(f"• {a}", st["bullet"]))

    # ── 5. Serviços ─────────────────────────────────────────────────────────
    story.append(Paragraph("5. SERVIÇOS DE APOIO", st["section"]))
    services = pei.get("servicos_apoio") or []
    if services:
        for s in services:
            story.append(Paragraph(f"• {s}", st["bullet"]))
    else:
        story.append(Paragraph("Não especificado.", st["body"]))

    # ── 6. Avaliação ────────────────────────────────────────────────────────
    story.append(Paragraph("6. AVALIAÇÃO E ACOMPANHAMENTO", st["section"]))
    evaluation = pei.get("avaliacao") or "A ser definido pela equipe pedagógica."
    story.append(Paragraph(evaluation, st["body"]))
    review = pei.get("data_revisao")
    if review:
        story.append(Paragraph(f"<b>Data prevista para revisão:</b> {review}", st["body"]))

    # ── 7. Assinaturas ──────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("7. ASSINATURAS", st["section"]))
    story.append(Spacer(1, 0.8*cm))

    sig_rows = [
        ["_" * 32, "_" * 32, "_" * 32],
        ["Professor(a) Responsável", "Coordenador(a) Pedagógico(a)", "Responsável pelo Aluno"],
    ]
    sig_table = Table(sig_rows, colWidths=[5.5*cm, 6*cm, 5.5*cm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("TEXTCOLOR", (0, 1), (-1, 1), _GRAY),
    ]))
    story.append(sig_table)

    # ── Footer ───────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=0.5, color=_BORDER),
        Paragraph(
            f"Documento gerado pelo SIGPEI-IA em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            st["footer"],
        ),
    ]

    doc.build(story)
    return buf.getvalue()
