"""
Generates the technical report of the StartupScan project in .docx format.

Usage:
    python docs/generate_technical_report.py
"""

import os
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
OUTPUT_PATH = os.path.join(DOCS_DIR, "StartupScan_Technical_Report.docx")

# ---------------------------------------------------------------------------
# Report metadata
# ---------------------------------------------------------------------------
AUTHOR = "Andre Hangalo"
AUTHOR_EMAIL = "hangaloandre@gmail.com"
PROJECT_TITLE = "StartupScan"
REPORT_SUBTITLE = (
    "Intelligent Startup Evaluation Platform Powered by Artificial Intelligence"
)
GENERATION_DATE = datetime.now().strftime("%B %d, %Y")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _set_font(run, name="Times New Roman", size=12, bold=False,
              italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def _para(doc, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=12,
          bold=False, italic=False, space_before=0, space_after=6,
          font="Times New Roman"):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    _set_font(run, name=font, size=size, bold=bold, italic=italic)
    return p


def _heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in h.runs:
        run.font.name = "Times New Roman"
        run.font.color.rgb = RGBColor(0, 0, 0)
    return h


def _bullet(doc, items, size=12):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(item)
        _set_font(run, size=size)


def _numbered(doc, items, size=12):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(item)
        _set_font(run, size=size)


def _table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light List Accent 1"
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for para in hdr_cells[i].paragraphs:
            for run in para.runs:
                run.font.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(11)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = val
            for para in cells[i].paragraphs:
                for run in para.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
    if col_widths:
        for row in table.rows:
            for i, cell in enumerate(row.cells):
                if i < len(col_widths):
                    cell.width = Inches(col_widths[i])
    return table


def _page_break(doc):
    doc.add_page_break()


def _add_page_numbers(doc):
    """Adds page numbering in the footer."""
    section = doc.sections[0]
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_para.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_end)


def _set_margins(doc, top=1.0, bottom=1.0, left=1.25, right=1.0):
    section = doc.sections[0]
    section.top_margin = Inches(top)
    section.bottom_margin = Inches(bottom)
    section.left_margin = Inches(left)
    section.right_margin = Inches(right)


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _capa(doc):
    _para(doc, PROJECT_TITLE, align=WD_ALIGN_PARAGRAPH.CENTER,
          size=20, bold=True, space_after=8)
    _para(doc, REPORT_SUBTITLE, align=WD_ALIGN_PARAGRAPH.CENTER,
          size=14, italic=True, space_after=60)

    _para(doc, f"Author: {AUTHOR}", align=WD_ALIGN_PARAGRAPH.CENTER,
          size=12, space_after=4)
    _para(doc, AUTHOR_EMAIL, align=WD_ALIGN_PARAGRAPH.CENTER,
          size=12, space_after=4)
    _para(doc, GENERATION_DATE, align=WD_ALIGN_PARAGRAPH.CENTER,
          size=12, space_after=0)
    _page_break(doc)


def _resumo(doc):
    _heading(doc, "Abstract", level=1)
    _para(doc, (
        "This report describes the development of the StartupScan project, a full-stack web platform "
        "for intelligent startup evaluation. "
        "The system's main goal is to automate the complete cycle of startup pitch analysis, from receiving "
        "multimodal inputs — text, documents, audio, video, and YouTube links — to producing communication "
        "artifacts ready for use by entrepreneurs, analysts, and investors."
    ))
    _para(doc, (
        "The platform integrates a machine learning pipeline based on scikit-learn and XGBoost to generate "
        "a success score from 0 to 10, with category-based explainability. In addition, it offers integration "
        "with the OpenAI GPT API as an alternative engine, generation of a technical PDF report, construction "
        "of a visual pitch deck PDF with multiple templates, and generation of an AI-narrated explainer video, "
        "with support for the D-ID API and a local fallback via moviepy and TTS."
    ))
    _para(doc, (
        "From a technical standpoint, the system was built with Django 6 and Django REST Framework, "
        "uses SQLite in development and PostgreSQL in production, and relies on Redis and Celery for "
        "asynchronous processing of long-running tasks. Access control is implemented through a "
        "role-based access control (RBAC) model with five levels: administrator, analyst, entrepreneur, "
        "investor, and general public."
    ))
    _para(doc, (
        "Keywords: artificial intelligence, startup evaluation, machine learning, "
        "Django, multimodal processing, pitch analysis."
    ), italic=True, space_after=0)
    _page_break(doc)


