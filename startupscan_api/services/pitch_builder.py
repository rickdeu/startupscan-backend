import json
import os
import hashlib
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def _build_pitch_uniqueness_key(idea_data: dict) -> str:
    raw = json.dumps(
        {
            "startup_name": idea_data.get("startup_name", ""),
            "problem": idea_data.get("problem", ""),
            "solution": idea_data.get("solution", ""),
            "target_customer": idea_data.get("target_customer", ""),
            "business_model": idea_data.get("business_model", ""),
            "model_source": idea_data.get("model_source", ""),
            "created_hint": idea_data.get("created_at", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


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
    uniqueness_key = _build_pitch_uniqueness_key(idea_data)
    tone_variants = [
        "foco em crescimento disciplinado",
        "foco em eficiência operacional com escala",
        "foco em diferenciação de mercado e execução comercial",
        "foco em tração previsível e governança para captação",
    ]
    variant = tone_variants[int(uniqueness_key, 16) % len(tone_variants)]

    elevator_pitch = (
        f"{one_liner} Resolvemos o problema de {target_customer} com uma solução prática e escalável. "
        f"Nosso modelo de negócio ({business_model}) permite crescimento sustentável, "
        f"com diferencial em {competitive_advantage or 'execução e foco no cliente'}. "
        f"Abordagem estratégica: {variant}."
    )

    script_3min = [
        "Abertura: contextualize o problema e impacto atual no mercado.",
        f"Problema: {problem}",
        f"Solução: {solution}",
        f"Mercado e cliente-alvo: {target_customer}. {market_size or 'Mercado em expansão e com espaço para liderança.'}",
        f"Modelo de negócio e tração: {business_model}. {traction or 'Validação inicial em andamento.'} Ênfase: {variant}.",
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
        "narrative_uniqueness_key": uniqueness_key,
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
    data.setdefault("narrative_uniqueness_key", "")
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
                        "elevator_pitch, script_3min(lista de tópicos), pitch_deck(lista com slide,title,bullets), closing. "
                        "O roteiro precisa ser único para esta startup e não pode reutilizar texto padrão de outras startups."
                    ),
                    "idea_data": idea_data,
                    "uniqueness_key": _build_pitch_uniqueness_key(idea_data),
                }
                response = client.chat.completions.create(
                    model=model_name,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Você é especialista em storytelling e captação para startups. "
                                "Cada roteiro deve ser exclusivo para a startup analisada."
                            ),
                        },
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                )
                data = json.loads(response.choices[0].message.content)
                if isinstance(data, dict):
                    data["narrative_uniqueness_key"] = payload["uniqueness_key"]
                    return _normalize_payload(data, "gpt")
            except Exception:
                # Fallback silencioso para modo local quando GPT falhar.
                pass

    return _normalize_payload(_local_pitch_fallback(idea_data), "local")


def _safe_str(value, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text or default


def _wrap_text_lines(text: str, max_chars: int = 80) -> list[str]:
    text = " ".join((_safe_str(text, "")).split())
    if not text:
        return []
    words = text.split(" ")
    lines = []
    current = []
    current_len = 0
    for word in words:
        add_len = len(word) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += add_len
    if current:
        lines.append(" ".join(current))
    return lines


def _truncate_text(text: str, max_chars: int = 340) -> str:
    text = _safe_str(text, "")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut or text[:max_chars]).rstrip() + "..."


def _palette_for_slide(index: int) -> dict:
    palettes = [
        {
            "bg": colors.HexColor("#060B1A"),
            "band": colors.HexColor("#1D4ED8"),
            "card": colors.HexColor("#0F172A"),
            "text": colors.HexColor("#F8FAFC"),
            "muted": colors.HexColor("#BFDBFE"),
            "accent": colors.HexColor("#22D3EE"),
            "shape1": colors.HexColor("#172554"),
            "shape2": colors.HexColor("#1E3A8A"),
        },
        {
            "bg": colors.HexColor("#0B1020"),
            "band": colors.HexColor("#7C3AED"),
            "card": colors.HexColor("#111827"),
            "text": colors.HexColor("#F8FAFC"),
            "muted": colors.HexColor("#DDD6FE"),
            "accent": colors.HexColor("#F472B6"),
            "shape1": colors.HexColor("#312E81"),
            "shape2": colors.HexColor("#4C1D95"),
        },
        {
            "bg": colors.HexColor("#09121B"),
            "band": colors.HexColor("#0EA5E9"),
            "card": colors.HexColor("#0F172A"),
            "text": colors.HexColor("#F8FAFC"),
            "muted": colors.HexColor("#BAE6FD"),
            "accent": colors.HexColor("#2DD4BF"),
            "shape1": colors.HexColor("#164E63"),
            "shape2": colors.HexColor("#155E75"),
        },
    ]
    return palettes[index % len(palettes)]


