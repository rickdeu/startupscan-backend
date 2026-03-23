import json
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _local_pitch_fallback(idea_data: dict) -> dict:
    startup_name = idea_data.get("startup_name", "Startup")
    one_liner = idea_data.get("one_liner", "").strip() or (
        f"{startup_name} transforma um problema crítico em oportunidade de crescimento."
    )
    problem = idea_data.get("problem", "")
    solution = idea_data.get("solution", "")
    target_customer = idea_data.get("target_customer", "")
    business_model = idea_data.get("business_model", "")
    competitive_advantage = idea_data.get("competitive_advantage", "")
    traction = idea_data.get("traction", "")
    team = idea_data.get("team", "")
    funding_goal = idea_data.get("funding_goal", "")
    use_of_funds = idea_data.get("use_of_funds", "")
    market_size = idea_data.get("market_size", "")
    call_to_action = idea_data.get("call_to_action", "")

    return {
        "title": f"Pitch de Negócio - {startup_name}",
        "slogan": one_liner,
        "sections": [
            {"title": "Problema", "content": problem},
            {"title": "Solução", "content": solution},
            {"title": "Cliente-Alvo", "content": target_customer},
            {"title": "Modelo de Negócio", "content": business_model},
            {"title": "Tamanho de Mercado", "content": market_size or "Mercado em validação e expansão."},
            {"title": "Diferencial Competitivo", "content": competitive_advantage or "Posicionamento orientado a execução e velocidade."},
            {"title": "Tração", "content": traction or "Tração inicial em desenvolvimento com foco em validação contínua."},
            {"title": "Equipe", "content": team or "Equipe fundadora comprometida com execução disciplinada."},
        ],
        "investment": {
            "funding_goal": funding_goal or "Captação seed para acelerar crescimento.",
            "use_of_funds": use_of_funds or "Produto, aquisição de clientes e fortalecimento operacional.",
        },
        "closing": call_to_action or "Estamos prontos para uma reunião de aprofundamento com investidores estratégicos.",
        "engine_used": "local",
    }


def generate_pitch_from_idea(idea_data: dict, model_source: str = "local") -> dict:
    """
    Gera pitch estruturado a partir da ideia de negócio.
    Retorna payload pronto para renderização/exportação.
    """
    model_source = (model_source or "local").strip().lower()
    if model_source not in {"local", "gpt"}:
        model_source = "local"

    if model_source == "gpt":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
                client = OpenAI(api_key=api_key)
                payload = {
                    "task": (
                        "Transforme os dados da ideia em um pitch estruturado para investidores. "
                        "Responda em JSON com campos: title, slogan, sections(list{title,content}), "
                        "investment({funding_goal,use_of_funds}), closing."
                    ),
                    "idea_data": idea_data,
                }
                response = client.chat.completions.create(
                    model=model_name,
                    temperature=0.25,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "Você é especialista em storytelling e captação para startups."},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                )
                data = json.loads(response.choices[0].message.content)
                if isinstance(data, dict):
                    data.setdefault("engine_used", "gpt")
                    data.setdefault("sections", [])
                    data.setdefault("investment", {})
                    data.setdefault("closing", "")
                    return data
            except Exception:
                # Fallback silencioso para modo local quando GPT falhar.
                pass

    return _local_pitch_fallback(idea_data)


def export_pitch_pdf(pitch_payload: dict, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PitchTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=9,
    )
    subtitle_style = ParagraphStyle(
        "PitchSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )

    story = []
    story.append(Paragraph(pitch_payload.get("title", "Pitch de Negócio"), title_style))
    story.append(
        Paragraph(
            f"Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')} "
            f"| Motor: {pitch_payload.get('engine_used', 'local')}",
            subtitle_style,
        )
    )
    story.append(Paragraph(f"<b>Slogan:</b> {pitch_payload.get('slogan', '')}", styles["BodyText"]))
    story.append(Spacer(1, 0.4 * cm))

    for section in pitch_payload.get("sections", []):
        title = section.get("title", "Seção")
        content = section.get("content", "")
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
        story.append(Paragraph(content or "Sem conteúdo informado.", styles["BodyText"]))
        story.append(Spacer(1, 0.25 * cm))

    investment = pitch_payload.get("investment", {}) or {}
    story.append(Paragraph("<b>Estratégia de Captação</b>", styles["Heading3"]))
    inv_table = Table(
        [
            ["Meta de captação", investment.get("funding_goal", "Não informado")],
            ["Uso do capital", investment.get("use_of_funds", "Não informado")],
        ],
        colWidths=[5 * cm, 11 * cm],
    )
    inv_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(inv_table)
    story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("<b>Fecho</b>", styles["Heading3"]))
    story.append(Paragraph(pitch_payload.get("closing", ""), styles["BodyText"]))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(story)
    return output_path
