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

    elevator_pitch = (
        f"{one_liner} Resolvemos o problema de {target_customer} com uma solução prática e escalável. "
        f"Nosso modelo de negócio ({business_model}) permite crescimento sustentável, "
        f"com diferencial em {competitive_advantage or 'execução e foco no cliente'}."
    )

    script_3min = [
        "Abertura: contextualize o problema e impacto atual no mercado.",
        f"Problema: {problem}",
        f"Solução: {solution}",
        f"Mercado e cliente-alvo: {target_customer}. {market_size or 'Mercado em expansão e com espaço para liderança.'}",
        f"Modelo de negócio e tração: {business_model}. {traction or 'Validação inicial em andamento.'}",
        f"Equipe e execução: {team or 'Equipe multidisciplinar com foco em entrega.'}",
        f"Pedido de investimento: {funding_goal or 'Rodada seed para acelerar escala.'}",
        f"Uso de fundos e fecho: {use_of_funds or 'Expansão comercial, produto e operação.'}",
    ]

    pitch_deck = [
        {"slide": 1, "title": "Abertura", "bullets": [one_liner, "Visão de longo prazo da startup"]},
        {"slide": 2, "title": "Problema", "bullets": [problem, "Dor real e recorrente do mercado"]},
        {"slide": 3, "title": "Solução", "bullets": [solution, "Entrega clara de valor ao cliente"]},
        {"slide": 4, "title": "Mercado", "bullets": [target_customer, market_size or "Mercado em crescimento"]},
        {"slide": 5, "title": "Modelo de Negócio", "bullets": [business_model, competitive_advantage or "Diferencial competitivo sustentável"]},
        {"slide": 6, "title": "Tração", "bullets": [traction or "KPIs iniciais em evolução", "Estratégia de crescimento"]},
        {"slide": 7, "title": "Equipe", "bullets": [team or "Time fundador comprometido", "Capacidade de execução"]},
        {"slide": 8, "title": "Captação", "bullets": [funding_goal or "Meta de investimento", use_of_funds or "Plano de uso do capital"]},
    ]

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
        "elevator_pitch": elevator_pitch,
        "script_3min": script_3min,
        "pitch_deck": pitch_deck,
        "engine_used": "local",
    }


def _normalize_payload(data: dict, engine_used: str) -> dict:
    data = data if isinstance(data, dict) else {}
    data.setdefault("title", "Pitch de Negócio")
    data.setdefault("slogan", "")
    data.setdefault("sections", [])
    data.setdefault("investment", {})
    data.setdefault("closing", "")
    data.setdefault("elevator_pitch", "")
    data.setdefault("script_3min", [])
    data.setdefault("pitch_deck", [])
    data.setdefault("engine_used", engine_used)
    return data


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
                        "Transforme os dados da ideia em um pitch completo para apresentação em evento e reunião com investidores. "
                        "Responda em JSON com campos: "
                        "title, slogan, sections(list{title,content}), investment({funding_goal,use_of_funds}), "
                        "elevator_pitch, script_3min(lista de tópicos), pitch_deck(lista com slide,title,bullets), closing."
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
                    return _normalize_payload(data, "gpt")
            except Exception:
                # Fallback silencioso para modo local quando GPT falhar.
                pass

    return _normalize_payload(_local_pitch_fallback(idea_data), "local")


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

    elevator_pitch = pitch_payload.get("elevator_pitch", "")
    if elevator_pitch:
        story.append(Paragraph("<b>Elevator Pitch (60-90 segundos)</b>", styles["Heading3"]))
        story.append(Paragraph(elevator_pitch, styles["BodyText"]))
        story.append(Spacer(1, 0.25 * cm))

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

    script_3min = pitch_payload.get("script_3min", []) or []
    if script_3min:
        story.append(Paragraph("<b>Roteiro para apresentação de 3 minutos</b>", styles["Heading3"]))
        for idx, item in enumerate(script_3min, start=1):
            story.append(Paragraph(f"{idx}. {item}", styles["BodyText"]))
        story.append(Spacer(1, 0.3 * cm))

    deck = pitch_payload.get("pitch_deck", []) or []
    if deck:
        story.append(Paragraph("<b>Estrutura sugerida de Pitch Deck</b>", styles["Heading3"]))
        deck_rows = [["Slide", "Título", "Pontos-chave"]]
        for slide in deck:
            bullets = slide.get("bullets", []) or []
            bullets_text = " • ".join(str(b) for b in bullets if b)
            deck_rows.append(
                [
                    str(slide.get("slide", "")),
                    str(slide.get("title", "")),
                    bullets_text or "Sem pontos informados",
                ]
            )
        deck_table = Table(deck_rows, colWidths=[1.5 * cm, 4.5 * cm, 10 * cm])
        deck_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(deck_table)
        story.append(Spacer(1, 0.3 * cm))

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
