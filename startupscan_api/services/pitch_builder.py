import json
import os
import hashlib
import colorsys
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


PITCH_DESIGN_MODE_AUTO = "auto_context"
PITCH_DESIGN_MODE_MANUAL = "manual_premium"

PITCH_DESIGN_MODE_CHOICES = [
    (PITCH_DESIGN_MODE_AUTO, "Design automático por contexto (atual)"),
    (PITCH_DESIGN_MODE_MANUAL, "Design premium manual (template escolhido pelo usuário)"),
]

PITCH_MANUAL_TEMPLATE_CHOICES = [
    ("orbit", "Orbit Premium"),
    ("grid", "Grid Executive"),
    ("wave", "Wave Smooth"),
    ("diagonal", "Diagonal Corporate"),
    ("aurora", "Aurora Glass"),
    ("ribbon", "Ribbon Stage"),
]


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
    return _enrich_pitch_payload_for_detailed_slides(data)


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


def _safe_sentence(text: str) -> str:
    sentence = " ".join(_safe_str(text, "").split())
    if not sentence:
        return ""
    if sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def _extract_startup_name(payload: dict) -> str:
    title = _safe_str(payload.get("title"), "")
    if " - " in title:
        candidate = title.split(" - ", 1)[-1].strip()
        if candidate:
            return candidate
    return _safe_str(payload.get("startup_name"), "Startup")


def _sections_map(payload: dict) -> dict:
    mapped = {}
    for section in (payload.get("sections") or []):
        if not isinstance(section, dict):
            continue
        key = _safe_str(section.get("title"), "").lower()
        if key:
            mapped[key] = _safe_str(section.get("content"), "")
    return mapped


def _detail_variant(unique_key: str) -> str:
    variants = [
        "execucao disciplinada e previsibilidade de resultados",
        "crescimento com governanca e eficiencia operacional",
        "diferenciacao competitiva com foco em receita recorrente",
        "escalabilidade sustentada por metricas e validacao comercial",
    ]
    if not unique_key:
        return variants[0]
    try:
        idx = int(unique_key, 16)
    except ValueError:
        idx = sum(ord(ch) for ch in unique_key)
    return variants[idx % len(variants)]


def _build_detail_context(payload: dict) -> dict:
    sections = _sections_map(payload)
    startup_name = _extract_startup_name(payload)
    problem = sections.get("problema") or _safe_str(payload.get("elevator_pitch"), "dor relevante de mercado")
    solution = sections.get("solucao") or sections.get("solução") or "solucao com proposta de valor clara"
    market = (
        sections.get("tamanho de mercado")
        or sections.get("mercado")
        or sections.get("cliente-alvo")
        or sections.get("cliente alvo")
        or "mercado em crescimento com espaco para lideranca"
    )
    traction = sections.get("tracao") or sections.get("tração") or "indicadores iniciais em consolidacao"
    model = sections.get("modelo de negocio") or sections.get("modelo de negócio") or "modelo replicavel e orientado a escala"
    slogan = _safe_str(
        payload.get("slogan"),
        f"{startup_name} transforma uma necessidade critica em crescimento sustentavel.",
    )
    return {
        "startup_name": startup_name,
        "problem": _safe_sentence(problem),
        "solution": _safe_sentence(solution),
        "market": _safe_sentence(market),
        "traction": _safe_sentence(traction),
        "model": _safe_sentence(model),
        "slogan": _safe_sentence(slogan),
    }


def _expand_slide_bullet(text: str, slide_title: str, context: dict, variant: str) -> str:
    startup = context["startup_name"]
    problem = context["problem"]
    solution = context["solution"]
    market = context["market"]
    traction = context["traction"]
    model = context["model"]

    base = _safe_sentence(text)
    if not base:
        base = (
            f"{startup} estrutura este tema com metas claras de produto, operacao e receita, "
            f"garantindo alinhamento entre estrategia e execucao."
        )
    if len(base) < 120:
        base = (
            f"{base} No contexto de {slide_title}, a startup prioriza {variant}, "
            "com responsaveis definidos, calendario de entrega e criterio de sucesso mensuravel."
        )
    if len(base) < 210:
        base = (
            f"{base} A leitura de mercado considera {market} e o plano de monetizacao combina {model}."
        )
    if len(base) < 290:
        base = (
            f"{base} O racional estrategico parte do problema central ({problem}) e conecta essa dor "
            f"a capacidade de entrega da solucao ({solution}), com sinais de tracao em evolucao ({traction})."
        )
    return _safe_sentence(_truncate_text(base, 340))