def _indice(doc):
    _heading(doc, "Table of Contents", level=1)
    entries = [
        ("1.", "Introduction", "5"),
        ("2.", "Context and Objectives", "6"),
        ("  2.1.", "Problem", "6"),
        ("  2.2.", "System Objectives", "6"),
        ("  2.3.", "Target Audience", "7"),
        ("3.", "Technical Architecture", "8"),
        ("  3.1.", "Technology Stack", "8"),
        ("  3.2.", "Component Architecture", "9"),
        ("  3.3.", "Data Flow", "9"),
        ("  3.4.", "Asynchronous Processing", "10"),
        ("4.", "Data Model", "11"),
        ("  4.1.", "PitchAnalysis", "11"),
        ("  4.2.", "UserProfile", "12"),
        ("  4.3.", "IdeaPitchSubmission", "12"),
        ("  4.4.", "InvestorConnectionInterest", "13"),
        ("  4.5.", "IdeaPublicFeedback", "13"),
        ("5.", "Implemented Features", "14"),
        ("  5.1.", "Multimodal Pitch Evaluation", "14"),
        ("  5.2.", "Technical PDF Report", "15"),
        ("  5.3.", "Pitch Deck PDF", "15"),
        ("  5.4.", "AI Explainer Video", "16"),
        ("  5.5.", "Idea Builder", "16"),
        ("  5.6.", "Batch Processing", "17"),
        ("  5.7.", "ML Model Management", "17"),
        ("  5.8.", "Investor-Startup Connections", "17"),
        ("6.", "Access Control and Roles", "18"),
        ("7.", "Endpoint Reference", "19"),
        ("8.", "Machine Learning Pipeline", "21"),
        ("9.", "Installation and Configuration", "22"),
        ("  9.1.", "Prerequisites", "22"),
        ("  9.2.", "Local Setup", "22"),
        ("  9.3.", "Environment Variables", "23"),
        ("  9.4.", "Running with Docker Compose", "25"),
        ("  9.5.", "Deployment on Render", "25"),
        ("10.", "Testing and Validation", "26"),
        ("11.", "Conclusion", "27"),
        ("12.", "References", "28"),
    ]
    tbl = doc.add_table(rows=0, cols=3)
    tbl.style = "Table Grid"
    for num, title, page in entries:
        row = tbl.add_row().cells
        row[0].text = num
        row[1].text = title
        row[2].text = page
        for cell in row:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
        row[0].width = Inches(0.5)
        row[1].width = Inches(5.0)
        row[2].width = Inches(0.5)
    _page_break(doc)


def _introducao(doc):
    _heading(doc, "1. Introduction", level=1)
    _para(doc, (
        "The startup ecosystem in Angola and across Africa in general has grown significantly in recent "
        "years, driven by expanding connectivity, the emergence of accelerators, and the growing "
        "availability of venture capital. In this context, the ability to evaluate investment opportunities "
        "quickly, consistently, and rigorously becomes a critical factor for every stakeholder in the "
        "ecosystem — entrepreneurs, analysts, and investors."
    ))
    _para(doc, (
        "The StartupScan project was developed with the goal of addressing this need through a web "
        "platform that automates and standardizes the process of evaluating startup pitches using "
        "artificial intelligence."
    ))
    _para(doc, (
        "This technical report documents the entirety of the work carried out: from requirements "
        "definition and system architecture, through the implementation of each feature, to the "
        "installation, configuration, testing, and deployment procedures. The document is organized "
        "to serve as a technical reference for developers and stakeholders."
    ))
    _para(doc, (
        "The report is structured into twelve chapters. Chapters 2 and 3 provide context on the "
        "problem and describe the system architecture. Chapters 4 through 8 detail the data model, "
        "the features, access control, the endpoints, and the machine learning pipeline. Chapters 9 "
        "and 10 cover installation and testing. Chapter 11 presents the conclusions, and chapter 12 "
        "lists the bibliographic references."
    ))


def _contexto_objetivos(doc):
    _heading(doc, "2. Context and Objectives", level=1)

    _heading(doc, "2.1. Problem", level=2)
    _para(doc, (
        "Evaluating startup pitches is a traditionally manual, time-consuming, and subjective process. "
        "An experienced analyst can only evaluate a limited number of pitches per week, and the quality "
        "of feedback varies significantly between evaluators. This inefficiency creates bottlenecks in "
        "accelerators and investment funds, delays the financing process, and deprives entrepreneurs of "
        "structured, actionable feedback in a timely manner."
    ))
    _para(doc, (
        "Additionally, entrepreneurs, particularly those at early stages, often lack tools to help them "
        "structure and effectively communicate their ideas to potential investors. The absence of "
        "quality communication artifacts — pitch decks, reports, and presentation videos — constitutes "
        "a barrier to accessing financing."
    ))

    _heading(doc, "2.2. System Objectives", level=2)
    _para(doc, "StartupScan was designed to achieve the following objectives:")

    _para(doc, "Business objectives:", bold=True, space_after=2)
    _bullet(doc, [
        "Reduce the time to analyze startup opportunities from days to seconds.",
        "Standardize the quality and structure of feedback for entrepreneurs.",
        "Provide ready-to-use communication artifacts (PDF, video) with no extra effort.",
        "Create a structured channel connecting entrepreneurs and investors.",
    ])

    _para(doc, "Technical objectives:", bold=True, space_after=2)
    _bullet(doc, [
        "Implement a robust multimodal data ingestion pipeline.",
        "Develop and integrate an interpretable machine learning model.",
        "Build a system for automatic artifact generation (PDF, video).",
        "Ensure scalability through asynchronous processing with Celery.",
        "Provide a RESTful API for integration with external systems.",
    ])

    _heading(doc, "2.3. Target Audience", level=2)
    _table(doc,
        ["Profile", "Role in the system", "Main features"],
        [
            ["Entrepreneur", "entrepreneur",
             "Pitch submission, idea builder, pitch deck PDF, connections"],
            ["Analyst", "analyst",
             "Analytical dashboard, batch processing, ML model management"],
            ["Investor", "investor",
             "Deal flow dashboard, expressing interest, connection hub"],
            ["General public", "general_public",
             "Browsing public ideas, star-rated feedback"],
            ["Administrator", "admin",
             "Full management: users, models, system configuration"],
        ],
        col_widths=[1.2, 1.2, 3.6],
    )


