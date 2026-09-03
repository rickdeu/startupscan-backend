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
PDF_PATH = os.path.join(DOCS_DIR, "Software_Engineering_Documentation.pdf")


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

    # 1) Macro architecture
    fig, ax = plt.subplots(figsize=(12, 4.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    _draw_box(ax, 0.02, 0.55, 0.16, 0.3, "Frontend\nTemplates + JS", "#dbeafe")
    _draw_box(ax, 0.21, 0.55, 0.16, 0.3, "Views/API\nDjango + DRF", "#dcfce7")
    _draw_box(ax, 0.40, 0.55, 0.16, 0.3, "AI Pipeline\nLocal + GPT", "#ede9fe")
    _draw_box(ax, 0.59, 0.55, 0.16, 0.3, "AI Video\nD-ID/Local", "#fee2e2")
    _draw_box(ax, 0.78, 0.55, 0.18, 0.3, "Persistence\nSQLite/PostgreSQL", "#fde68a")
    _draw_box(ax, 0.26, 0.12, 0.2, 0.25, "PDF Report\nreport_export", "#fef3c7")
    _draw_box(ax, 0.52, 0.12, 0.2, 0.25, "Pitch Deck PDF\npitch_builder", "#ccfbf1")

    for x0, x1 in [(0.18, 0.21), (0.37, 0.40), (0.56, 0.59), (0.75, 0.78)]:
        ax.annotate("", xy=(x1, 0.70), xytext=(x0, 0.70), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.36, 0.37), xytext=(0.46, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.62, 0.37), xytext=(0.62, 0.55), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("StartupScan Platform Architecture", fontsize=12, weight="bold")
    architecture_path = os.path.join(ASSETS_DIR, "platform_architecture.png")
    fig.tight_layout()
    fig.savefig(architecture_path, dpi=150)
    plt.close(fig)

    # 2) Main functional flow
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    flow_steps = [
        (0.03, 0.70, "1. Multimodal\nsubmission"),
        (0.20, 0.70, "2. Feature\nextraction"),
        (0.37, 0.70, "3. Local/GPT\nscoring"),
        (0.54, 0.70, "4. Result\n+ recommendations"),
        (0.71, 0.70, "5. AI video\n(D-ID/local)"),
        (0.86, 0.70, "6. Export\nPDF/Pitch"),
        (0.29, 0.30, "7. Persistence\nhistory/metadata"),
        (0.56, 0.30, "8. Operational\ndashboard"),
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
    ax.set_title("Business functional flow", fontsize=12, weight="bold")
    flow_path = os.path.join(ASSETS_DIR, "functional_flow.png")
    fig.tight_layout()
    fig.savefig(flow_path, dpi=150)
    plt.close(fig)

    # 3) Example of categories
    categories = [
        "Clarity",
        "Value",
        "Innovation",
        "Viability",
        "Scalability",
        "Market",
        "Team",
        "Sustainability",
    ]
    values = [7.8, 8.2, 7.4, 6.9, 7.1, 7.6, 6.8, 7.3]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(categories, values, color="#2563eb")
    ax.set_ylim(0, 10)
    ax.set_ylabel("Score")
    ax.set_title("Example score by category (0-10)")
    ax.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.12, f"{val:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    categories_path = os.path.join(ASSETS_DIR, "category_example.png")
    fig.savefig(categories_path, dpi=150)
    plt.close(fig)

    # 4) Asynchronous job SLA (phase visual)
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.axis("off")
    phases = [
        ("Queue", "#e2e8f0"),
        ("Initialization", "#c7d2fe"),
        ("Preparation", "#bfdbfe"),
        ("Rendering", "#93c5fd"),
        ("Persistence", "#60a5fa"),
        ("Completed", "#22c55e"),
    ]
    x = 0.02
    for label, color in phases:
        _draw_box(ax, x, 0.25, 0.145, 0.5, label, color)
        x += 0.16
    for i in range(5):
        ax.annotate("", xy=(0.18 + 0.16 * i, 0.50), xytext=(0.165 + 0.16 * i, 0.50), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.set_title("Asynchronous job phases (video/training)", fontsize=11, weight="bold")
    jobs_path = os.path.join(ASSETS_DIR, "job_phases.png")
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
    story.append(Paragraph("Software Engineering Documentation - StartupScan", title_style))
    story.append(Paragraph("Complete and detailed version", subtitle_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("1. Scope and objectives", h2))
    story.append(
        Paragraph(
            "StartupScan is an AI-powered startup evaluation platform, aimed at pitch validation, "
            "executive communication, and decision support. The scope covers multimodal processing, scoring, "
            "report generation, AI video generation, visual pitch decks, and model management.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Operational objectives:", h3))
    for item in [
        "Reduce the time needed to analyze a startup opportunity.",
        "Standardize technical and investment feedback.",
        "Generate artifacts ready for stakeholder meetings.",
        "Maintain traceability of analyses and model iterations.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("2. Implemented requirements", h2))
    story.append(
        _table(
            [
                ["Functional requirement", "Status", "Notes"],
                ["Multimodal submission (text/doc/audio/video/youtube)", "Implemented", "Main flow in the pitch form"],
                ["Local/GPT evaluation with fallback", "Implemented", "Automatic fallback for resilience"],
                ["Score 0-10 + categories + recommendations", "Implemented", "With an interpretable block for investors"],
                ["Technical PDF report of the analysis", "Implemented", "Available on the result page"],
                ["AI video (auto/did_only/local_only)", "Implemented", "Asynchronous with a progress endpoint"],
                ["Slide-based pitch PDF", "Implemented", "Visual deck with a professional layout"],
                ["Automatic + manual premium design in the pitch PDF", "Implemented", "Configurable templates"],
                ["Model management (training/retraining/activation)", "Implemented", "With real-time progress"],
                ["Operational and investor dashboard", "Implemented", "With charts and filters"],
            ],
            [8.8 * cm, 2.4 * cm, 5.0 * cm],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("3. Technical architecture", h2))
    story.append(
        Paragraph(
            "The architecture consists of a server-side rendering frontend (Django templates), a Django/DRF backend, "
            "specialized AI services, and a relational persistence layer.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(architecture_path, width=17 * cm, height=6.3 * cm))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Stack:", h3))
    for item in [
        "Backend: Django + DRF",
        "AI: scikit-learn, OpenAI SDK",
        "Video/audio: moviepy, edge-tts, gTTS, D-ID API",
        "PDF/docs: reportlab, pypdf, python-docx",
        "Frontend: Bootstrap + JS + Chart.js",
        "Database: SQLite (dev), PostgreSQL (compatibility)",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("4. Business flows", h2))
    story.append(Image(flow_path, width=17 * cm, height=7.9 * cm))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "The flow starts with multimodal submission, goes through feature extraction and AI inference, "
            "and ends with decision artifacts: report, video, and pitch deck.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("5. Data model and persistence", h2))
    story.append(
        _table(
            [
                ["Entity", "Responsibility", "Critical fields"],
                ["PitchAnalysis", "Main evaluation record", "startup_name, score, report, metadata, multimodal files"],
                ["IdeaPitchSubmission", "Idea-to-full-pitch flow", "startup_name, problem, solution, generated_pitch, status"],
            ],
            [3.7 * cm, 5.8 * cm, 6.7 * cm],
            header_bg="#dcfce7",
            grid="#86efac",
        )
    )
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            "The JSON metadata layer is used to attach dynamic information about jobs, generation modes, "
            "narrative uniqueness keys, and processing state.",
            body,
        )
    )

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("6. Evaluation and interpretability pipeline", h2))
    story.append(Image(categories_path, width=17 * cm, height=6.2 * cm))
    story.append(Spacer(1, 0.18 * cm))
    for item in [
        "Extraction and consolidation of multimodal context.",
        "Score prediction and interpretable report generation.",
        "Standardized categories to facilitate comparison between startups.",
        "Recommendations oriented toward action and investment readiness.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(PageBreak())
    story.append(Paragraph("7. AI video pipeline", h2))
    story.append(Image(jobs_path, width=17 * cm, height=3.8 * cm))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "Video generation runs as an asynchronous job with phase-based progress. "
            "It supports the auto, did_only, and local_only modes, with detailed error handling per scenario and mandatory completion at the end.",
            body,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        _table(
            [
                ["Mode", "Description", "Fallback"],
                ["auto", "Attempts realistic D-ID and falls back to local when needed", "Yes"],
                ["did_only", "Forces exclusive use of the D-ID API", "No"],
                ["local_only", "Local rendering with no external dependency", "Not applicable"],
            ],
            [3 * cm, 9 * cm, 3 * cm],
            header_bg="#fee2e2",
            grid="#fecaca",
        )
    )

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("8. Pitch deck PDF pipeline", h2))
    story.append(
        Paragraph(
            "The pitch deck is exported in slide-based format (one page per slide), with two design strategies: "
            "automatic by context and manual premium by template.",
            body,
        )
    )
    story.append(
        _table(
            [
                ["Design mode", "Behavior", "Templates"],
                ["automatic by context", "Selects the visual identity based on the startup's content", "orbit/grid/wave/diagonal/aurora/ribbon"],
                ["manual premium", "The user explicitly chooses the template", "orbit/grid/wave/diagonal/aurora/ribbon"],
            ],
            [4.2 * cm, 6.8 * cm, 4 * cm],
            header_bg="#ede9fe",
            grid="#c4b5fd",
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("9. Main APIs and routes", h2))
    story.append(
        _table(
            [
                ["Route", "Method", "Description"],
                ["/analyze/form/", "GET/POST", "Multimodal submission and analysis"],
                ["/results/<id>/", "GET", "Full analysis view"],
                ["/results/<id>/pdf/", "GET", "Technical PDF report"],
                ["/results/<id>/pitch/pdf/", "GET", "Visual pitch deck PDF"],
                ["/results/<id>/video/generate/", "POST", "Starts an AI video job"],
                ["/results/<id>/video/progress/<job_id>/", "GET", "Video job status and progress"],
                ["/models/", "GET/POST", "Model management and training"],
                ["/investors/", "GET", "Investor-oriented dashboard"],
            ],
            [6.2 * cm, 2.2 * cm, 7.6 * cm],
            header_bg="#fef3c7",
            grid="#fde68a",
        )
    )

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("10. Operational guide", h2))
    for idx, item in enumerate(
        [
            "Start the application and check basic health via the dashboard.",
            "Run a multimodal submission with financial data.",
            "Check score, categories, and recommendations in the result.",
            "Generate a video in auto mode and track progress.",
            "Generate a pitch PDF in automatic mode and manual premium mode.",
            "Download the report and check the format for stakeholders.",
            "Monitor logs and analysis metadata for traceability.",
        ],
        start=1,
    ):
        story.append(Paragraph(f"{idx}. {item}", body))

    story.append(Spacer(1, 0.22 * cm))
    story.append(Paragraph("11. Security, reliability, and fallbacks", h2))
    for item in [
        "Format validation and upload exception handling.",
        "Normalized error messages for the frontend.",
        "Local fallback when GPT/D-ID is unavailable (where applicable).",
        "Error separation by scenario for quick diagnosis.",
        "User-based access control on sensitive routes.",
    ]:
        story.append(Paragraph(f"• {item}", body))

    story.append(Spacer(1, 0.22 * cm))
    story.append(Paragraph("12. Recommended testing and validation", h2))
    for cmd in [
        "python3 manage.py check",
        "python3 manage.py test",
        "python3 docs/generate_engineering_pdf.py",
        "python3 docs/generate_engineering_docx.py",
    ]:
        story.append(Paragraph(f"• {cmd}", body))
    story.append(
        Paragraph(
            "Minimum functional scenario: multimodal submission, result with score, AI video with progress, "
            "pitch deck PDF in both design modes, and technical report download.",
            body,
        )
    )

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("13. Documentation delivery and publishing", h2))
    story.append(
        Paragraph(
            "The operational routine includes publishing the updated documentation (PDF and DOCX) to the project's Discord webhook, "
            "ensuring immediate distribution to the team and stakeholders.",
            body,
        )
    )

    doc.build(story)
    return PDF_PATH


if __name__ == "__main__":
    generated = build_pdf()
    print(generated)
