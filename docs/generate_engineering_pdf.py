import os
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.8, wrap=True)


def generate_visual_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1) Arquitetura macro
    fig, ax = plt.subplots(figsize=(12, 4.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    _draw_box(ax, 0.02, 0.55, 0.16, 0.3, "Frontend\nTemplates + JS", "#dbeafe")
    _draw_box(ax, 0.21, 0.55, 0.16, 0.3, "Views/API\nDjango + DRF", "#dcfce7")
    _draw_box(ax, 0.40, 0.55, 0.16, 0.3, "Pipeline IA\nLocal + GPT", "#ede9fe")
    _draw_box(ax, 0.59, 0.55, 0.16, 0.3, "Video IA\nD-ID/Local", "#fee2e2")
    _draw_box(ax, 0.78, 0.55, 0.18, 0.3, "Persistencia\nSQLite/PostgreSQL", "#fde68a")
    _draw_box(ax, 0.26, 0.12, 0.2, 0.25, "Relatorio PDF\nreport_export", "#fef3c7")
    _draw_box(ax, 0.52, 0.12, 0.2, 0.25, "Pitch Deck PDF\npitch_builder", "#ccfbf1")

    for x0, x1 in [(0.18, 0.21), (0.37, 0.40), (0.56, 0.59), (0.75, 0.78)]:
        ax.annotate("", xy=(x1, 0.70), xytext=(x0, 0.70), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.36, 0.37), xytext=(0.46, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.62, 0.37), xytext=(0.62, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Arquitetura da Plataforma StartupScan", fontsize=12, weight="bold")
    architecture_path = os.path.join(ASSETS_DIR, "arquitetura_plataforma.png")
    fig.tight_layout()
    fig.savefig(architecture_path, dpi=150)
    plt.close(fig)

    # 2) Fluxo funcional principal
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    flow_steps = [
        (0.03, 0.70, "1. Submissao\nmultimodal"),
        (0.20, 0.70, "2. Extracao de\nfeatures"),
        (0.37, 0.70, "3. Scoring\nlocal/GPT"),
        (0.54, 0.70, "4. Resultado\n+ recomendacoes"),
        (0.71, 0.70, "5. Video IA\n(D-ID/local)"),
        (0.86, 0.70, "6. Export\nPDF/Pitch"),
        (0.29, 0.30, "7. Persistencia\nhistorico/metadata"),
        (0.56, 0.30, "8. Dashboard\noperacional"),
    ]
    for x, y, text in flow_steps:
        _draw_box(ax, x, y, 0.12, 0.18, text, "#e2e8f0")
    for start, end in [
        ((0.15, 0.79), (0.20, 0.79)),
        ((0.32, 0.79), (0.37, 0.79)),
        ((0.49, 0.79), (0.54, 0.79)),
        ((0.66, 0.79), (0.71, 0.79)),
        ((0.83, 0.79), (0.86, 0.79)),
        ((0.89, 0.70), (0.62, 0.39)),
        ((0.41, 0.39), (0.56, 0.39)),
    ]:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Fluxo funcional de negocio", fontsize=12, weight="bold")
    flow_path = os.path.join(ASSETS_DIR, "fluxo_funcional.png")
    fig.tight_layout()
    fig.savefig(flow_path, dpi=150)
    plt.close(fig)

    # 3) Exemplo de categorias
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
    ax.set_title("Exemplo de score por categoria (0-10)")
    ax.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.12, f"{val:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    categories_path = os.path.join(ASSETS_DIR, "categorias_exemplo.png")
    fig.savefig(categories_path, dpi=150)
    plt.close(fig)

    # 4) SLA de jobs assincromos (visual de fases)
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.axis("off")
    phases = [
        ("Fila", "#e2e8f0"),
        ("Inicializacao", "#c7d2fe"),
        ("Preparacao", "#bfdbfe"),
        ("Renderizacao", "#93c5fd"),
        ("Persistencia", "#60a5fa"),
        ("Concluido", "#22c55e"),
    ]
    x = 0.02
    for label, color in phases:
        _draw_box(ax, x, 0.25, 0.145, 0.5, label, color)
        x += 0.16
    for i in range(5):
        ax.annotate("", xy=(0.18 + 0.16 * i, 0.50), xytext=(0.165 + 0.16 * i, 0.50), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.set_title("Fases de jobs assincromos (video/treino)", fontsize=11, weight="bold")
    jobs_path = os.path.join(ASSETS_DIR, "fases_jobs.png")
    fig.tight_layout()
    fig.savefig(jobs_path, dpi=150)
    plt.close(fig)

    return architecture_path, flow_path, categories_path, jobs_path


def _table(data, col_widths, header_bg="#dbeafe", grid="#bfdbfe"):
    tb = Table(data, colWidths=col_widths)
    tb.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor(grid)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tb


def build_pdf():
    architecture_path, flow_path, categories_path, jobs_path = generate_visual_assets()
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
        spaceAfter=9,
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
    story.append(Paragraph("Documentacao de Engenharia de Software - StartupScan", title_style))
    story.append(Paragraph("Versao completa e detalhada", subtitle_style))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("1. Escopo e objetivos", h2))
    story.append(
        Paragraph(
            "O StartupScan e uma plataforma de avaliacao de startups com IA, voltada para validacao de pitch, "
            "comunicacao executiva e suporte a decisao. O escopo cobre processamento multimodal, scoring, "
            "geracao de relatorios, geracao de video IA, pitch deck visual e gestao de modelos.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Objetivos operacionais:", h3))
    for item in [
        "Reduzir tempo de analise de oportunidade de startup.",
        "Padronizar feedback tecnico e de investimento.",
        "Gerar artefatos prontos para reunioes com stakeholders.",
        "Manter rastreabilidade de analises e iteracoes de modelo.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("2. Requisitos implementados", h2))
    story.append(
        _table(
            [
                ["Requisito funcional", "Status", "Observacao"],
                ["Submissao multimodal (texto/doc/audio/video/youtube)", "Implementado", "Fluxo principal no formulario de pitch"],
                ["Avaliacao local/GPT com fallback", "Implementado", "Fallback automatico para resiliencia"],
                ["Score 0-10 + categorias + recomendacoes", "Implementado", "Com bloco interpretavel para investidor"],
                ["Relatorio tecnico PDF da analise", "Implementado", "Disponivel na pagina de resultado"],
                ["Video IA (auto/did_only/local_only)", "Implementado", "Assincrono com endpoint de progresso"],
                ["Pitch PDF em slides", "Implementado", "Deck visual com layout profissional"],
                ["Design automatico + premium manual no pitch PDF", "Implementado", "Templates configuraveis"],
                ["Gestao de modelos (treino/retreino/ativacao)", "Implementado", "Com progresso realtime"],
                ["Dashboard operacional e investidor", "Implementado", "Com graficos e filtros"],
            ],
            [8.8 * cm, 2.4 * cm, 5.0 * cm],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("3. Arquitetura tecnica", h2))
    story.append(
        Paragraph(
            "A arquitetura e composta por frontend server-side rendering (Django templates), backend Django/DRF, "
            "servicos de IA especializados e camada de persistencia relacional.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(architecture_path, width=17 * cm, height=6.3 * cm))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Stack:", h3))
    for item in [
        "Backend: Django + DRF",
        "IA: scikit-learn, OpenAI SDK",
        "Video/audio: moviepy, edge-tts, gTTS, D-ID API",
        "PDF/docs: reportlab, pypdf, python-docx",
        "Frontend: Bootstrap + JS + Chart.js",
        "Banco: SQLite (dev), PostgreSQL (compatibilidade)",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("4. Fluxos de negocio", h2))
    story.append(Image(flow_path, width=17 * cm, height=7.9 * cm))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "O fluxo inicia na submissao multimodal, passa por extracao de features e inferencia IA, "
            "e termina em artefatos de decisao: relatorio, video e pitch deck.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("5. Modelo de dados e persistencia", h2))
    story.append(
        _table(
            [
                ["Entidade", "Responsabilidade", "Campos criticos"],
                ["PitchAnalysis", "Registro da avaliacao principal", "startup_name, score, report, metadata, arquivos multimodais"],
                ["IdeaPitchSubmission", "Fluxo de ideia para pitch completo", "startup_name, problem, solution, generated_pitch, status"],
            ],
            [3.7 * cm, 5.8 * cm, 6.7 * cm],
            header_bg="#dcfce7",
            grid="#86efac",
        )
    )
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            "A camada de metadata em JSON e utilizada para acoplar informacoes dinamicas de jobs, modos de geracao, "
            "chaves de unicidade narrativa e estado de processamento.",
            body,
        )
    )

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("6. Pipeline de avaliacao e interpretabilidade", h2))
    story.append(Image(categories_path, width=17 * cm, height=6.2 * cm))
    story.append(Spacer(1, 0.18 * cm))
    for item in [
        "Extracao e consolidacao de contexto multimodal.",
        "Predicao de score e geracao de relatorio interpretavel.",
        "Categorias padronizadas para facilitar comparacao entre startups.",
        "Recomendacoes orientadas a acao e prontidao de investimento.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(PageBreak())
    story.append(Paragraph("7. Pipeline de video IA", h2))
    story.append(Image(jobs_path, width=17 * cm, height=3.8 * cm))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "A geracao de video roda em job assincromo com progresso por fases. "
            "Suporta os modos auto, did_only e local_only, com erro detalhado por cenario e conclusao obrigatoria no final.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        _table(
            [
                ["Modo", "Descricao", "Fallback"],
                ["auto", "Tenta D-ID realista e cai para local quando necessario", "Sim"],
                ["did_only", "Forca uso exclusivo da API D-ID", "Nao"],
                ["local_only", "Renderizacao local sem dependencia externa", "Nao aplicavel"],
            ],
            [3 * cm, 9 * cm, 3 * cm],
            header_bg="#fee2e2",
            grid="#fecaca",
        )
    )

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("8. Pipeline de pitch deck PDF", h2))
    story.append(
        Paragraph(
            "O pitch deck e exportado em formato slide-based (uma pagina por slide), com duas estrategias de design: "
            "automatico por contexto e premium manual por template.",
            body,
        )
    )
    story.append(
        _table(
            [
                ["Modo de design", "Comportamento", "Templates"],
                ["automatico por contexto", "Seleciona identidade visual a partir do conteudo da startup", "orbit/grid/wave/diagonal/aurora/ribbon"],
                ["premium manual", "Usuario escolhe explicitamente o template", "orbit/grid/wave/diagonal/aurora/ribbon"],
            ],
            [4.2 * cm, 6.8 * cm, 4 * cm],
            header_bg="#ede9fe",
            grid="#c4b5fd",
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("9. APIs e rotas principais", h2))
    story.append(
        _table(
            [
                ["Rota", "Metodo", "Descricao"],
                ["/analyze/form/", "GET/POST", "Submissao e analise multimodal"],
                ["/results/<id>/", "GET", "Visualizacao completa da analise"],
                ["/results/<id>/pdf/", "GET", "Relatorio tecnico PDF"],
                ["/results/<id>/pitch/pdf/", "GET", "Pitch deck PDF visual"],
                ["/results/<id>/video/generate/", "POST", "Inicializa job de video IA"],
                ["/results/<id>/video/progress/<job_id>/", "GET", "Estado e progresso do job de video"],
                ["/models/", "GET/POST", "Gestao e treino de modelos"],
                ["/investors/", "GET", "Dashboard orientado a investidor"],
            ],
            [6.2 * cm, 2.2 * cm, 7.6 * cm],
            header_bg="#fef3c7",
            grid="#fde68a",
        )
    )

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("10. Guia operacional", h2))
    for idx, item in enumerate(
        [
            "Subir aplicacao e validar health basico via dashboard.",
            "Executar submissao multimodal com dados financeiros.",
            "Validar score, categorias e recomendacoes no resultado.",
            "Gerar video em modo auto e acompanhar progresso.",
            "Gerar pitch PDF em modo automatico e premium manual.",
            "Baixar relatorio e validar formato para stakeholder.",
            "Monitorar logs e metadata da analise para rastreabilidade.",
        ],
        start=1,
    ):
        story.append(Paragraph(f"{idx}. {item}", body))

    story.append(Spacer(1, 0.22 * cm))
    story.append(Paragraph("11. Seguranca, confiabilidade e fallbacks", h2))
    for item in [
        "Validacao de formatos e tratamento de excecoes de upload.",
        "Mensagens de erro normalizadas para frontend.",
        "Fallback local quando GPT/D-ID estiver indisponivel (onde aplicavel).",
        "Separacao de erro por cenario para diagnostico rapido.",
        "Controle de acesso por usuario em rotas sensiveis.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.22 * cm))
    story.append(Paragraph("12. Testes e validacao recomendada", h2))
    for cmd in [
        "python3 manage.py check",
        "python3 manage.py test",
        "python3 docs/generate_engineering_pdf.py",
        "python3 docs/generate_engineering_docx.py",
    ]:
        story.append(Paragraph(f"• {cmd}", body))
    story.append(
        Paragraph(
            "Cenario funcional minimo: submissao multimodal, resultado com score, video IA com progresso, "
            "pitch deck PDF nos dois modos de design e download de relatorio tecnico.",
            body,
        )
    )

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("13. Entrega de documentacao e publicacao", h2))
    story.append(
        Paragraph(
            "A rotina operacional inclui publicacao da documentacao atualizada (PDF e DOCX) no webhook Discord do projeto, "
            "assegurando distribuicao imediata para equipe e stakeholders.",
            body,
        )
    )

    doc.build(story)
    return PDF_PATH


if __name__ == "__main__":
    generated = build_pdf()
    print(generated)