def _arquitectura(doc):
    _heading(doc, "3. Technical Architecture", level=1)

    _heading(doc, "3.1. Technology Stack", level=2)
    _para(doc, (
        "The system was built on a set of mature technologies widely adopted in the industry, "
        "selected based on criteria of stability, ecosystem support, and fit for the problem."
    ))
    _table(doc,
        ["Layer", "Technology", "Version", "Function"],
        [
            ["Web framework", "Django", "6.0.3", "MVC, ORM, authentication, admin"],
            ["REST API", "Django REST Framework", "3.16.1", "Serialization, JSON endpoints"],
            ["Server", "Gunicorn + WhiteNoise", "23.0 / 6.11", "WSGI, static files"],
            ["Database (dev)", "SQLite", "3.x", "Local persistence"],
            ["Database (prod)", "PostgreSQL", "15", "Production persistence"],
            ["Cache / Queues", "Redis + Celery", "—", "Asynchronous jobs"],
            ["ML / AI", "scikit-learn, XGBoost", "1.4.2 / 2.0.3", "Scoring pipeline"],
            ["LLM", "OpenAI SDK", "1.23.2", "GPT as an alternative engine"],
            ["Video", "moviepy, OpenCV, D-ID", "2.1.2 / 4.9", "AI video generation"],
            ["Audio / TTS", "Whisper, edge-tts, gTTS", "—", "Transcription and speech synthesis"],
            ["PDF / DOCX", "ReportLab, pypdf, python-docx", "4.4 / 6.9 / 1.2", "Document generation"],
            ["Frontend", "Django Templates + Bootstrap + Chart.js", "—", "Web interface"],
        ],
        col_widths=[1.5, 1.8, 1.0, 2.2],
    )

    _heading(doc, "3.2. Component Architecture", level=2)
    _para(doc, (
        "The system follows a layered architecture with clear separation of responsibilities. "
        "Each layer communicates only with the adjacent layer, favoring code maintainability "
        "and testability."
    ))
    _table(doc,
        ["Layer", "Modules", "Responsibility"],
        [
            ["Presentation", "templates/, static/",
             "Web interface, forms, dashboards, progress polling"],
            ["Control", "views.py, urls.py",
             "Request orchestration, access control, HTTP responses"],
            ["Business", "services/*, modeling.py",
             "Analysis logic, artifact generation, model training"],
            ["Data", "models.py, serializers.py",
             "Database abstraction, validation, serialization"],
            ["Infrastructure", "tasks.py, celery.py, settings.py",
             "Asynchronous queues, configuration, environment variables"],
        ],
        col_widths=[1.4, 1.8, 3.3],
    )

    _heading(doc, "3.3. Data Flow", level=2)
    _para(doc, "The main flow of a pitch evaluation follows these steps:")
    _numbered(doc, [
        "The user submits the pitch through the web form or the REST API.",
        "The pitch_input.py module extracts and normalizes content from all formats "
        "(text, PDF, DOCX, audio via Whisper, video via audio extraction).",
        "The feature engineering engine transforms text into TF-IDF vectors and "
        "normalizes financial data.",
        "The active ML model (or GPT, if configured) generates the score and the "
        "structured report with categories and recommendations.",
        "The result is persisted in the PitchAnalysis table in the database.",
        "The user is redirected to the results page, where they can download "
        "the PDF report, the pitch deck, or start video generation.",
    ])

    _heading(doc, "3.4. Asynchronous Processing", level=2)
    _para(doc, (
        "Long-running tasks — ML model training and video generation — are executed "
        "asynchronously so as not to block the web server. The pattern implemented "
        "is as follows:"
    ))
    _numbered(doc, [
        "The client sends a POST request to the task-start endpoint.",
        "The server creates a unique job identifier (job_id) and starts the task "
        "in the background via Celery.",
        "The server immediately returns the job_id to the client.",
        "The client periodically polls the progress endpoint, receiving "
        "JSON status updates.",
        "When the status is 'completed', the client displays the result to the user.",
    ])
    _para(doc, (
        "This pattern is applied both to model training (/model/retrain/ → "
        "/models/training/progress/<job_id>/) and to video generation "
        "(/video/generate/ → /video/progress/<job_id>/)."
    ))


