import os
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
ASSETS_DIR = os.path.join(DOCS_DIR, "assets")
PDF_PATH = os.path.join(DOCS_DIR, "Documentacao_Engenharia_Software.pdf")


def _draw_box(ax, x, y, w, h, text, color):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.03",
        linewidth=1.2,
        edgecolor="#0f172a",
        facecolor=color,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, wrap=True)


def generate_visual_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1) Arquitetura
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    _draw_box(ax, 0.02, 0.55, 0.17, 0.28, "Frontend Web\n(Django Templates + JS)", "#dbeafe")
    _draw_box(ax, 0.22, 0.55, 0.17, 0.28, "Camada de Views\n(DRF + Django Views)", "#dcfce7")
    _draw_box(ax, 0.42, 0.55, 0.17, 0.28, "IA / Pipeline\nScoring local + GPT", "#ede9fe")
    _draw_box(ax, 0.62, 0.55, 0.17, 0.28, "Video IA\nD-ID/local/hibrido", "#fee2e2")
    _draw_box(ax, 0.82, 0.55, 0.16, 0.28, "Persistencia\nSQLite/PostgreSQL", "#fde68a")
    _draw_box(ax, 0.27, 0.12, 0.2, 0.25, "Exportacao PDF\nrelatorio + pitch deck", "#fef3c7")
    _draw_box(ax, 0.54, 0.12, 0.2, 0.25, "Gestao de Modelos\nTreino + progresso realtime", "#ccfbf1")
    ax.annotate("", xy=(0.28, 0.69), xytext=(0.23, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.42, 0.69), xytext=(0.39, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.62, 0.69), xytext=(0.59, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.82, 0.69), xytext=(0.79, 0.69), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.36, 0.37), xytext=(0.46, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.63, 0.37), xytext=(0.63, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Arquitetura da Plataforma", fontsize=12, weight="bold")
    architecture_path = os.path.join(ASSETS_DIR, "arquitetura_plataforma.png")
    fig.tight_layout()
    fig.savefig(architecture_path, dpi=140)
    plt.close(fig)

    # 2) Fluxo de negocio
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    steps = [
        (0.05, 0.72, "1. Submissao multimodal\n(texto/doc/audio/video/youtube)"),
        (0.30, 0.72, "2. Extracao de features\ntexto + audio + video + financeiro"),
        (0.55, 0.72, "3. Scoring IA\nmotor local ou GPT"),
        (0.80, 0.72, "4. Relatorio automatico\ncategorias 0-10"),
        (0.30, 0.30, "5. Persistencia\nhistorico e metadados"),
        (0.60, 0.30, "6. Dashboard + PDF\nprogresso e benchmark"),
    ]
    for x, y, text in steps:
        _draw_box(ax, x, y, 0.17, 0.18, text, "#e2e8f0")
    arrows = [
        ((0.22, 0.81), (0.30, 0.81)),
        ((0.47, 0.81), (0.55, 0.81)),
        ((0.72, 0.81), (0.80, 0.81)),
        ((0.88, 0.72), (0.70, 0.40)),
        ((0.47, 0.39), (0.60, 0.39)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Fluxo funcional do projeto", fontsize=12, weight="bold")
    flow_path = os.path.join(ASSETS_DIR, "fluxo_funcional.png")
    fig.tight_layout()
    fig.savefig(flow_path, dpi=140)
    plt.close(fig)

    # 3) Exemplo visual de categorias
    categories = [
        "Clareza",
        "Valor",
        "Inovacao",
        "Viabilidade",
        "Escalabilidade",
        "Mercado",
        "Equipe",
        "Sustentabilidade",
    ]
    values = [7.8, 8.2, 7.4, 6.9, 7.1, 7.6, 6.8, 7.3]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(categories, values, color="#2563eb")
    ax.set_ylim(0, 10)
    ax.set_ylabel("Nota")
    ax.set_title("Exemplo de notas por categoria (0-10)")
    ax.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.12, f"{val:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    categories_path = os.path.join(ASSETS_DIR, "categorias_exemplo.png")
    fig.savefig(categories_path, dpi=140)
    plt.close(fig)

    return architecture_path, flow_path, categories_path


def build_pdf():
    architecture_path, flow_path, categories_path = generate_visual_assets()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleDoc",
        parent=styles["Heading1"],
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "SubDoc",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    h2 = styles["Heading2"]
    h3 = styles["Heading3"]
    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    story = []
    story.append(Paragraph("Documentacao de Engenharia de Software", title_style))
    story.append(Paragraph("Plataforma Multimodal para Pitch Automatizado de Startups", subtitle_style))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("1. Objetivo do sistema", h2))
    story.append(
        Paragraph(
            "A plataforma automatiza a avaliacao de pitches de startups com entrada multimodal, "
            "gerando score, feedback por categoria e relatorios em PDF. "
            "O foco e acelerar a validacao de ideias e apoiar decisoes de empreendedores e investidores.",
            body,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("2. Requisitos implementados", h2))
    req_table = Table(
        [
            ["Requisito", "Status"],
            ["Upload de texto em TXT/PDF/DOCX", "Implementado"],
            ["Audio por upload ou gravacao no navegador", "Implementado"],
            ["Video por upload ou gravacao no navegador", "Implementado"],
            ["Link YouTube no fluxo de pitch", "Implementado"],
            ["Analise com score final e categorias 0-10", "Implementado"],
            ["Relatorio automatico com pontos fortes e melhorias", "Implementado"],
            ["Exportacao de relatorio completo em PDF", "Implementado"],
            ["Video IA com D-ID/local/hibrido + progresso realtime", "Implementado"],
            ["Pitch PDF estilo slides com design automatico/manual", "Implementado"],
            ["Gestao de modelos com treino realtime", "Implementado"],
            ["Dashboard com historico, progresso e comparacao por sector", "Implementado"],
        ],
        colWidths=[12 * cm, 4 * cm],
    )
    req_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(req_table)
    story.append(PageBreak())

    story.append(Paragraph("3. Arquitetura tecnica", h2))
    story.append(
        Paragraph(
            "A solucao e baseada em Django/DRF no backend, templates responsivos no frontend, "
            "pipeline de features para multimodalidade e exportacao de relatorios em PDF.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(architecture_path, width=17 * cm, height=6.2 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("4. Fluxo funcional", h2))
    story.append(Image(flow_path, width=17 * cm, height=8 * cm))
    story.append(PageBreak())

    story.append(Paragraph("5. Logica de avaliacao, video e pitch deck", h2))
    story.append(
        Paragraph(
            "A avaliacao combina dados financeiros, qualidade textual, sinais multimodais e motor de inferencia "
            "(local ou GPT). O relatorio devolve score final e categorias padronizadas de 0 a 10. "
            "A plataforma tambem gera video explicativo (D-ID/local/hibrido) e pitch deck PDF visual com templates contextuais.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(categories_path, width=17 * cm, height=6.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Categorias aplicadas:", h3))
    for c in [
        "Clareza da ideia",
        "Proposta de valor",
        "Inovacao",
        "Viabilidade tecnica/financeira",
        "Escalabilidade",
        "Mercado-alvo",
        "Equipe fundadora",
        "Sustentabilidade",
    ]:
        story.append(Paragraph(f"• {c}", body))

    story.append(PageBreak())
    story.append(Paragraph("6. Guia do usuario", h2))
    story.append(Paragraph("Passo a passo para uso da plataforma:", h3))
    steps = [
        "Aceda a pagina 'Novo Pitch'.",
        "Preencha dados da startup e sector.",
        "Envie texto ou documento (TXT/PDF/DOCX).",
        "Opcionalmente grave ou envie audio e video, e adicione link YouTube.",
        "Informe receita, crescimento e margem.",
        "Escolha motor local ou GPT e clique em 'Analisar Pitch'.",
        "No resultado, opcionalmente gere video IA escolhendo modo (D-ID/local/hibrido).",
        "Para o pitch PDF, selecione design automatico por contexto ou design premium manual.",
        "Baixe relatorio PDF e pitch deck PDF e acompanhe seu historico no dashboard.",
    ]
    for idx, step in enumerate(steps, start=1):
        story.append(Paragraph(f"{idx}. {step}", body))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("7. Operacao e testes", h2))
    story.append(Paragraph("Comandos basicos:", h3))
    for cmd in [
        "python3 manage.py check",
        "python3 manage.py runserver 0.0.0.0:8000",
        "python3 manage.py train_model --model-output ai_models/pitch_model.pkl",
        "python3 docs/generate_engineering_pdf.py",
    ]:
        story.append(Paragraph(f"• {cmd}", body))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "Para validacao funcional, recomenda-se testar submissao multimodal, geracao de score, "
            "video IA com barra de progresso, pitch PDF com diferentes templates e comparacao de desempenho por sector no dashboard.",
            body,
        )
    )

    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("8. Publicacao da documentacao no Discord", h2))
    story.append(
        Paragraph(
            "A entrega operacional inclui o envio do PDF tecnico para webhook Discord definido pelo projeto, "
            "garantindo distribuicao imediata da documentacao apos atualizacoes.",
            body,
        )
    )

    doc.build(story)
    return PDF_PATH


if __name__ == "__main__":
    path = build_pdf()
    print(path)