def _ensure_detailed_sections(payload: dict, context: dict, variant: str):
    sections = payload.get("sections") or []
    if not isinstance(sections, list):
        sections = []
    if not sections:
        sections = [
            {"title": "Problema", "content": context["problem"]},
            {"title": "Solucao", "content": context["solution"]},
            {"title": "Mercado", "content": context["market"]},
            {"title": "Modelo de Negocio", "content": context["model"]},
            {"title": "Tracao", "content": context["traction"]},
        ]

    enriched_sections = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = _safe_str(section.get("title"), "Secao")
        content = _safe_sentence(section.get("content"))
        if len(content) < 220:
            content = (
                f"{content} {context['startup_name']} desenvolve esta frente com {variant}, "
                "estabelecendo prioridades por ciclo trimestral, indicadores de desempenho e rotina de acompanhamento executivo. "
                "A execucao combina validacao de mercado, disciplina financeira e melhoria continua da proposta de valor."
            ).strip()
        enriched_sections.append({"title": title, "content": _safe_sentence(content)})
    payload["sections"] = enriched_sections


def _ensure_detailed_script(payload: dict, context: dict, variant: str):
    script = payload.get("script_3min") or []
    if not isinstance(script, list):
        script = []
    if not script:
        script = [
            "Abertura: contextualizar oportunidade e relevancia de mercado.",
            "Problema: detalhar dor principal e impacto financeiro para o cliente.",
            "Solucao: apresentar abordagem, diferencial e entrega de valor.",
            "Execucao: mostrar modelo operacional, GTM e ritmo de crescimento.",
            "Captacao: explicar uso de capital, marcos e governanca.",
            "Conclusao: reforcar tese de investimento e convite para proxima reuniao.",
        ]

    detailed = []
    for idx, line in enumerate(script[:8], start=1):
        sentence = _safe_sentence(line)
        if len(sentence) < 160:
            sentence = (
                f"{sentence} Neste passo {idx}, {context['startup_name']} evidencia {variant}, "
                "incluindo KPI alvo, prazo de execucao, risco principal e mitigacao prevista para proteger retorno do investidor."
            )
        detailed.append(_safe_sentence(sentence))
    payload["script_3min"] = detailed


def _ensure_detailed_deck(payload: dict, context: dict, variant: str):
    deck = payload.get("pitch_deck") or []
    if not isinstance(deck, list):
        deck = []
    if not deck:
        deck = [
            {"slide": 1, "title": "Abertura", "bullets": [context["slogan"]]},
            {"slide": 2, "title": "Problema", "bullets": [context["problem"]]},
            {"slide": 3, "title": "Solucao", "bullets": [context["solution"]]},
            {"slide": 4, "title": "Mercado", "bullets": [context["market"]]},
            {"slide": 5, "title": "Modelo de Negocio", "bullets": [context["model"]]},
            {"slide": 6, "title": "Tracao", "bullets": [context["traction"]]},
            {"slide": 7, "title": "Roadmap", "bullets": ["Marcos trimestrais e criterio de sucesso para escalar com seguranca."]},
            {"slide": 8, "title": "Captacao", "bullets": ["Tese de investimento, uso de capital e retorno esperado."]},
        ]

    enriched_deck = []
    for idx, raw_item in enumerate(deck[:12], start=1):
        item = raw_item if isinstance(raw_item, dict) else {}
        title = _safe_str(item.get("title"), f"Slide {idx}")
        bullets = [_safe_str(b, "") for b in (item.get("bullets") or []) if _safe_str(b, "")]
        if not bullets:
            bullets = [f"{title}: eixo prioritario para crescimento consistente e validacao comercial."]

        expanded = [_expand_slide_bullet(bullet, title, context, variant) for bullet in bullets[:5]]
        while len(expanded) < 4:
            expanded.append(
                _expand_slide_bullet(
                    f"{title}: frente adicional com plano de execucao, metricas e governanca de risco.",
                    title,
                    context,
                    variant,
                )
            )

        enriched_deck.append(
            {
                "slide": item.get("slide", idx),
                "title": title,
                "bullets": expanded[:6],
            }
        )
    payload["pitch_deck"] = enriched_deck