def _modelos_dados(doc):
    _heading(doc, "4. Data Model", level=1)
    _para(doc, (
        "The StartupScan data schema is composed of five main models, all managed "
        "by the Django ORM and versioned through the migration system. "
        "Each model is described below, together with its fields and relationships."
    ))

    _heading(doc, "4.1. PitchAnalysis", level=2)
    _para(doc, (
        "Central record of each startup evaluation. It aggregates all input data, "
        "analysis results, and operational metadata."
    ))
    _table(doc,
        ["Field", "Type", "Description"],
        [
            ["user", "FK User (nullable)", "User who submitted the analysis"],
            ["startup_name", "CharField", "Startup name"],
            ["industry", "CharField", "Sector (tech, health, finance, education, ecommerce, other)"],
            ["contact_email", "EmailField", "Contact email"],
            ["text", "TextField", "Pitch text"],
            ["audio_file", "FileField", "Uploaded audio file"],
            ["video_file", "FileField", "Uploaded video file"],
            ["document_file", "FileField", "Uploaded document (PDF, DOCX, etc.)"],
            ["presenter_face_image_file", "FileField", "Presenter photograph"],
            ["youtube_url", "URLField", "YouTube link for the pitch"],
            ["revenue", "DecimalField", "Revenue in AOA"],
            ["growth_rate", "FloatField", "Growth rate (%)"],
            ["profit_margin", "FloatField", "Profit margin (%)"],
            ["burn_rate", "DecimalField", "Monthly cash burn"],
            ["success_score", "FloatField", "Final score from 0 to 10"],
            ["confidence", "FloatField", "Prediction confidence (%)"],
            ["report", "JSONField", "Full structured report"],
            ["status", "CharField", "pending / processing / completed / failed"],
            ["model_version", "CharField", "Version of the ML model used"],
            ["processing_time", "FloatField", "Processing time in seconds"],
            ["ip_address", "GenericIPAddressField", "Client IP"],
            ["created_at", "DateTimeField", "Creation date/time"],
            ["updated_at", "DateTimeField", "Last update date/time"],
        ],
        col_widths=[1.8, 1.5, 3.2],
    )

    _heading(doc, "4.2. UserProfile", level=2)
    _para(doc, (
        "Extension of Django's default user model to support the role system. "
        "Automatically created when each new user registers."
    ))
    _table(doc,
        ["Field", "Type", "Description"],
        [
            ["user", "OneToOneField User", "Reference to the Django user"],
            ["role", "CharField", "One of five roles: entrepreneur, investor, analyst, general_public, admin"],
            ["created_at", "DateTimeField", "Creation date/time"],
            ["updated_at", "DateTimeField", "Last update date/time"],
        ],
        col_widths=[1.8, 1.8, 2.9],
    )

    _heading(doc, "4.3. IdeaPitchSubmission", level=2)
    _para(doc, (
        "Stores business ideas submitted through the idea builder. Each record represents "
        "an idea in draft state or with a generated pitch."
    ))
    _table(doc,
        ["Field", "Type", "Description"],
        [
            ["user", "FK User", "Creating user"],
            ["startup_name", "CharField", "Startup name"],
            ["one_liner", "CharField", "One-sentence pitch"],
            ["problem", "TextField", "Problem the startup solves"],
            ["solution", "TextField", "Proposed solution"],
            ["target_customer", "TextField", "Target customer profile"],
            ["market_size", "TextField", "Addressable market size"],
            ["business_model", "TextField", "Business model"],
            ["competitive_advantage", "TextField", "Competitive edge"],
            ["traction", "TextField", "Current traction and validations"],
            ["team", "TextField", "Team composition and experience"],
            ["funding_goal", "CharField", "Funding target"],
            ["use_of_funds", "TextField", "Planned use of funds"],
            ["model_source", "CharField", "Generation engine: local / gpt"],
            ["status", "CharField", "draft / generated"],
            ["generated_pitch", "JSONField", "Content of the generated pitch"],
        ],
        col_widths=[1.8, 1.2, 3.5],
    )

    _heading(doc, "4.4. InvestorConnectionInterest", level=2)
    _para(doc, (
        "Records an investor's interest in a startup analysis. Supports the full "
        "communication cycle between investor and entrepreneur."
    ))
    _table(doc,
        ["Field", "Type", "Description"],
        [
            ["analysis", "FK PitchAnalysis", "Analysis of interest"],
            ["investor", "FK User", "Investor user"],
            ["entrepreneur", "FK User (nullable)", "Recipient entrepreneur user"],
            ["status", "CharField", "pending / reviewing / connected / rejected / withdrawn"],
            ["investor_message", "TextField", "Investor's initial message"],
            ["entrepreneur_reply", "TextField", "Entrepreneur's reply"],
            ["created_at", "DateTimeField", "Date/time the interest was created"],
            ["responded_at", "DateTimeField", "Date/time of the entrepreneur's reply"],
        ],
        col_widths=[1.8, 1.5, 3.2],
    )

    _heading(doc, "4.5. IdeaPublicFeedback", level=2)
    _para(doc, (
        "Community evaluation of ideas made public in the idea marketplace. "
        "Each user may submit only one feedback entry per idea."
    ))
    _table(doc,
        ["Field", "Type", "Description"],
        [
            ["submission", "FK IdeaPitchSubmission", "Evaluated idea"],
            ["author", "FK User", "User who submitted the evaluation"],
            ["stars", "IntegerField", "Rating from 1 to 5 stars"],
            ["endorsed", "BooleanField", "Indicates whether the user endorsed the idea"],
            ["comment", "TextField", "Qualitative comment"],
            ["created_at", "DateTimeField", "Date/time of the evaluation"],
        ],
        col_widths=[1.8, 1.2, 3.5],
    )


