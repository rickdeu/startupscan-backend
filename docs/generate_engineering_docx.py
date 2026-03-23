import os
from datetime import datetime

from docx import Document
from docx.shared import Inches


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
ASSETS_DIR = os.path.join(DOCS_DIR, "assets")
DOCX_PATH = os.path.join(DOCS_DIR, "Documentacao_Engenharia_Software.docx")


def _add_bullet_list(document: Document, items: list[str]):
    for item in items:
        document.add_paragraph(item, style="List Bullet")


def _add_numbered_list(document: Document, items: list[str]):
    for item in items:
        document.add_paragraph(item, style="List Number")


def _add_table(document: Document, headers: list[str], rows: list[list[str]]):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Light List Accent 1"
    hdr = table.rows[0].cells
    for idx, header in enumerate(headers):
        hdr[idx].text = header
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = value
    return table


def build_docx():
    os.makedirs(DOCS_DIR, exist_ok=True)

    doc = Document()
    doc.add_heading("Documentacao de Engenharia de Software", level=0)
    doc.add_paragraph("StartupScan - versao completa e detalhada")
    doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    doc.add_heading("1. Resumo e objetivos", level=1)
    doc.add_paragraph(
        "O StartupScan e uma plataforma para avaliacao de startups com IA, projetada para reduzir tempo de analise, "
        "aumentar padronizacao do feedback e produzir artefatos executivos para tomada de decisao."
    )
    _add_bullet_list(
        doc,
        [
            "Receber pitch em formato multimodal.",
            "Gerar score e recomendacoes interpretaveis.",
            "Entregar relatorio tecnico, video IA e pitch deck visual.",
            "Suportar operacao continua com monitoramento de jobs.",
        ],
    )

    doc.add_heading("2. Escopo funcional implementado", level=1)
    _add_bullet_list(
        doc,
        [
            "Submissao multimodal (texto, documento, audio, video e YouTube).",
            "Analise de startup com score 0-10 e recomendacoes por categoria.",
            "Motor local e opcao GPT com fallback.",
            "Video IA no resultado (D-ID/local/hibrido) com progresso realtime.",
            "Pitch PDF estilo slides com design automatico por contexto.",
            "Pitch PDF com modo premium manual e template escolhido pelo usuario.",
            "Gestao de modelos com treino, retreino, ativacao e monitoramento realtime.",
            "Dashboards operacional e investidor.",
        ],
    )

    doc.add_heading("3. Arquitetura tecnica", level=1)
    doc.add_paragraph(
        "A solucao utiliza arquitetura modular com servicos especializados para analise, video e exportacao."
    )
    _add_table(
        doc,
        ["Camada", "Tecnologia", "Responsabilidade"],
        [
            ["Frontend", "Django Templates + JS", "Interface, formularios, dashboards e polling de progresso"],
            ["Backend", "Django + DRF", "Orquestracao, regras de negocio, rotas e seguranca"],
            ["IA", "scikit-learn + OpenAI", "Scoring, interpretabilidade e narrativa"],
            ["Video", "moviepy + D-ID", "Geracao de video IA e renderizacao local"],
            ["Documentacao", "reportlab + python-docx", "Exportacao PDF e DOCX"],
            ["Persistencia", "SQLite/PostgreSQL", "Analises, submissoes e metadata operacional"],
        ],
    )

    architecture_image = os.path.join(ASSETS_DIR, "arquitetura_plataforma.png")
    if os.path.exists(architecture_image):
        doc.add_paragraph("Diagrama de arquitetura:")
        doc.add_picture(architecture_image, width=Inches(6.4))

    flow_image = os.path.join(ASSETS_DIR, "fluxo_funcional.png")
    if os.path.exists(flow_image):
        doc.add_paragraph("Fluxo funcional:")
        doc.add_picture(flow_image, width=Inches(6.4))

    categories_image = os.path.join(ASSETS_DIR, "categorias_exemplo.png")
    if os.path.exists(categories_image):
        doc.add_paragraph("Exemplo de categorias de avaliacao:")
        doc.add_picture(categories_image, width=Inches(6.4))

    jobs_image = os.path.join(ASSETS_DIR, "fases_jobs.png")
    if os.path.exists(jobs_image):
        doc.add_paragraph("Fases de jobs assincromos:")
        doc.add_picture(jobs_image, width=Inches(6.4))

    doc.add_heading("4. Fluxos de negocio", level=1)
    doc.add_paragraph("Fluxo A - Avaliacao multimodal:")
    _add_numbered_list(
        doc,
        [
            "Receber entrada multimodal.",
            "Extrair e consolidar contexto.",
            "Executar inferencia local/GPT.",
            "Persistir resultado estruturado.",
            "Exibir score e recomendacoes.",
        ],
    )
    doc.add_paragraph("Fluxo B - Video IA:")
    _add_numbered_list(
        doc,
        [
            "Selecionar modo (auto/did_only/local_only).",
            "Criar job assincromo.",
            "Acompanhar progresso por endpoint.",
            "Persistir artefato e metadata.",
        ],
    )
    doc.add_paragraph("Fluxo C - Pitch deck PDF:")
    _add_numbered_list(
        doc,
        [
            "Construir narrativa do pitch.",
            "Selecionar modo de design (automatico/manual).",
            "Renderizar slides visuais.",
            "Entregar PDF para download.",
        ],
    )

    doc.add_heading("5. Endpoints principais", level=1)
    _add_table(
        doc,
        ["Endpoint", "Metodo", "Descricao"],
        [
            ["/analyze/form/", "GET/POST", "Formulario de avaliacao multimodal"],
            ["/results/<id>/", "GET", "Resultado completo da analise"],
            ["/results/<id>/pdf/", "GET", "Relatorio tecnico da analise"],
            ["/results/<id>/pitch/pdf/", "GET", "Pitch deck visual"],
            ["/results/<id>/video/generate/", "POST", "Inicia geracao de video"],
            ["/results/<id>/video/progress/<job_id>/", "GET", "Progresso do video"],
            ["/models/", "GET/POST", "Gestao e treino de modelos"],
            ["/investors/", "GET", "Dashboard investidor"],
        ],
    )

    doc.add_heading("6. Guia de utilizacao", level=1)
    _add_numbered_list(
        doc,
        [
            "Aceder a pagina de Novo Pitch.",
            "Preencher informacoes da startup e sector.",
            "Submeter dados multimodais (texto, documento, audio, video, YouTube).",
            "Executar avaliacao com motor local ou GPT.",
            "Consultar resultado com score, categorias e recomendacoes.",
            "Opcionalmente gerar video IA no modo desejado.",
            "Gerar relatorio PDF tecnico.",
            "Gerar pitch PDF em design automatico por contexto.",
            "Gerar pitch PDF em design premium manual (template escolhido).",
        ],
    )

    doc.add_heading("7. Operacao, testes e troubleshooting", level=1)
    _add_bullet_list(
        doc,
        [
            "python3 manage.py check",
            "python3 manage.py test",
            "python3 docs/generate_engineering_pdf.py",
            "python3 docs/generate_engineering_docx.py",
        ],
    )
    doc.add_paragraph("Checklist funcional minimo:")
    _add_bullet_list(
        doc,
        [
            "Submissao multimodal valida.",
            "Score e categorias no resultado.",
            "Video IA com barra de progresso.",
            "Pitch PDF com os dois modos de design.",
            "Download de relatorio tecnico.",
        ],
    )
    doc.add_paragraph("Troubleshooting rapido:")
    _add_bullet_list(
        doc,
        [
            "Falha D-ID: validar chave, creditos e URL HTTPS da imagem.",
            "Falha GPT: validar OPENAI_API_KEY e fallback local.",
            "Falha PDF/DOCX: validar dependencias e permissao de escrita.",
        ],
    )

    doc.add_heading("8. Publicacao de documentacao", level=1)
    doc.add_paragraph(
        "A entrega operacional do projeto inclui envio da documentacao atualizada para o webhook Discord "
        "em formatos PDF e DOCX."
    )

    doc.save(DOCX_PATH)
    return DOCX_PATH


if __name__ == "__main__":
    path = build_docx()
    print(path)