def _enrich_pitch_payload_for_detailed_slides(payload: dict) -> dict:
    context = _build_detail_context(payload)
    variant = _detail_variant(_safe_str(payload.get("narrative_uniqueness_key"), ""))

    _ensure_detailed_sections(payload, context, variant)
    _ensure_detailed_script(payload, context, variant)
    _ensure_detailed_deck(payload, context, variant)

    elevator = _safe_sentence(payload.get("elevator_pitch"))
    if len(elevator) < 260:
        elevator = (
            f"{elevator} {context['startup_name']} combina visao de mercado, execucao comercial e disciplina financeira "
            "para capturar demanda reprimida com crescimento previsivel, priorizando eficiencia de aquisicao e retencao."
        ).strip()
    payload["elevator_pitch"] = _safe_sentence(elevator)

    closing = _safe_sentence(payload.get("closing"))
    if len(closing) < 170:
        closing = (
            f"{closing} A startup apresenta tese clara de valor, plano operacional validavel e governanca para escalar com qualidade. "
            "O proximo passo proposto e uma reuniao tecnica para revisar diligencia, milestones e estrutura da rodada."
        ).strip()
    payload["closing"] = _safe_sentence(closing)
    return payload


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


def get_pitch_design_mode_choices() -> list[tuple[str, str]]:
    return list(PITCH_DESIGN_MODE_CHOICES)


def get_pitch_design_template_choices() -> list[tuple[str, str]]:
    return list(PITCH_MANUAL_TEMPLATE_CHOICES)


def normalize_pitch_design_options(design_mode: str | None, manual_template: str | None) -> tuple[str, str]:
    mode = _safe_str(design_mode, PITCH_DESIGN_MODE_AUTO).lower()
    valid_modes = {choice[0] for choice in PITCH_DESIGN_MODE_CHOICES}
    if mode not in valid_modes:
        mode = PITCH_DESIGN_MODE_AUTO

    template = _safe_str(manual_template, PITCH_MANUAL_TEMPLATE_CHOICES[0][0]).lower()
    valid_templates = {choice[0] for choice in PITCH_MANUAL_TEMPLATE_CHOICES}
    if template not in valid_templates:
        template = PITCH_MANUAL_TEMPLATE_CHOICES[0][0]
    return mode, template


def _hsv_color(hue_deg: float, saturation: float, value: float) -> colors.Color:
    h = (float(hue_deg) % 360.0) / 360.0
    s = max(0.0, min(1.0, float(saturation)))
    v = max(0.0, min(1.0, float(value)))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return colors.Color(r, g, b)


def _mix_colors(color_a: colors.Color, color_b: colors.Color, ratio: float) -> colors.Color:
    r = max(0.0, min(1.0, float(ratio)))
    return colors.Color(
        (color_a.red * (1 - r)) + (color_b.red * r),
        (color_a.green * (1 - r)) + (color_b.green * r),
        (color_a.blue * (1 - r)) + (color_b.blue * r),
    )


def _collect_pitch_text_blob(pitch_payload: dict) -> str:
    bits = [
        _safe_str(pitch_payload.get("title"), ""),
        _safe_str(pitch_payload.get("slogan"), ""),
        _safe_str(pitch_payload.get("elevator_pitch"), ""),
        _safe_str(pitch_payload.get("closing"), ""),
    ]
    for section in (pitch_payload.get("sections", []) or []):
        bits.append(_safe_str(section.get("title"), ""))
        bits.append(_safe_str(section.get("content"), ""))
    for deck in (pitch_payload.get("pitch_deck", []) or []):
        bits.append(_safe_str(deck.get("title"), ""))
        for bullet in (deck.get("bullets", []) or []):
            bits.append(_safe_str(bullet, ""))
    return " ".join(bit for bit in bits if bit).lower()


def _infer_pitch_context(pitch_payload: dict) -> str:
    blob = _collect_pitch_text_blob(pitch_payload)
    contexts = {
        "fintech": ["fintech", "finance", "pagamento", "credito", "banco", "wallet", "fatura"],
        "saude": ["saude", "health", "clinica", "hospital", "medico", "paciente", "telemedicina"],
        "educacao": ["educacao", "ensino", "aluno", "universidade", "escola", "edtech", "curso"],
        "energia": ["energia", "solar", "eletrica", "bateria", "sustentavel", "renovavel", "grid"],
        "logistica": ["logistica", "supply", "cadeia", "transporte", "entrega", "estoque", "warehouse"],
        "agro": ["agro", "fazenda", "agricola", "agritech", "campo", "safra", "produtor"],
        "retail": ["retail", "ecommerce", "loja", "consumidor", "varejo", "marketplace", "cliente final"],
    }
    scores = {}
    for context_name, words in contexts.items():
        score = 0
        for word in words:
            score += blob.count(word)
        scores[context_name] = score
    winner = max(scores, key=lambda k: scores[k]) if scores else "geral"
    return winner if scores.get(winner, 0) > 0 else "geral"