def _funcionalidades(doc):
    _heading(doc, "5. Implemented Features", level=1)

    _heading(doc, "5.1. Multimodal Pitch Evaluation", level=2)
    _para(doc, (
        "The system's core feature allows the user to submit information "
        "about their startup in any combination of the following formats:"
    ))
    _bullet(doc, [
        "Free text typed directly into the form.",
        "Document: .txt, .md, .csv, .pdf, .docx.",
        "Audio file (WAV, MP3, OGG) — transcribed via OpenAI Whisper.",
        "Video file — audio is extracted and transcribed.",
        "YouTube link — audio is extracted and transcribed.",
        "Financial data: revenue (AOA), growth rate, profit margin, burn rate.",
    ])
    _para(doc, (
        "The pitch_input.py module consolidates all inputs into a single normalized "
        "text block, which is then processed by the ML pipeline. The analysis result "
        "includes: a score from 0 to 10, a confidence percentage, an executive summary, "
        "strengths, weaknesses, actionable recommendations, and an evaluation across "
        "eight categories — Clarity of Proposal, Value Proposition, Innovation, "
        "Viability, Scalability, Target Market, Team, and Sustainability."
    ))

    _heading(doc, "5.2. Technical PDF Report", level=2)
    _para(doc, (
        "For each completed analysis, the system automatically generates a technical "
        "report in PDF format via ReportLab. The document includes: submitted startup "
        "data, score and confidence with a graphical visualization, detailed evaluation "
        "by category, financial analysis, actionable recommendations, and metadata about "
        "the model used (version, processing time)."
    ))

    _heading(doc, "5.3. Pitch Deck PDF", level=2)
    _para(doc, (
        "The system generates a visual pitch deck in PDF format, structured as slides "
        "ready for presentation to investors. Each page corresponds to a slide, "
        "with an executive cover, a structured narrative, and a conclusion. "
        "Two modes are supported:"
    ))
    _bullet(doc, [
        "Automatic design by context (recommended): the system selects the template "
        "based on the industry and the startup's data.",
        "Manual premium design: the user chooses among six templates — Orbit, Grid, "
        "Wave, Diagonal, Aurora, and Ribbon.",
    ])

    _heading(doc, "5.4. AI Explainer Video", level=2)
    _para(doc, (
        "Based on the analysis result, the system generates an AI-narrated video "
        "between 1 and 3 minutes long. Three generation modes are supported:"
    ))
    _bullet(doc, [
        "auto: attempts the D-ID API (realistic presenter) and falls back to a local video on failure.",
        "did_only: uses exclusively the D-ID API.",
        "local_only: local generation with moviepy and TTS, with no paid external dependencies.",
    ])
    _para(doc, (
        "The process is asynchronous, with progress updated in real time via polling. "
        "The system supports automatic detection of the presenter's gender from a "
        "photograph, using deepface, in order to select the appropriate TTS voice."
    ))

    _heading(doc, "5.5. Idea Builder", level=2)
    _para(doc, (
        "The idea builder allows the entrepreneur to structure a business idea "
        "through a guided form with fields for problem, solution, target customer, "
        "market size, business model, competitive advantage, traction, team, "
        "funding goal, and use of funds. Based on this data, the system "
        "automatically generates a narrative pitch (via the local model or GPT), which can be "
        "exported as a PDF or published to the public marketplace to receive feedback "
        "from the community."
    ))

    _heading(doc, "5.6. Batch Processing", level=2)
    _para(doc, (
        "Analysts and administrators can submit a CSV file containing multiple "
        "pitches for batch evaluation. Processing happens asynchronously, "
        "with progress polling available. Results are made available for "
        "download as a consolidated CSV file."
    ))

    _heading(doc, "5.7. ML Model Management", level=2)
    _para(doc, (
        "The model management panel, accessible to analysts and administrators, allows:"
    ))
    _bullet(doc, [
        "Importing external datasets (CSV of pitches and financial data).",
        "Training and retraining the model with real-time progress.",
        "Activating the model to be used in analyses.",
        "Editing model metadata (display name, description).",
        "Removing obsolete models.",
    ])

    _heading(doc, "5.8. Investor-Startup Connections", level=2)
    _para(doc, (
        "The platform implements a structured communication channel between investors "
        "and entrepreneurs. The investor expresses interest in an analysis with a "
        "personalized message. The entrepreneur receives the notification in the "
        "connection hub and can accept, reject, or reply. The connection status moves "
        "through the cycle: pending → reviewing → connected / rejected."
    ))


def _controlo_acesso(doc):
    _heading(doc, "6. Access Control and Roles", level=1)
    _para(doc, (
        "The system implements Role-Based Access Control (RBAC). Each user has a "
        "UserProfile with a role assigned at registration time. Access to each "
        "feature is checked by the RoleRequiredMixin in the views. Administrators "
        "correspond to Django superusers, created via manage.py createsuperuser."
    ))
    _table(doc,
        ["Role", "Dashboard", "Pitch", "ML Models", "Investor", "Ideas", "Connections", "Admin"],
        [
            ["admin", "✓", "✓", "✓", "✓", "✓", "✓", "✓"],
            ["analyst", "✓", "✓", "✓", "—", "✓", "—", "—"],
            ["entrepreneur", "✓", "✓", "—", "—", "✓", "✓", "—"],
            ["investor", "—", "—", "—", "✓", "✓", "✓", "—"],
            ["general_public", "—", "—", "—", "—", "✓ (view)", "—", "—"],
        ],
        col_widths=[1.2, 0.8, 0.7, 0.9, 0.9, 0.7, 0.9, 0.7],
    )
    _para(doc, (
        "The role_home_url() function determines the home page for each user after "
        "authentication. Sensitive views use LoginRequiredMixin in combination with "
        "RoleRequiredMixin to ensure double verification."
    ))