def _draw_background(pdf: canvas.Canvas, width: float, height: float, palette: dict):
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    pdf.setFillColor(palette["shape1"])
    pdf.circle(width * 0.92, height * 0.82, 90, stroke=0, fill=1)
    pdf.setFillColor(palette["shape2"])
    pdf.circle(width * 0.84, height * 0.68, 130, stroke=0, fill=1)
    pdf.setFillColor(palette["band"])
    pdf.rect(0, height - 42, width, 42, stroke=0, fill=1)


def _draw_footer(
    pdf: canvas.Canvas,
    width: float,
    page_number: int,
    total_pages: int,
    engine_used: str,
    uniqueness_key: str,
    palette: dict,
):
    footer_text = (
        f"StartupScan Pitch Deck | Motor: {engine_used} | "
        f"ID: {uniqueness_key or 'manual'} | Slide {page_number}/{total_pages}"
    )
    pdf.setFillColor(palette["muted"])
    pdf.setFont("Helvetica", 9)
    pdf.drawString(28, 16, footer_text)


def _draw_cover_slide(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    title: str,
    slogan: str,
    startup_name: str,
    subtitle: str,
    palette: dict,
):
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 35)
    y = height - 130
    for line in _wrap_text_lines(title, max_chars=32)[:2]:
        pdf.drawString(52, y, line)
        y -= 40

    pdf.setFillColor(palette["muted"])
    pdf.setFont("Helvetica", 15)
    for line in _wrap_text_lines(_truncate_text(slogan, 180), max_chars=65)[:3]:
        pdf.drawString(52, y, line)
        y -= 22

    pdf.setFillColor(palette["card"])
    pdf.roundRect(52, 86, width - 104, 124, 16, stroke=0, fill=1)
    pdf.setFillColor(palette["accent"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(72, 183, "APRESENTACAO EXECUTIVA")
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica", 12)
    pdf.drawString(72, 160, f"Startup: {startup_name}")
    pdf.drawString(72, 140, subtitle)
    pdf.drawString(72, 120, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    initials = (_safe_str(startup_name, "ST")[:2]).upper()
    pdf.setFillColor(palette["band"])
    pdf.circle(width - 110, 148, 44, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    text_w = stringWidth(initials, "Helvetica-Bold", 22)
    pdf.drawString(width - 110 - (text_w / 2), 141, initials)


def _draw_visual_metrics(
    pdf: canvas.Canvas,
    title: str,
    width: float,
    y_start: float,
    card_height: float,
    palette: dict,
):
    seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:6], 16)
    labels = ["Impacto", "Escala", "Retorno"]
    levels = [
        40 + (seed % 56),
        40 + ((seed // 7) % 56),
        40 + ((seed // 13) % 56),
    ]
    x_base = width - 230
    bar_w = 42
    gap = 16
    max_h = card_height - 72

    pdf.setFillColor(palette["muted"])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x_base, y_start + card_height - 24, "Indicadores visuais")

    for idx, value in enumerate(levels):
        x = x_base + (idx * (bar_w + gap))
        h = max(18, max_h * (value / 100.0))
        pdf.setFillColor(colors.HexColor("#1F2937"))
        pdf.roundRect(x, y_start + 26, bar_w, max_h, 5, stroke=0, fill=1)
        pdf.setFillColor(palette["accent"])
        pdf.roundRect(x, y_start + 26, bar_w, h, 5, stroke=0, fill=1)
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(x + (bar_w / 2), y_start + 14, labels[idx])


def _draw_content_slide(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    bullets: list[str],
    palette: dict,
):
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 27)
    y = height - 100
    for line in _wrap_text_lines(_safe_str(title, "Slide"), max_chars=42)[:2]:
        pdf.drawString(52, y, line)
        y -= 34

    if subtitle:
        pdf.setFillColor(palette["muted"])
        pdf.setFont("Helvetica", 12)
        for line in _wrap_text_lines(_truncate_text(subtitle, 190), max_chars=72)[:2]:
            pdf.drawString(52, y, line)
            y -= 18

    card_x = 52
    card_y = 66
    card_w = width - 104
    card_h = height - 186

    pdf.setFillColor(palette["card"])
    pdf.roundRect(card_x, card_y, card_w, card_h, 16, stroke=0, fill=1)
    pdf.setFillColor(palette["band"])
    pdf.roundRect(card_x, card_y + card_h - 32, card_w, 32, 16, stroke=0, fill=1)

    left_x = card_x + 24
    left_y = card_y + card_h - 54
    pdf.setFillColor(palette["text"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left_x, left_y, "Pontos-chave")

    text_y = left_y - 24
    pdf.setFont("Helvetica", 11)
    for raw_bullet in bullets[:6]:
        bullet = _truncate_text(_safe_str(raw_bullet, "Sem informacao"), 180)
        wrapped = _wrap_text_lines(bullet, max_chars=56)[:3]
        if text_y < card_y + 30:
            break
        pdf.setFillColor(palette["accent"])
        pdf.circle(left_x + 2, text_y + 5, 2.4, stroke=0, fill=1)
        pdf.setFillColor(palette["text"])
        if wrapped:
            pdf.drawString(left_x + 12, text_y, wrapped[0])
            text_y -= 15
        for extra_line in wrapped[1:]:
            if text_y < card_y + 30:
                break
            pdf.drawString(left_x + 12, text_y, extra_line)
            text_y -= 14
        text_y -= 8

    _draw_visual_metrics(pdf, title, width, card_y, card_h, palette)


def _build_pitch_slides(pitch_payload: dict) -> list[dict]:
    slides = []
    title = _safe_str(pitch_payload.get("title"), "Pitch de Negocio")
    slogan = _safe_str(pitch_payload.get("slogan"), "Proposta de valor em evolucao.")
    startup_name = title.replace("Pitch de Negócio - ", "").replace("Pitch de Negocio - ", "").strip() or "Startup"

    slides.append(
        {
            "title": title,
            "subtitle": "Deck visual para apresentacao a investidores",
            "bullets": [slogan],
            "kind": "cover",
            "startup_name": startup_name,
        }
    )

    elevator = _safe_str(pitch_payload.get("elevator_pitch"), "")
    if elevator:
        slides.append(
            {
                "title": "Elevator Pitch",
                "subtitle": "Mensagem central em ate 90 segundos",
                "bullets": _wrap_text_lines(_truncate_text(elevator, 440), max_chars=95)[:5],
                "kind": "content",
            }
        )

    deck = pitch_payload.get("pitch_deck", []) or []
    for item in deck[:10]:
        title = _safe_str(item.get("title"), "Slide")
        bullets = [str(b).strip() for b in (item.get("bullets", []) or []) if str(b).strip()]
        if not bullets:
            bullets = ["Sem pontos informados para este slide."]
        slides.append(
            {
                "title": title,
                "subtitle": f"Slide {item.get('slide', '')}".strip(),
                "bullets": bullets,
                "kind": "content",
            }
        )

    if not deck:
        sections = pitch_payload.get("sections", []) or []
        for sec in sections[:8]:
            sec_title = _safe_str(sec.get("title"), "Secao")
            sec_content = _safe_str(sec.get("content"), "Sem conteudo informado.")
            slides.append(
                {
                    "title": sec_title,
                    "subtitle": "Resumo estrategico",
                    "bullets": _wrap_text_lines(_truncate_text(sec_content, 420), max_chars=95)[:5],
                    "kind": "content",
                }
            )

    investment = pitch_payload.get("investment", {}) or {}
    funding = _safe_str(investment.get("funding_goal"), "Nao informado")
    use_of_funds = _safe_str(investment.get("use_of_funds"), "Nao informado")
    slides.append(
        {
            "title": "Capitacao e Uso de Capital",
            "subtitle": "Plano financeiro para execucao e escala",
            "bullets": [f"Meta de captacao: {funding}", f"Uso do capital: {use_of_funds}"],
            "kind": "content",
        }
    )

    script = pitch_payload.get("script_3min", []) or []
    if script:
        timeline = [f"Passo {idx}: {item}" for idx, item in enumerate(script[:5], start=1)]
        slides.append(
            {
                "title": "Roteiro de Apresentacao",
                "subtitle": "Sequencia sugerida para apresentacao ao vivo",
                "bullets": timeline,
                "kind": "content",
            }
        )

    closing = _safe_str(
        pitch_payload.get("closing"),
        "Obrigado pela atencao. Estamos prontos para os proximos passos da captacao.",
    )
    slides.append(
        {
            "title": "Conclusao",
            "subtitle": "Mensagem final ao investidor",
            "bullets": _wrap_text_lines(_truncate_text(closing, 420), max_chars=90)[:5],
            "kind": "content",
        }
    )
    return slides


def export_pitch_pdf(pitch_payload: dict, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    slides = _build_pitch_slides(pitch_payload)
    page_size = landscape(A4)
    width, height = page_size

    pdf = canvas.Canvas(output_path, pagesize=page_size)
    engine_used = _safe_str(pitch_payload.get("engine_used"), "local")
    uniqueness_key = _safe_str(pitch_payload.get("narrative_uniqueness_key"), "")
    total_pages = len(slides)

    for idx, slide in enumerate(slides, start=1):
        palette = _palette_for_slide(idx - 1)
        _draw_background(pdf, width, height, palette)

        if slide.get("kind") == "cover":
            _draw_cover_slide(
                pdf=pdf,
                width=width,
                height=height,
                title=_safe_str(slide.get("title"), "Pitch Deck"),
                slogan=_safe_str((slide.get("bullets") or [""])[0], ""),
                startup_name=_safe_str(slide.get("startup_name"), "Startup"),
                subtitle=_safe_str(slide.get("subtitle"), ""),
                palette=palette,
            )
        else:
            _draw_content_slide(
                pdf=pdf,
                width=width,
                height=height,
                title=_safe_str(slide.get("title"), "Slide"),
                subtitle=_safe_str(slide.get("subtitle"), ""),
                bullets=[str(b) for b in (slide.get("bullets") or [])],
                palette=palette,
            )

        _draw_footer(pdf, width, idx, total_pages, engine_used, uniqueness_key, palette)
        pdf.showPage()

    pdf.save()
    return output_path