def _context_display_name(context_name: str) -> str:
    labels = {
        "fintech": "Fintech",
        "saude": "HealthTech",
        "educacao": "EdTech",
        "energia": "EnergyTech",
        "logistica": "LogTech",
        "agro": "AgriTech",
        "retail": "RetailTech",
        "geral": "BusinessTech",
    }
    return labels.get(context_name, "BusinessTech")


def _build_pitch_design_profile(
    pitch_payload: dict,
    *,
    design_mode: str = PITCH_DESIGN_MODE_AUTO,
    manual_template: str | None = None,
) -> dict:
    mode, normalized_template = normalize_pitch_design_options(design_mode, manual_template)
    context = _infer_pitch_context(pitch_payload)
    raw_signature = _safe_str(pitch_payload.get("narrative_uniqueness_key"), "")
    if not raw_signature:
        raw_signature = hashlib.sha256(
            json.dumps(pitch_payload or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:14]
    seed = int(hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:12], 16)

    base_hues = {
        "fintech": 214,
        "saude": 171,
        "educacao": 256,
        "energia": 49,
        "logistica": 206,
        "agro": 112,
        "retail": 323,
        "geral": 231,
    }
    template_by_context = {
        "fintech": ["grid", "orbit", "diagonal", "ribbon"],
        "saude": ["wave", "aurora", "orbit", "grid"],
        "educacao": ["diagonal", "grid", "wave", "ribbon"],
        "energia": ["wave", "diagonal", "aurora", "orbit"],
        "logistica": ["grid", "diagonal", "ribbon", "orbit"],
        "agro": ["wave", "grid", "aurora", "orbit"],
        "retail": ["orbit", "diagonal", "grid", "ribbon"],
        "geral": ["orbit", "grid", "wave", "diagonal", "aurora", "ribbon"],
    }
    layout_options = ["focus", "split", "timeline"]

    base_hue = float(base_hues.get(context, 231)) + float((seed % 19) - 9)
    accent_hue = (base_hue + 28 + (seed % 17)) % 360.0
    band_hue = (base_hue + 10 + (seed % 9)) % 360.0
    template_list = template_by_context.get(context, template_by_context["geral"])
    template_name = normalized_template if mode == PITCH_DESIGN_MODE_MANUAL else template_list[seed % len(template_list)]
    if mode == PITCH_DESIGN_MODE_MANUAL:
        context_label = f"{_context_display_name(context)} · Premium Manual"
    else:
        context_label = _context_display_name(context)

    return {
        "context": context,
        "context_label": context_label,
        "seed": seed,
        "base_hue": base_hue,
        "accent_hue": accent_hue,
        "band_hue": band_hue,
        "template_name": template_name,
        "layout_seed": seed % len(layout_options),
        "layout_options": layout_options,
        "design_mode": mode,
        "manual_template": normalized_template,
    }


def _palette_for_slide(index: int, design_profile: dict) -> dict:
    slide_offset = float(index * 4 + (design_profile.get("seed", 0) % 11))
    base_h = float(design_profile.get("base_hue", 231.0)) + (slide_offset * 0.35)
    band_h = float(design_profile.get("band_hue", 241.0)) + (slide_offset * 0.8)
    accent_h = float(design_profile.get("accent_hue", 271.0)) + (slide_offset * 1.1)
    bg = _hsv_color(base_h, 0.58, 0.12)
    card = _hsv_color(base_h + 6, 0.42, 0.20)
    band = _hsv_color(band_h, 0.72, 0.83)
    accent = _hsv_color(accent_h, 0.75, 0.96)
    shape1 = _hsv_color(base_h - 9, 0.62, 0.24)
    shape2 = _hsv_color(base_h + 13, 0.61, 0.30)
    muted = _mix_colors(band, colors.white, 0.72)
    return {
        "bg": bg,
        "band": band,
        "card": card,
        "text": colors.HexColor("#F8FAFC"),
        "muted": muted,
        "accent": accent,
        "shape1": shape1,
        "shape2": shape2,
    }


