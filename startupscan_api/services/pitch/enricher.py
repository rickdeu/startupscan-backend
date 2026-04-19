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
        base = f"{base} A leitura de mercado considera {market} e o plano de monetizacao combina {model}."
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

    enriched = []
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
        enriched.append({"title": title, "content": _safe_sentence(content)})
    payload["sections"] = enriched


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

        enriched_deck.append({"slide": item.get("slide", idx), "title": title, "bullets": expanded[:6]})
    payload["pitch_deck"] = enriched_deck


def enrich_pitch_payload(payload: dict) -> dict:
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