def _endpoints(doc):
    _heading(doc, "7. Endpoint Reference", level=1)
    _para(doc, (
        "The following table lists all endpoints available on the platform, "
        "organized by functional domain."
    ))

    _heading(doc, "Authentication", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["GET/POST", "/login/", "Login page and processing"],
            ["GET", "/logout/", "Log out"],
            ["GET/POST", "/register/", "Registration page and processing"],
            ["POST", "/set-language/", "Change the interface language"],
        ],
        col_widths=[0.8, 2.0, 3.7],
    )

    _heading(doc, "Pitch Analysis", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["GET/POST", "/analyze/form/", "Pitch form and submission"],
            ["POST", "/analyze/", "REST API analysis endpoint"],
            ["GET", "/results/<id>/", "Results page"],
            ["GET", "/results/<id>/pdf/", "Technical PDF report"],
            ["GET", "/results/<id>/pitch/pdf/", "Pitch deck PDF"],
        ],
        col_widths=[0.8, 2.5, 3.2],
    )

    _heading(doc, "Explainer Video", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["POST", "/results/<id>/video/generate/", "Start video generation"],
            ["POST", "/results/<id>/video/detect-gender/", "Detect presenter's gender"],
            ["GET", "/results/<id>/video/progress/<job_id>/", "Video progress polling"],
        ],
        col_widths=[0.8, 3.0, 2.7],
    )

    _heading(doc, "Batch Processing", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["POST", "/batch/analyze/", "Submit a CSV for batch analysis"],
            ["GET", "/batch/status/<batch_id>/", "Batch processing status"],
            ["GET", "/batch/results/<batch_id>/", "Download results as CSV"],
        ],
        col_widths=[0.8, 2.5, 3.2],
    )

    _heading(doc, "Model Management", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["GET", "/models/", "Model management panel"],
            ["POST", "/model/retrain/", "Start model training"],
            ["GET", "/models/training/progress/<job_id>/", "Training progress"],
            ["GET", "/training/status/<task_id>/", "Celery task status"],
        ],
        col_widths=[0.8, 2.7, 3.0],
    )

    _heading(doc, "Idea Builder and Connections", level=2)
    _table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["GET/POST", "/pitch/builder/", "Idea form and submission"],
            ["GET", "/pitch/builder/<id>/", "Idea detail and editing"],
            ["GET", "/pitch/builder/<id>/pdf/", "Export idea as PDF"],
            ["GET", "/ideas/", "Public idea marketplace"],
            ["GET", "/ideas/<id>/", "Public idea detail"],
            ["POST", "/ideas/<id>/feedback/", "Submit feedback on an idea"],
            ["POST", "/investors/interest/<id>/", "Express interest in a startup"],
            ["GET", "/connections/", "Connection hub"],
            ["POST", "/connections/<id>/update/", "Update connection status"],
        ],
        col_widths=[0.8, 2.5, 3.2],
    )


def _pipeline_ml(doc):
    _heading(doc, "8. Machine Learning Pipeline", level=1)
    _para(doc, (
        "StartupScan's scoring engine is a supervised machine learning pipeline, "
        "trained on historical startup pitch data. "
        "Each stage of the pipeline is described below."
    ))

    _heading(doc, "8.1. Preprocessing and Feature Engineering", level=2)
    _bullet(doc, [
        "Pitch text: TF-IDF vectorization with n-grams of 1 to 2 tokens.",
        "Financial data: normalization with StandardScaler (revenue, growth, "
        "profit margin, burn rate).",
        "Financial health feature: composite metric calculated from growth, "
        "margin, and revenue.",
        "Data augmentation: 60x factor with Gaussian jitter to enrich "
        "scarce datasets.",
    ])

    _heading(doc, "8.2. Ensemble Model", level=2)
    _para(doc, (
        "The model uses an ensemble of three base estimators with soft voting:"
    ))
    _bullet(doc, [
        "Random Forest Classifier (scikit-learn).",
        "Gradient Boosting Classifier (scikit-learn).",
        "Extra Trees Classifier (scikit-learn).",
    ])
    _para(doc, (
        "As an alternative, the XGBoost Classifier can be activated for larger datasets. "
        "Cross-validation uses 5-fold KFold for unbiased performance estimation."
    ))

    _heading(doc, "8.3. Model Output", level=2)
    _bullet(doc, [
        "Success score: continuous value from 0 to 10.",
        "Confidence: percentage derived from the dispersion among the ensemble's estimators.",
        "Categories: eight dimensions individually evaluated based on the "
        "features most relevant to each dimension.",
        "Recommendations: interpretable text generated based on the lowest-scoring categories.",
    ])

    _heading(doc, "8.4. GPT Integration", level=2)
    _para(doc, (
        "When the OPENAI_API_KEY variable is configured, the system can use "
        "GPT as an alternative analysis engine. The analyze_with_gpt() function sends the "
        "consolidated pitch to the OpenAI API and processes the response in the same "
        "structured format as the local model. If the API is unavailable or fails, "
        "the system automatically falls back to the local model without user intervention."
    ))

    _heading(doc, "8.5. Model Lifecycle Management", level=2)
    _para(doc, (
        "The active model is managed by the model_registry.py module, which maintains a "
        "JSON metadata file with the name and path of the active model. Newly trained models "
        "are persisted as .pkl files via joblib. Activating a new model "
        "immediately updates the registry, affecting all subsequent analyses."
    ))


