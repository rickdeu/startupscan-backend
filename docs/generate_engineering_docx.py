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


def build_docx():
    os.makedirs(DOCS_DIR, exist_ok=True)

    doc = Document()
    doc.add_heading("Documentacao de Engenharia de Software", level=0)
    doc.add_paragraph("Plataforma Multimodal para Avaliacao e Pitch Automatizado de Startups")
    doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    doc.add_heading("1. Objetivo do sistema", level=1)
    doc.add_paragraph(
        "A plataforma automatiza a avaliacao de startups com entrada multimodal, "
        "score de potencial, relatorios tecnicos, video explicativo e pitch deck visual."
    )

    doc.add_heading("2. Funcionalidades implementadas", level=1)
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
        "A solucao utiliza Django + DRF no backend, templates responsivos no frontend, "
        "pipeline de IA para analise multimodal e servicos de exportacao de documentos."
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

    doc.add_heading("4. Guia de utilizacao", level=1)
    _add_numbered_list(
        doc,
        [
            "Aceder a pagina de Novo Pitch.",
            "Preencher informacoes da startup e sector.",
            "Submeter dados multimodais (texto, documento, audio, video, YouTube).",
            "Executar avaliacao com motor local ou GPT.",
            "Consultar resultado com score, categorias e recomendacoes.",
            "Opcionalmente gerar video IA no modo desejado.",
            "Gerar relatorio PDF tecnico da analise.",
            "Gerar pitch PDF com design automatico ou premium manual.",
        ],
    )

    doc.add_heading("5. Operacao e validacao", level=1)
    _add_bullet_list(
        doc,
        [
            "python3 manage.py check",
            "python3 manage.py test",
            "python3 docs/generate_engineering_pdf.py",
            "python3 docs/generate_engineering_docx.py",
        ],
    )

    doc.add_heading("6. Publicacao de documentacao", level=1)
    doc.add_paragraph(
        "A entrega operacional do projeto inclui envio da documentacao atualizada para o webhook Discord "
        "em formatos PDF e DOCX."
    )

    doc.save(DOCX_PATH)
    return DOCX_PATH


if __name__ == "__main__":
    path = build_docx()
    print(path)