def _draw_background(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    palette: dict,
    template_name: str,
    design_seed: int,
):
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(palette["band"])
    pdf.rect(0, height - 42, width, 42, stroke=0, fill=1)

    template = (template_name or "orbit").strip().lower()
    seed_shift = (design_seed % 37) - 18
    if template == "grid":
        pdf.setStrokeColor(_mix_colors(palette["shape1"], palette["shape2"], 0.5))
        pdf.setLineWidth(0.6)
        step = 26 + (design_seed % 7)
        y = 0
        while y < height:
            pdf.line(0, y, width, y + (seed_shift * 0.25))
            y += step
        x = 0
        while x < width:
            pdf.line(x, 0, x + (seed_shift * 0.3), height)
            x += step
    elif template == "wave":
        pdf.setFillColor(palette["shape1"])
        for idx in range(5):
            radius = 230 + (idx * 66)
            cx = (width * 0.18) + (idx * 82) + (seed_shift * 0.8)
            cy = (-40) + (idx * 34)
            pdf.circle(cx, cy, radius, stroke=0, fill=1)
        pdf.setFillColor(palette["shape2"])
        for idx in range(4):
            radius = 210 + (idx * 72)
            cx = width - 80 - (idx * 72)
            cy = height - 40 + (idx * 20)
            pdf.circle(cx, cy, radius, stroke=0, fill=1)
    elif template == "diagonal":
        pdf.setFillColor(palette["shape1"])
        pdf.saveState()
        pdf.translate(-140 + seed_shift, -80)
        pdf.rotate(17 + (design_seed % 7))
        for idx in range(9):
            pdf.roundRect(0, idx * 66, width + 260, 42, 9, stroke=0, fill=1)
        pdf.restoreState()
        pdf.setFillColor(palette["shape2"])
        pdf.saveState()
        pdf.translate(width * 0.4, -120)
        pdf.rotate(17 + (design_seed % 7))
        for idx in range(7):
            pdf.roundRect(0, idx * 74, width + 120, 26, 7, stroke=0, fill=1)
        pdf.restoreState()
    elif template == "aurora":
        pdf.setFillColor(_mix_colors(palette["shape1"], colors.white, 0.08))
        for idx in range(6):
            radius = 300 - (idx * 28)
            cx = (width * 0.1) + idx * 90 + (seed_shift * 0.4)
            cy = height - 40 - (idx * 18)
            pdf.circle(cx, cy, radius, stroke=0, fill=1)
        pdf.setFillColor(_mix_colors(palette["shape2"], colors.white, 0.1))
        for idx in range(5):
            radius = 260 - (idx * 24)
            cx = width - 40 - idx * 84
            cy = 30 + idx * 22
            pdf.circle(cx, cy, radius, stroke=0, fill=1)
    elif template == "ribbon":
        pdf.setFillColor(palette["shape1"])
        for idx in range(10):
            y = 20 + (idx * 64)
            wobble = (seed_shift * 0.6) + (idx % 3) * 8
            pdf.roundRect(-40 + wobble, y, width + 80, 24, 10, stroke=0, fill=1)
        pdf.setFillColor(palette["shape2"])
        for idx in range(8):
            y = 46 + (idx * 72)
            wobble = (seed_shift * 0.5) - (idx % 4) * 9
            pdf.roundRect(-60 + wobble, y, width + 120, 16, 8, stroke=0, fill=1)
    else:
        pdf.setFillColor(palette["shape1"])
        pdf.circle(width * 0.92, height * 0.82, 90 + (design_seed % 22), stroke=0, fill=1)
        pdf.setFillColor(palette["shape2"])
        pdf.circle(width * 0.84, height * 0.68, 130 + (design_seed % 26), stroke=0, fill=1)


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
    context_label: str,
    template_name: str,
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
    pdf.drawString(72, 140, subtitle or "Deck estrategico para investidores")
    pdf.drawString(72, 122, f"Contexto visual: {context_label} | Template: {template_name}")
    pdf.drawString(72, 103, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

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
    layout_mode: str,
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

    mode = (layout_mode or "focus").strip().lower()
    if mode == "split":
        split_x = card_x + (card_w * 0.58)
        pdf.setStrokeColor(_mix_colors(palette["accent"], colors.white, 0.45))
        pdf.setLineWidth(1.1)
        pdf.line(split_x, card_y + 14, split_x, card_y + card_h - 44)

        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(card_x + 24, card_y + card_h - 54, "Teses principais")
        pdf.drawString(split_x + 18, card_y + card_h - 54, "Notas de execucao")

        half = max(1, (len(bullets) + 1) // 2)
        left_items = bullets[:half]
        right_items = bullets[half:]

        def _draw_bullet_column(items, start_x, start_y, max_chars):
            y_cursor = start_y
            pdf.setFont("Helvetica", 10.5)
            for raw in items[:5]:
                if y_cursor < card_y + 32:
                    break
                wrapped = _wrap_text_lines(_truncate_text(_safe_str(raw, "Sem informacao"), 160), max_chars=max_chars)[:3]
                pdf.setFillColor(palette["accent"])
                pdf.circle(start_x + 2, y_cursor + 4.5, 2.3, stroke=0, fill=1)
                pdf.setFillColor(palette["text"])
                for line in wrapped:
                    if y_cursor < card_y + 32:
                        break
                    pdf.drawString(start_x + 11, y_cursor, line)
                    y_cursor -= 13
                y_cursor -= 8

        _draw_bullet_column(left_items, card_x + 24, card_y + card_h - 80, 40)
        _draw_bullet_column(right_items, split_x + 18, card_y + card_h - 80, 31)
        _draw_visual_metrics(pdf, title, width, card_y, card_h, palette)
    elif mode == "timeline":
        line_x = card_x + 84
        top_y = card_y + card_h - 68
        bottom_y = card_y + 38
        pdf.setStrokeColor(_mix_colors(palette["accent"], colors.white, 0.3))
        pdf.setLineWidth(2.0)
        pdf.line(line_x, bottom_y, line_x, top_y)
        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(card_x + 24, card_y + card_h - 54, "Fluxo da narrativa")

        step_y = top_y - 18
        for idx, raw in enumerate(bullets[:6], start=1):
            if step_y < bottom_y + 6:
                break
            wrapped = _wrap_text_lines(_truncate_text(_safe_str(raw, "Sem informacao"), 180), max_chars=58)[:2]
            pdf.setFillColor(palette["accent"])
            pdf.circle(line_x, step_y + 4, 5, stroke=0, fill=1)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawCentredString(line_x, step_y + 1.5, str(idx))
            pdf.setFillColor(palette["text"])
            pdf.setFont("Helvetica", 10.5)
            for line in wrapped:
                pdf.drawString(line_x + 18, step_y, line)
                step_y -= 13
            step_y -= 11
    else:
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


def export_pitch_pdf(
    pitch_payload: dict,
    output_path: str,
    *,
    design_mode: str = PITCH_DESIGN_MODE_AUTO,
    manual_template: str | None = None,
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    slides = _build_pitch_slides(pitch_payload)
    page_size = landscape(A4)
    width, height = page_size

    pdf = canvas.Canvas(output_path, pagesize=page_size)
    engine_used = _safe_str(pitch_payload.get("engine_used"), "local")
    uniqueness_key = _safe_str(pitch_payload.get("narrative_uniqueness_key"), "")
    selected_design_mode, selected_manual_template = normalize_pitch_design_options(design_mode, manual_template)
    design_profile = _build_pitch_design_profile(
        pitch_payload,
        design_mode=selected_design_mode,
        manual_template=selected_manual_template,
    )
    total_pages = len(slides)

    for idx, slide in enumerate(slides, start=1):
        palette = _palette_for_slide(idx - 1, design_profile)
        _draw_background(
            pdf,
            width,
            height,
            palette,
            design_profile.get("template_name", "orbit"),
            int(design_profile.get("seed", 0)),
        )

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
                context_label=_safe_str(design_profile.get("context_label"), "BusinessTech"),
                template_name=_safe_str(design_profile.get("template_name"), "orbit").upper(),
            )
        else:
            layout_options = design_profile.get("layout_options") or ["focus"]
            layout_idx = (int(design_profile.get("layout_seed", 0)) + idx - 1) % len(layout_options)
            _draw_content_slide(
                pdf=pdf,
                width=width,
                height=height,
                title=_safe_str(slide.get("title"), "Slide"),
                subtitle=_safe_str(slide.get("subtitle"), ""),
                bullets=[str(b) for b in (slide.get("bullets") or [])],
                palette=palette,
                layout_mode=layout_options[layout_idx],
            )

        _draw_footer(pdf, width, idx, total_pages, engine_used, uniqueness_key, palette)
        pdf.showPage()

    pdf.save()
    return output_path