def _instalacao(doc):
    _heading(doc, "9. Installation and Configuration", level=1)

    _heading(doc, "9.1. Prerequisites", level=2)
    _table(doc,
        ["Software", "Minimum version", "Required", "Note"],
        [
            ["Python", "3.10", "Yes", "3.11 or 3.12 recommended"],
            ["pip", "23.x", "Yes", "Included with Python"],
            ["Git", "2.x", "Yes", "To clone the repository"],
            ["Redis", "7.x", "No*", "Required for Celery (asynchronous jobs)"],
            ["FFmpeg", "6.x", "No*", "Required for local video generation"],
            ["Docker", "24.x", "No*", "For containerized execution"],
        ],
        col_widths=[1.2, 1.0, 1.0, 3.3],
    )
    _para(doc, (
        "* Optional for basic operation (evaluation, PDF). "
        "Redis and FFmpeg are required for local video and asynchronous processing."
    ), italic=True)

    _heading(doc, "9.2. Local Setup", level=2)
    _numbered(doc, [
        "Clone the repository: git clone https://github.com/rickdeu/startupscan-backend.git",
        "Create a virtual environment: python -m venv .venv",
        "Activate the virtual environment: source .venv/bin/activate (Linux/macOS) "
        "or .venv\\Scripts\\activate (Windows)",
        "Install dependencies: pip install -r requirements.txt",
        "Create a .env file with the required environment variables (see 9.3).",
        "Apply migrations: python manage.py migrate",
        "Create an administrator account: python manage.py createsuperuser",
        "Collect static files: python manage.py collectstatic --noinput",
        "(Optional) Train an initial model: python manage.py train_model "
        "--model-output ai_models/pitch_model.pkl",
        "Start the server: python manage.py runserver 0.0.0.0:8000",
    ])

    _heading(doc, "9.3. Environment Variables", level=2)
    _para(doc, "Required variables:", bold=True, space_after=2)
    _table(doc,
        ["Variable", "Description", "Example"],
        [
            ["SECRET_KEY", "Django secret key (required in production)",
             "django-insecure-..."],
            ["DJANGO_DEBUG", "Debug mode: 1 for dev, 0 for prod", "1"],
        ],
        col_widths=[1.8, 2.7, 2.0],
    )
    _para(doc, "Database variables (for PostgreSQL):", bold=True, space_after=2)
    _table(doc,
        ["Variable", "Description", "Example"],
        [
            ["DATABASE_URL", "Full PostgreSQL connection URL",
             "postgres://user:pass@host:5432/db"],
            ["POSTGRES_USER", "PostgreSQL user", "startupscan"],
            ["POSTGRES_PASSWORD", "PostgreSQL password", "password123"],
            ["POSTGRES_DB", "Database name", "startupscan"],
            ["POSTGRES_HOST", "PostgreSQL server host", "localhost"],
            ["POSTGRES_PORT", "PostgreSQL port", "5432"],
        ],
        col_widths=[1.8, 2.2, 2.5],
    )
    _para(doc, "External API variables:", bold=True, space_after=2)
    _table(doc,
        ["Variable", "Effect if absent"],
        [
            ["OPENAI_API_KEY", "System uses exclusively the local ML model"],
            ["OPENAI_MODEL", "Uses gpt-4.1-mini as the GPT model"],
            ["DID_API_KEY", "Video generation uses local mode (moviepy + TTS)"],
            ["DID_API_BASE_URL", "Uses https://api.d-id.com as the endpoint"],
            ["EDGE_TTS_VOICE_PT_AO", "Uses the default Portuguese edge-tts voice"],
            ["WHISPER_MODEL", "Uses the 'base' model for audio transcription"],
        ],
        col_widths=[2.2, 4.3],
    )

    _heading(doc, "9.4. Running with Docker Compose", level=2)
    _para(doc, (
        "The docker-compose.yml file at the project root brings up the "
        "full stack with a single command:"
    ))
    _bullet(doc, [
        "web: Django application via Gunicorn on port 8000.",
        "db: PostgreSQL 15 on port 5432.",
        "redis: Redis 7 on port 6379.",
        "celery-worker: asynchronous task processing.",
        "celery-beat: scheduling of periodic tasks.",
    ])
    _para(doc, "Start command: docker-compose up -d")
    _para(doc, "Stop command: docker-compose down")
    _para(doc, "Remove all data: docker-compose down -v")

    _heading(doc, "9.5. Deployment on Render", level=2)
    _para(doc, (
        "The project is configured for continuous deployment on the Render.com platform "
        "through the render.yaml file and the GitHub Actions workflow at "
        ".github/workflows/deploy-render-main.yml. "
        "Deployment is automatically triggered on every push to the main branch, "
        "after configuring the RENDER_DEPLOY_HOOK_URL secret in the GitHub repository."
    ))


def _testes(doc):
    _heading(doc, "10. Testing and Validation", level=1)

    _heading(doc, "10.1. Automated Tests", level=2)
    _para(doc, (
        "The automated test suite is implemented in startupscan_api/tests.py "
        "and covers the application's main flows. To run the tests:"
    ))
    _bullet(doc, [
        "python manage.py test — runs the entire test suite.",
        "python manage.py check — checks the Django system configuration.",
    ])

    _heading(doc, "10.2. Functional Validation Checklist", level=2)
    _para(doc, (
        "After installation or after significant code changes, "
        "it is recommended to validate the following flows:"
    ))
    _numbered(doc, [
        "Registration and authentication with each of the five roles.",
        "Pitch submission with plain text and verification of the generated score.",
        "Pitch submission with a PDF file and verification of text extraction.",
        "Download of the technical PDF report.",
        "Pitch deck PDF generation in automatic mode.",
        "Pitch deck PDF generation in premium mode (at least one template).",
        "Video generation in local_only mode.",
        "Video generation progress polling (verify updates).",
        "Model training via the panel and activation of the new model.",
        "Model training progress polling.",
        "Idea submission in the builder and export as PDF.",
        "Publishing an idea and submitting feedback from a general public account.",
        "Full connection flow: expressing interest → entrepreneur's reply.",
    ])

    _heading(doc, "10.3. Troubleshooting", level=2)
    _table(doc,
        ["Problem", "Likely cause", "Solution"],
        [
            ["SECRET_KEY not defined",
             "DJANGO_DEBUG=0 without SECRET_KEY in .env",
             "Add SECRET_KEY to .env or set DJANGO_DEBUG=1"],
            ["D-ID video fails",
             "Invalid API key, no credits, or image not accessible via HTTPS",
             "Check DID_API_KEY and credits; test with local_only mode"],
            ["PDF not generated",
             "ReportLab not installed or MEDIA_ROOT without write permission",
             "pip install reportlab; check permissions on the media/ directory"],
            ["GPT not used",
             "OPENAI_API_KEY missing or invalid",
             "Set OPENAI_API_KEY in .env; the system uses the local model as fallback"],
            ["Celery not processing jobs",
             "Redis is not running",
             "Start Redis (redis-server) and the Celery worker"],
            ["Submission overlay persists",
             "Browser cache",
             "Clear browser cache (Ctrl+Shift+R)"],
        ],
        col_widths=[1.5, 2.0, 3.0],
    )


def _conclusao(doc):
    _heading(doc, "11. Conclusion", level=1)
    _para(doc, (
        "The StartupScan project proved to be technically viable and functionally complete. "
        "The platform successfully implements the full startup evaluation cycle — from multimodal "
        "data ingestion to the production of communication artifacts — and integrates a diverse "
        "set of cutting-edge technologies in machine learning, natural language processing, "
        "video synthesis, and document generation."
    ))
    _para(doc, (
        "The project applies, in a real context, a broad range of engineering practices: "
        "web software architecture, RESTful API development, implementation of "
        "machine learning pipelines, asynchronous task processing, relational database "
        "management, and DevOps practices with Docker and CI/CD."
    ))
    _para(doc, (
        "The main technical challenges encountered during development included: "
        "normalizing multimodal inputs with varying formats and quality, "
        "calibrating the ML model with limited-size datasets (solved through data "
        "augmentation), integrating external APIs with asynchronous behavior "
        "(D-ID, OpenAI), and implementing an efficient polling system "
        "for long-running jobs without degrading the user experience."
    ))
    _para(doc, (
        "As future work, the following opportunities for evolution have been identified: "
        "integration of more recent large language models (LLMs) for deeper "
        "semantic analysis; implementation of a recommendation system "
        "to connect entrepreneurs with investors based on sector preferences; "
        "a metrics and analytics dashboard for administrators; and support for multiple "
        "languages in artifact generation."
    ))
    _para(doc, (
        "In summary, StartupScan represents a concrete contribution to the modernization "
        "of the startup evaluation ecosystem, with potential application in accelerators, "
        "investment funds, and entrepreneurship programs in the Angolan and African context."
    ))


def _referencias(doc):
    _heading(doc, "12. References", level=1)
    refs = [
        ("Django Software Foundation", "Django Web Framework", "2024",
         "https://www.djangoproject.com/"),
        ("Tom Christie", "Django REST Framework", "2024",
         "https://www.django-rest-framework.org/"),
        ("Pedregosa, F. et al.", "Scikit-learn: Machine Learning in Python. "
         "Journal of Machine Learning Research, 12, 2825–2830.", "2011", "—"),
        ("Chen, T. & Guestrin, C.", "XGBoost: A Scalable Tree Boosting System. "
         "Proceedings of the 22nd ACM SIGKDD.", "2016", "—"),
        ("OpenAI", "GPT-4 Technical Report", "2024", "https://openai.com/research/gpt-4"),
        ("D-ID", "D-ID API Documentation", "2024", "https://docs.d-id.com/"),
        ("Radford, A. et al.", "Robust Speech Recognition via Large-Scale Weak Supervision "
         "(Whisper)", "2022", "https://openai.com/research/whisper"),
        ("Zulko", "MoviePy: Video Editing with Python", "2024",
         "https://zulko.github.io/moviepy/"),
        ("ReportLab", "ReportLab PDF Library", "2024", "https://www.reportlab.com/"),
        ("Docker Inc.", "Docker Documentation", "2024", "https://docs.docker.com/"),
        ("Render", "Render Documentation", "2024", "https://render.com/docs"),
        ("Celery Project", "Celery: Distributed Task Queue", "2024",
         "https://docs.celeryq.dev/"),
    ]
    for i, (authors, title, year, url) in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        r1 = p.add_run(f"[{i}] {authors}. ")
        _set_font(r1, size=11)
        r2 = p.add_run(f"{title}. ")
        _set_font(r2, size=11, italic=True)
        r3 = p.add_run(f"{year}.")
        _set_font(r3, size=11)
        if url != "—":
            r4 = p.add_run(f" Available at: {url}")
            _set_font(r4, size=11)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build():
    os.makedirs(DOCS_DIR, exist_ok=True)
    doc = Document()
    _set_margins(doc, top=1.1, bottom=1.0, left=1.25, right=1.0)
    _add_page_numbers(doc)

    _capa(doc)
    _resumo(doc)
    _indice(doc)
    _introducao(doc)
    _page_break(doc)
    _contexto_objetivos(doc)
    _page_break(doc)
    _arquitectura(doc)
    _page_break(doc)
    _modelos_dados(doc)
    _page_break(doc)
    _funcionalidades(doc)
    _page_break(doc)
    _controlo_acesso(doc)
    _page_break(doc)
    _endpoints(doc)
    _page_break(doc)
    _pipeline_ml(doc)
    _page_break(doc)
    _instalacao(doc)
    _page_break(doc)
    _testes(doc)
    _page_break(doc)
    _conclusao(doc)
    _page_break(doc)
    _referencias(doc)

    doc.save(OUTPUT_PATH)
    print(f"Report generated at: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build()
