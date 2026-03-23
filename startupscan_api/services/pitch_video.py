import io
import json
import os
import re
import hashlib
import textwrap
import asyncio
import time
import math
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import requests
from django.utils import timezone
from gtts import gTTS
from moviepy import AudioFileClip, ImageClip, VideoClip, VideoFileClip, afx, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

try:
    import edge_tts
except Exception:
    edge_tts = None


@dataclass
class VideoPlan:
    scenes: list
    narration: str
    character_name: str
    engine_used: str


MIN_VIDEO_SECONDS = 60
MAX_VIDEO_SECONDS = 180
TARGET_VIDEO_SECONDS = 130


class ExplainerVideoGenerationError(RuntimeError):
    """Erro estruturado para expor falhas de geração realista/local."""

    def __init__(
        self,
        message: str,
        *,
        did_status: str | None = None,
        did_error: str | None = None,
        local_error: str | None = None,
    ):
        super().__init__(message)
        self.did_status = did_status
        self.did_error = did_error
        self.local_error = local_error


def _build_video_uniqueness_key(payload: dict) -> str:
    raw = json.dumps(
        {
            "startup_name": payload.get("startup_name", ""),
            "score": payload.get("score", 0),
            "summary": payload.get("summary", ""),
            "growth_rate": payload.get("growth_rate", 0),
            "profit_margin": payload.get("profit_margin", 0),
            "revenue": payload.get("revenue", 0),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _narrative_tagline(startup_name: str, uniqueness_key: str) -> str:
    options = [
        f"{startup_name} avança com estratégia de escala responsável e impacto mensurável.",
        f"{startup_name} combina visão de mercado com execução disciplinada para captação.",
        f"{startup_name} apresenta crescimento com tese clara de valor para investidores.",
        f"{startup_name} demonstra diferencial competitivo com foco em tração sustentável.",
    ]
    return options[int(uniqueness_key, 16) % len(options)]


def _int_to_pt_word(value: int) -> str:
    table = {
        0: "zero",
        1: "um",
        2: "dois",
        3: "tres",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
        11: "onze",
        12: "doze",
        13: "treze",
        14: "catorze",
        15: "quinze",
        16: "dezasseis",
        17: "dezassete",
        18: "dezoito",
        19: "dezanove",
        20: "vinte",
    }
    return table.get(int(value), str(int(value)))


def _number_for_speech_pt(token: str) -> str:
    raw = str(token or "").strip()
    if not raw:
        return ""
    normalized = raw.replace(",", ".")
    if "." in normalized:
        left, right = normalized.split(".", 1)
        left = left.strip() or "0"
        right = re.sub(r"\D", "", right)
        if right:
            return f"{left} virgula {' '.join(right)}"
        return left
    if re.fullmatch(r"\d+", normalized):
        return _int_to_pt_word(int(normalized))
    return raw


def _normalize_numeric_ratio_for_tts(text: str) -> str:
    """
    Evita leitura de razão como data (ex.: 6.1/10 -> 6 virgula 1 por dez).
    """
    source = " ".join((text or "").split())
    if not source:
        return ""

    ratio_pattern = re.compile(
        r"(?<![\d/])(\d{1,3}(?:[.,]\d+)?)\s*/\s*(\d{1,3}(?:[.,]\d+)?)(?!\s*/)"
    )

    def _ratio_repl(match: re.Match) -> str:
        num_token = match.group(1)
        den_token = match.group(2)
        spoken_num = _number_for_speech_pt(num_token)
        spoken_den = _number_for_speech_pt(den_token)
        return f"{spoken_num} por {spoken_den}"

    return ratio_pattern.sub(_ratio_repl, source)


def _apply_tts_speech_fixes(plan: VideoPlan) -> VideoPlan:
    scenes = []
    for raw_scene in (plan.scenes or []):
        if not isinstance(raw_scene, dict):
            continue
        scene = dict(raw_scene)
        scene["text"] = _normalize_numeric_ratio_for_tts(str(scene.get("text", "") or ""))
        scenes.append(scene)

    narration = _normalize_numeric_ratio_for_tts(
        " ".join(str(s.get("text", "") or "") for s in scenes).strip() or plan.narration
    )
    return VideoPlan(
        scenes=scenes,
        narration=narration,
        character_name=plan.character_name,
        engine_used=plan.engine_used,
    )


def _load_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _analysis_payload(analysis):
    report = analysis.report or {}
    return {
        "startup_name": analysis.startup_name or f"Startup {analysis.id}",
        "score": float(analysis.success_score or 0),
        "summary": report.get("summary", ""),
        "strengths": report.get("strengths", [])[:3],
        "recommendations": report.get("recommendations", [])[:3],
        "investor_pitch": report.get("investor_pitch", {}),
        "category_scores": report.get("category_scores", {}),
        "revenue": float(analysis.revenue or 0),
        "growth_rate": float(analysis.growth_rate or 0),
        "profit_margin": float(analysis.profit_margin or 0),
    }


def _local_video_plan(payload: dict) -> VideoPlan:
    startup_name = payload["startup_name"]
    character_name = startup_name
    score = payload["score"]
    summary = payload.get("summary", "").strip()
    strengths = payload.get("strengths", [])
    recommendations = payload.get("recommendations", [])
    investor_pitch = payload.get("investor_pitch", {})
    category_scores = payload.get("category_scores", {})
    uniqueness_key = _build_video_uniqueness_key(payload)

    thesis = investor_pitch.get("investment_thesis", "Oportunidade com potencial relevante para investidores.")
    readiness = investor_pitch.get("funding_readiness", "Em evolução")
    suggested_ticket = investor_pitch.get("suggested_ticket", "Seed com acompanhamento estratégico")

    top_categories = []
    if isinstance(category_scores, dict):
        sorted_items = sorted(category_scores.items(), key=lambda kv: float(kv[1]), reverse=True)[:3]
        top_categories = [f"{k.replace('_', ' ').title()}: {v}/10" for k, v in sorted_items]

    stage_tones = [
        "com discurso orientado a investidores de crescimento",
        "com foco em execução e governança para escala",
        "com narrativa de mercado e diferenciação competitiva",
        "com mensagem de tração e previsibilidade de receita",
    ]
    tone = stage_tones[int(uniqueness_key, 16) % len(stage_tones)]
    narrative_tagline = _narrative_tagline(startup_name, uniqueness_key)

    recommendation_block = (
        " ".join(recommendations)
        if recommendations
        else "Acelerar produto, fortalecer vendas, aumentar retenção e preparar governança para investimento institucional."
    )
    strengths_block = (
        " ".join(strengths)
        if strengths
        else "Disciplina de execução, foco em cliente e capacidade de transformar visão em resultados."
    )
    category_block = " ; ".join(top_categories) if top_categories else "clareza estratégica, viabilidade, mercado e escala"

    scenes = [
        {
            "title": "Abertura Executiva",
            "text": (
                f"Senhoras e senhores, eu sou {character_name}. "
                f"Hoje apresento {startup_name} {tone}."
            ),
            "duration": 14,
        },
        {
            "title": "Problema e Oportunidade",
            "text": (
                summary
                or f"{startup_name} resolve um problema recorrente de mercado com potencial real de escala."
            ),
            "duration": 16,
        },
        {
            "title": "Solução e Diferenciação",
            "text": (
                f"A solução de {startup_name} combina execução prática com arquitetura escalável. "
                "Isto reduz fricção de adoção e melhora resultados para clientes."
            ),
            "duration": 16,
        },
        {
            "title": "Métricas-Chave",
            "text": (
                f"Receita atual: AOA {payload['revenue']:,.0f}. "
                f"Crescimento: {payload['growth_rate']:.1f}%. "
                f"Margem: {payload['profit_margin']:.1f}%. "
                f"Score preditivo: {score:.1f}/10."
            ),
            "duration": 15,
        },
        {
            "title": "Forças e Categorias",
            "text": (
                f"Pontos fortes: {strengths_block}. "
                f"Categorias de destaque: {category_block}."
            ),
            "duration": 15,
        },
        {
            "title": "Plano de Capital",
            "text": (
                f"{thesis} Prontidão atual: {readiness}. "
                f"Ticket sugerido: {suggested_ticket}."
            ),
            "duration": 15,
        },
        {
            "title": "Recomendações Estratégicas",
            "text": recommendation_block,
            "duration": 15,
        },
        {
            "title": "Encerramento Executivo",
            "text": (
                f"{startup_name} está posicionada para transformar execução em liderança de mercado. "
                f"{narrative_tagline}"
            ),
            "duration": 14,
        },
    ]

    narration = " ".join(scene["text"] for scene in scenes)
    return VideoPlan(scenes=scenes, narration=narration, character_name=character_name, engine_used="local")


def _gpt_video_plan(payload: dict) -> VideoPlan | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        uniqueness_key = _build_video_uniqueness_key(payload)
        prompt = {
            "task": (
                "Crie um roteiro executivo e cinematográfico em portugues para video explicativo de potencial de startup. "
                "Retorne JSON com: character_name, narration, scenes(list de objetos com title,text,duration). "
                "Duração total entre 1 e 3 minutos. "
                "Este roteiro deve ser único para esta startup e não pode reaproveitar estrutura textual genérica."
            ),
            "uniqueness_key": uniqueness_key,
            "analysis_payload": payload,
        }
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0.72,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é roteirista de vídeos de investimento para startups. "
                        "Cada roteiro precisa ser exclusivo para a startup, evitando repetição literal."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        scenes = data.get("scenes", []) if isinstance(data, dict) else []
        if not scenes:
            return None
        fixed_scenes = []
        for s in scenes:
            title = str(s.get("title", "Cena")).strip() or "Cena"
            text = str(s.get("text", "")).strip() or "Conteúdo em preparação."
            duration = int(float(s.get("duration", 15) or 15))
            duration = max(8, min(24, duration))
            fixed_scenes.append({"title": title, "text": text, "duration": duration})
        if fixed_scenes:
            fixed_scenes[-1]["text"] = (
                f"{fixed_scenes[-1]['text']} "
                f"{_narrative_tagline(payload['startup_name'], uniqueness_key)}"
            )
        narration = str(data.get("narration", "")).strip() or " ".join(scene["text"] for scene in fixed_scenes)
        character_name = str(data.get("character_name", payload["startup_name"])).strip() or payload["startup_name"]
        return VideoPlan(
            scenes=fixed_scenes[:8],
            narration=narration,
            character_name=character_name,
            engine_used="gpt",
        )
    except Exception:
        return None


def _plan_total_duration_seconds(plan: VideoPlan) -> int:
    try:
        return int(sum(float(scene.get("duration", 0) or 0) for scene in plan.scenes))
    except Exception:
        return 0


def _enforce_video_duration(plan: VideoPlan, payload: dict) -> VideoPlan:
    """
    Garante vídeo entre 1 e 3 minutos com ritmo natural.
    Se GPT vier fora da janela, usa fallback local.
    """
    total = _plan_total_duration_seconds(plan)
    word_count = len((plan.narration or "").split())
    if total < MIN_VIDEO_SECONDS or word_count < 100 or word_count > 420:
        return _local_video_plan(payload)

    scenes = [dict(s) for s in (plan.scenes or []) if isinstance(s, dict)]
    if not scenes:
        return _local_video_plan(payload)

    for scene in scenes:
        dur = int(float(scene.get("duration", 14) or 14))
        scene["duration"] = max(8, min(24, dur))

    total = sum(int(s.get("duration", 0) or 0) for s in scenes)
    if total > MAX_VIDEO_SECONDS:
        scale = MAX_VIDEO_SECONDS / max(1, total)
        for scene in scenes:
            scene["duration"] = max(8, int(round(scene["duration"] * scale)))
        total = sum(int(s.get("duration", 0) or 0) for s in scenes)
        while total > MAX_VIDEO_SECONDS:
            idx = max(range(len(scenes)), key=lambda i: int(scenes[i]["duration"]))
            if int(scenes[idx]["duration"]) <= 8:
                break
            scenes[idx]["duration"] = int(scenes[idx]["duration"]) - 1
            total -= 1

    if total < MIN_VIDEO_SECONDS:
        while total < MIN_VIDEO_SECONDS:
            for scene in scenes:
                if total >= MIN_VIDEO_SECONDS:
                    break
                scene["duration"] = int(scene["duration"]) + 1
                total += 1

    narration = " ".join(str(s.get("text", "") or "") for s in scenes).strip()
    return VideoPlan(
        scenes=scenes,
        narration=narration or plan.narration,
        character_name=plan.character_name,
        engine_used=plan.engine_used,
    )


def _build_conclusion_scene(payload: dict) -> dict:
    startup_name = payload.get("startup_name", "Startup")
    score = float(payload.get("score", 0) or 0)
    return {
        "title": "Conclusão da Apresentação",
        "text": (
            f"Em conclusão, {startup_name} demonstra uma oportunidade real de investimento com score {score:.1f}/10, "
            "fundamentos estratégicos e potencial de escala sustentável. "
            "Obrigado pela atenção. Estamos prontos para avançar com os próximos passos da captação."
        ),
        "duration": 18,
    }


def _scene_looks_like_conclusion(scene: dict) -> bool:
    title = str(scene.get("title", "") or "").lower()
    text = str(scene.get("text", "") or "").lower()
    blob = f"{title} {text}"
    keywords = [
        "conclus",
        "mensagem final",
        "final da apresenta",
        "obrigado",
        "próximos passos da captação",
    ]
    return any(k in blob for k in keywords)


def _ensure_plan_has_conclusion(plan: VideoPlan, payload: dict) -> VideoPlan:
    if not plan.scenes:
        scene = _build_conclusion_scene(payload)
        return VideoPlan(
            scenes=[scene],
            narration=scene["text"],
            character_name=plan.character_name or payload.get("startup_name", "Startup"),
            engine_used=plan.engine_used or "local",
        )

    if _scene_looks_like_conclusion(plan.scenes[-1]):
        return plan

    conclusion = _build_conclusion_scene(payload)
    total = _plan_total_duration_seconds(plan)
    scenes = [dict(s) for s in plan.scenes]

    if total <= (MAX_VIDEO_SECONDS - 14):
        scenes.append(conclusion)
    else:
        # Se já está no limite, substitui a última cena mantendo duração adequada.
        replacement = dict(conclusion)
        last_duration = int(float(scenes[-1].get("duration", 18) or 18))
        replacement["duration"] = max(12, min(20, last_duration))
        scenes[-1] = replacement

    narration = " ".join(str(s.get("text", "") or "") for s in scenes).strip()
    return VideoPlan(
        scenes=scenes,
        narration=narration or plan.narration,
        character_name=plan.character_name,
        engine_used=plan.engine_used,
    )


def build_video_plan_from_analysis(analysis) -> VideoPlan:
    payload = _analysis_payload(analysis)
    plan = _gpt_video_plan(payload)
    if plan is None:
        plan = _local_video_plan(payload)
    plan = _enforce_video_duration(plan, payload)
    plan = _ensure_plan_has_conclusion(plan, payload)
    plan = _apply_tts_speech_fixes(plan)
    return plan


def _download_binary_file(url: str, output_path: str) -> bool:
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            if resp.status_code >= 400:
                return False
            with open(output_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        fh.write(chunk)
        return True
    except Exception:
        return False


def _split_script_for_did(
    script_text: str,
    *,
    target_min_segments: int = 4,
    max_segments: int = 10,
    max_chars_per_segment: int = 360,
) -> list[str]:
    clean = " ".join((script_text or "").strip().split())
    if not clean:
        return []

    sentence_chunks = [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", clean) if s.strip()]
    if not sentence_chunks:
        sentence_chunks = [clean]

    segments = []
    current = ""
    for sentence in sentence_chunks:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars_per_segment:
            current = candidate
            continue
        if current:
            segments.append(current)
            current = sentence
        else:
            # sentença longa: quebra por palavras
            words = sentence.split()
            buf = []
            for w in words:
                cand = (" ".join(buf + [w])).strip()
                if len(cand) > max_chars_per_segment and buf:
                    segments.append(" ".join(buf).strip())
                    buf = [w]
                else:
                    buf.append(w)
            if buf:
                current = " ".join(buf).strip()
    if current:
        segments.append(current)

    # Refina segmentos grandes em blocos menores para manter ritmo natural.
    target = max(1, min(max_segments, target_min_segments))
    while len(segments) < target:
        idx_long = None
        max_len = 0
        for i, seg in enumerate(segments):
            if len(seg) > max_len:
                max_len = len(seg)
                idx_long = i
        if idx_long is None or max_len < 180:
            break
        words = segments[idx_long].split()
        mid = max(1, len(words) // 2)
        left = " ".join(words[:mid]).strip()
        right = " ".join(words[mid:]).strip()
        new_parts = [p for p in (left, right) if p]
        segments = segments[:idx_long] + new_parts + segments[idx_long + 1 :]
        if len(segments) >= max_segments:
            break

    cleaned = []
    for seg in segments[:max_segments]:
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) > max_chars_per_segment:
            seg = seg[:max_chars_per_segment].rsplit(" ", 1)[0].strip()
        if seg and seg[-1] not in ".!?":
            seg += "."
        cleaned.append(seg)
    return cleaned


def _stylize_stage_cinematic_text(script_text: str) -> str:
    """
    Ajusta ritmo da locução para apresentação curta: frases curtas e pausas naturais.
    Não altera semântica principal, apenas a musicalidade.
    """
    text = _normalize_numeric_ratio_for_tts(script_text or "")
    if not text:
        return ""
    sentence_chunks = [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", text) if s.strip()]
    stylized = []
    for idx, sentence in enumerate(sentence_chunks):
        sentence = sentence.rstrip(" .")
        if not sentence:
            continue
        # Introduz pausas pontuais de oratória sem exagerar.
        if idx % 3 == 0:
            stylized.append(f"{sentence}.")
        elif idx % 3 == 1:
            stylized.append(f"{sentence}... ")
        else:
            stylized.append(f"{sentence}. ")
    merged = " ".join(stylized).strip()
    return merged


def _normalize_gender_label(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"male", "man", "masculino", "homem"}:
        return "male"
    if normalized in {"female", "woman", "feminino", "mulher"}:
        return "female"
    return "unknown"


def _extract_gender_from_deepface_result(result) -> str:
    if isinstance(result, list) and result:
        return _extract_gender_from_deepface_result(result[0])
    if not isinstance(result, dict):
        return "unknown"

    direct = _normalize_gender_label(result.get("dominant_gender"))
    if direct != "unknown":
        return direct

    gender_block = result.get("gender")
    if isinstance(gender_block, dict):
        man_score = float(gender_block.get("Man", 0.0) or 0.0)
        woman_score = float(gender_block.get("Woman", 0.0) or 0.0)
        if man_score > woman_score:
            return "male"
        if woman_score > man_score:
            return "female"
    return "unknown"


def _infer_presenter_gender_from_image(image_path: str | None) -> str:
    if not image_path or not os.path.exists(image_path):
        return "unknown"

    try:
        from deepface import DeepFace

        analysis = DeepFace.analyze(
            img_path=image_path,
            actions=["gender"],
            enforce_detection=False,
            detector_backend="opencv",
            silent=True,
        )
        inferred = _extract_gender_from_deepface_result(analysis)
        if inferred != "unknown":
            return inferred
    except Exception:
        pass

    # Fallback leve por nome de arquivo quando não for possível inferir via modelo.
    name_hint = Path(image_path).name.lower()
    if any(token in name_hint for token in ["woman", "female", "mulher", "femin"]):
        return "female"
    if any(token in name_hint for token in ["man", "male", "homem", "masc"]):
        return "male"
    return "unknown"


def _resolve_voice_profile(presenter_gender: str | None) -> dict:
    gender = _normalize_gender_label(presenter_gender)
    did_generic = os.getenv("DID_VOICE_ID", "").strip()
    edge_ao_generic = os.getenv("EDGE_TTS_VOICE_PT_AO", "").strip()

    if gender == "female":
        did_candidates = [
            os.getenv("DID_VOICE_ID_FEMALE", "").strip(),
            "pt-PT-RaquelNeural",
            "pt-BR-FranciscaNeural",
            did_generic,
            "pt-PT-DuarteNeural",
        ]
        edge_candidates = [
            os.getenv("EDGE_TTS_VOICE_PT_AO_FEMALE", "").strip(),
            os.getenv("EDGE_TTS_VOICE_FEMALE", "").strip(),
            "pt-PT-RaquelNeural",
            "pt-BR-FranciscaNeural",
            edge_ao_generic,
            "pt-PT-DuarteNeural",
            "pt-BR-AntonioNeural",
        ]
    elif gender == "male":
        did_candidates = [
            os.getenv("DID_VOICE_ID_MALE", "").strip(),
            "pt-PT-DuarteNeural",
            "pt-BR-AntonioNeural",
            did_generic,
            "pt-PT-RaquelNeural",
        ]
        edge_candidates = [
            os.getenv("EDGE_TTS_VOICE_PT_AO_MALE", "").strip(),
            os.getenv("EDGE_TTS_VOICE_MALE", "").strip(),
            edge_ao_generic,
            "pt-PT-DuarteNeural",
            "pt-BR-AntonioNeural",
            "pt-PT-RaquelNeural",
            "pt-BR-FranciscaNeural",
        ]
    else:
        did_candidates = [did_generic, "pt-PT-DuarteNeural", "pt-PT-RaquelNeural", "pt-BR-AntonioNeural"]
        edge_candidates = [edge_ao_generic, "pt-PT-DuarteNeural", "pt-PT-RaquelNeural", "pt-BR-AntonioNeural"]

    did_candidates = [voice for voice in did_candidates if voice]
    edge_candidates = [voice for voice in edge_candidates if voice]
    did_voice_id = did_candidates[0] if did_candidates else "pt-PT-DuarteNeural"
    return {
        "gender": gender,
        "did_voice_id": did_voice_id,
        "edge_voices": edge_candidates,
    }


def _did_create_and_download_talk(
    *,
    create_url: str,
    headers: dict,
    source_image_url: str,
    script_text: str,
    voice_id: str,
    output_path: str,
) -> dict:
    payload = {
        "source_url": source_image_url,
        "script": {
            "type": "text",
            "input": script_text,
            "provider": {
                "type": "microsoft",
                "voice_id": voice_id,
            },
        },
        "config": {
            "fluent": True,
            "pad_audio": 0.0,
        },
    }
    create_resp = None
    for attempt in range(3):
        try:
            create_resp = requests.post(create_url, headers=headers, data=json.dumps(payload), timeout=120)
        except Exception as exc:
            if attempt < 2:
                time.sleep(1.8 * (attempt + 1))
                continue
            return {"status": "failed", "error": f"create_exception:{exc}"}
        if create_resp.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            time.sleep(1.8 * (attempt + 1))
            continue
        break

    if create_resp is None:
        return {"status": "failed", "error": "create_no_response"}

    if create_resp.status_code >= 400:
        return {
            "status": "failed",
            "error": f"create_failed:{create_resp.status_code}:{(create_resp.text or '')[:350]}",
        }

    create_data = create_resp.json() if create_resp.content else {}
    talk_id = create_data.get("id")
    if not talk_id:
        return {"status": "failed", "error": "missing_talk_id"}

    status_url = f"{create_url}/{talk_id}"
    result_url = None
    status_value = "created"
    error_message = ""
    for _ in range(95):
        poll_resp = requests.get(status_url, headers=headers, timeout=60)
        if poll_resp.status_code >= 400:
            error_message = f"poll_failed:{poll_resp.status_code}:{(poll_resp.text or '')[:250]}"
            break
        poll_data = poll_resp.json() if poll_resp.content else {}
        status_value = str(poll_data.get("status", "")).lower()
        if status_value == "done":
            result_url = poll_data.get("result_url")
            break
        if status_value in {"error", "failed", "rejected"}:
            error_message = str(poll_data.get("error", "failed"))
            break
        time.sleep(2.1)

    if not result_url:
        return {
            "status": status_value or "failed",
            "talk_id": talk_id,
            "error": error_message or "no_result_url",
        }

    ok = _download_binary_file(result_url, output_path)
    if not ok:
        return {
            "status": "failed",
            "talk_id": talk_id,
            "error": "result_download_failed",
        }
    return {
        "status": "done",
        "talk_id": talk_id,
        "result_url": result_url,
    }


def _try_generate_realistic_video_did(
    plan: VideoPlan,
    source_image_url: str,
    output_path: str,
    source_image_urls: list[str] | None = None,
    presenter_gender: str | None = None,
    real_image_only: bool = False,
    progress_callback=None,
):
    """
    Usa D-ID para gerar vídeo de avatar realista com gestos/lip-sync.
    Retorna metadados ou None em caso de falha/sem configuração.
    """
    api_key = os.getenv("DID_API_KEY", "").strip()
    original_source = (source_image_url or "").strip()
    did_sources = [u.strip() for u in (source_image_urls or []) if isinstance(u, str) and u.strip()]
    if real_image_only:
        # Modo estrito: usa apenas fontes reais sem composição de cenário.
        real_only_sources = [u for u in did_sources if u]
        if original_source:
            real_only_sources = [original_source] + [u for u in real_only_sources if u != original_source]
        did_sources = list(dict.fromkeys(real_only_sources))
    else:
        # Mantém fallback do source original ativo por padrão para reduzir falhas em poses dinâmicas.
        allow_original_fallback = os.getenv("DID_ALLOW_ORIGINAL_SOURCE_FALLBACK", "1").strip().lower() in {"1", "true", "yes"}
        if original_source and original_source not in did_sources:
            if not did_sources or allow_original_fallback:
                did_sources.append(original_source)
    # Dedup mantendo ordem.
    did_sources = list(dict.fromkeys(did_sources))

    if not api_key or not did_sources:
        return None

    auth_value = api_key if api_key.lower().startswith("basic ") else f"Basic {api_key}"
    base_url = os.getenv("DID_API_BASE_URL", "https://api.d-id.com").rstrip("/")
    create_url = f"{base_url}/talks"
    voice_profile = _resolve_voice_profile(presenter_gender)
    voice_id = voice_profile.get("did_voice_id") or "pt-PT-DuarteNeural"

    headers = {
        "Authorization": auth_value,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        stage_script = _stylize_stage_cinematic_text(plan.narration)
        words = len(stage_script.split())
        target_segments = 4 if words < 220 else 6
        max_segments = 8 if words < 320 else 10
        segments = _split_script_for_did(
            stage_script,
            target_min_segments=target_segments,
            max_segments=max_segments,
            max_chars_per_segment=360,
        )
        if not segments:
            return {
                "provider": "did",
                "status": "failed",
                "voice_id": voice_id,
                "voice_gender_target": voice_profile.get("gender", "unknown"),
                "error": "empty_script",
            }

        while len(did_sources) < len(segments):
            did_sources.append(did_sources[-1])

        segment_outputs = []
        segment_talk_ids = []
        segment_result_urls = []
        for idx, segment_text in enumerate(segments):
            if callable(progress_callback):
                try:
                    pct = 36 + int(((idx + 1) / max(1, len(segments))) * 46)
                    progress_callback(
                        pct,
                        "renderizacao",
                        f"Gerando segmento {idx + 1}/{len(segments)} no modo cinematográfico",
                    )
                except Exception:
                    pass
            segment_path = output_path if len(segments) == 1 else output_path.replace(".mp4", f"_did_seg_{idx + 1}.mp4")
            segment_outputs.append(segment_path)
            preferred_source = did_sources[idx % len(did_sources)]
            candidate_sources = [preferred_source] + [u for u in did_sources if u != preferred_source]
            talk_meta = None
            candidate_errors = []
            for source_candidate in candidate_sources:
                attempt_meta = _did_create_and_download_talk(
                    create_url=create_url,
                    headers=headers,
                    source_image_url=source_candidate,
                    script_text=segment_text,
                    voice_id=voice_id,
                    output_path=segment_path,
                )
                if attempt_meta.get("status") == "done":
                    talk_meta = attempt_meta
                    talk_meta["source_url_used"] = source_candidate
                    break
                candidate_errors.append(f"{source_candidate} => {attempt_meta.get('error', 'unknown_error')}")

            if not talk_meta or talk_meta.get("status") != "done":
                # Fallback de resgate: tenta uma versão condensada no source original.
                rescue_error = ""
                if original_source:
                    rescue_script = " ".join(segments[: min(3, len(segments))]).strip()
                    if len(rescue_script) > 900:
                        rescue_script = rescue_script[:900].rsplit(" ", 1)[0].strip() + "."
                    if rescue_script:
                        rescue_meta = _did_create_and_download_talk(
                            create_url=create_url,
                            headers=headers,
                            source_image_url=original_source,
                            script_text=rescue_script,
                            voice_id=voice_id,
                            output_path=output_path,
                        )
                        if rescue_meta.get("status") == "done":
                            return {
                                "provider": "did",
                                "talk_id": rescue_meta.get("talk_id"),
                                "talk_ids": [rescue_meta.get("talk_id")] if rescue_meta.get("talk_id") else [],
                                "result_url": rescue_meta.get("result_url"),
                                "result_urls": [rescue_meta.get("result_url")] if rescue_meta.get("result_url") else [],
                                "status": "done",
                                "voice_id": voice_id,
                                "voice_gender_target": voice_profile.get("gender", "unknown"),
                                "segment_count": 1,
                                "source_count": len(did_sources),
                                "style_mode": "did_real_image_only" if real_image_only else "cinematic_stage_presenter_rescue",
                                "real_image_only": bool(real_image_only),
                                "error": "",
                            }
                        rescue_error = rescue_meta.get("error", "rescue_unknown_error")
                return {
                    "provider": "did",
                    "status": "failed",
                    "voice_id": voice_id,
                    "voice_gender_target": voice_profile.get("gender", "unknown"),
                    "segment_index": idx + 1,
                    "segment_count": len(segments),
                    "error": "segment_failed_all_sources",
                    "segment_errors": candidate_errors,
                    "rescue_error": rescue_error,
                    "talk_id": (talk_meta or {}).get("talk_id"),
                }
            if talk_meta.get("talk_id"):
                segment_talk_ids.append(talk_meta["talk_id"])
            if talk_meta.get("result_url"):
                segment_result_urls.append(talk_meta["result_url"])

        if len(segment_outputs) > 1:
            final_clip = None
            clips = []
            try:
                for segment_path in segment_outputs:
                    clips.append(VideoFileClip(segment_path))
                final_clip = concatenate_videoclips(clips, method="compose")
                final_clip.write_videofile(
                    output_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="medium",
                    threads=2,
                    logger=None,
                )
            except Exception as exc:
                return {
                    "provider": "did",
                    "status": "failed",
                    "voice_id": voice_id,
                    "voice_gender_target": voice_profile.get("gender", "unknown"),
                    "error": f"stitch_failed:{exc}",
                }
            finally:
                for c in clips:
                    try:
                        c.close()
                    except Exception:
                        pass
                if final_clip is not None:
                    try:
                        final_clip.close()
                    except Exception:
                        pass
                for segment_path in segment_outputs:
                    try:
                        if segment_path != output_path and os.path.exists(segment_path):
                            os.remove(segment_path)
                    except Exception:
                        pass

        return {
            "provider": "did",
            "talk_id": segment_talk_ids[-1] if segment_talk_ids else None,
            "talk_ids": segment_talk_ids,
            "result_url": segment_result_urls[-1] if segment_result_urls else None,
            "result_urls": segment_result_urls,
            "status": "done",
            "voice_id": voice_id,
            "voice_gender_target": voice_profile.get("gender", "unknown"),
            "segment_count": len(segments),
            "source_count": len(did_sources),
            "style_mode": "did_real_image_only" if real_image_only else "cinematic_stage_presenter",
            "real_image_only": bool(real_image_only),
            "error": "",
        }
    except Exception as exc:
        return {
            "provider": "did",
            "status": "failed",
            "voice_id": voice_id,
            "voice_gender_target": voice_profile.get("gender", "unknown"),
            "error": f"exception:{exc}",
        }


def _prepare_presenter_image(image_path: str | None):
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGB")
        return img
    except Exception:
        return None


def _extract_face_patch(presenter_image: Image.Image | None):
    """Extrai um recorte aproximado do rosto (funciona mesmo sem detector facial)."""
    if presenter_image is None:
        return None
    w, h = presenter_image.size
    if w < 40 or h < 40:
        return None

    # Heurística: rosto costuma estar no terço superior e mais próximo do centro.
    crop_size = int(min(w, h) * 0.42)
    crop_size = max(80, min(crop_size, min(w, h)))
    center_x = w // 2
    center_y = int(h * 0.26)
    left = max(0, min(w - crop_size, center_x - crop_size // 2))
    top = max(0, min(h - crop_size, center_y - crop_size // 2))
    patch = presenter_image.crop((left, top, left + crop_size, top + crop_size))
    patch = ImageOps.fit(patch, (220, 220), method=Image.Resampling.LANCZOS)
    return patch.filter(ImageFilter.SMOOTH_MORE)


def _render_did_fullbody_source_image(
    *,
    face_patch: Image.Image | None,
    startup_name: str,
    output_path: str,
    pose_index: int = 0,
):
    """
    Gera uma imagem vertical de corpo inteiro para D-ID (palco + plateia + gestos).
    Serve para transformar foto meio-corpo em um visual de apresentador completo.
    """
    width, height = 1024, 1536
    shot_profiles = ["wide", "left", "right", "close", "hero"]
    profile = shot_profiles[pose_index % len(shot_profiles)]
    img = Image.new("RGB", (width, height), (10, 17, 31))
    draw = ImageDraw.Draw(img)

    # Fundo com gradiente simples de palco
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(8 + 20 * (1 - t))
        g = int(15 + 36 * (1 - t))
        b = int(26 + 62 * (1 - t))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Luzes e tela institucional
    beam_shift = {"wide": 0, "left": -36, "right": 36, "close": 0, "hero": 20}.get(profile, 0)
    draw.polygon([(0 + beam_shift, 0), (220 + beam_shift, 0), (80 + beam_shift, 420)], outline=(68, 124, 196))
    draw.polygon([(width - beam_shift, 0), (width - 220 - beam_shift, 0), (width - 80 - beam_shift, 420)], outline=(68, 124, 196))
    draw.rounded_rectangle((250, 115, width - 70, 285), radius=20, fill=(20, 38, 68), outline=(92, 156, 230), width=3)
    draw.text((280, 160), "Global Startup Summit", fill=(224, 236, 255), font=_load_font(34))
    draw.text((280, 208), "Palestra para grande audiência", fill=(178, 201, 232), font=_load_font(24))

    # Plateia gigante
    base_y = height - 45
    for row in range(10):
        y = base_y - row * 46
        crowd_count = 22 + row * 8
        head_r = max(4, 12 - row)
        shade = int(24 + row * 8)
        for i in range(crowd_count):
            x = int((i + 0.5) * width / crowd_count)
            draw.ellipse((x - head_r, y - head_r, x + head_r, y + head_r), fill=(shade, shade, shade + 6))
            if row >= 2:
                draw.rectangle((x - max(2, head_r // 2), y + head_r - 1, x + max(2, head_r // 2), y + head_r + 9), fill=(shade - 2, shade - 2, shade + 4))

    # Personagem corpo inteiro
    cx = width // 2
    top = 340
    if profile == "left":
        cx -= 74
        top = 332
    elif profile == "right":
        cx += 74
        top = 332
    elif profile == "close":
        top = 298
    elif profile == "hero":
        cx += 28
        top = 314
    skin = (212, 164, 136)
    suit_dark = (18, 30, 56)
    suit_mid = (28, 47, 84)
    shirt = (229, 234, 242)
    tie = (164, 34, 58)

    # Pernas
    draw.rounded_rectangle((cx - 66, top + 520, cx - 12, top + 815), radius=18, fill=(14, 26, 49))
    draw.rounded_rectangle((cx + 12, top + 520, cx + 66, top + 815), radius=18, fill=(14, 26, 49))
    draw.rounded_rectangle((cx - 86, top + 805, cx - 4, top + 842), radius=10, fill=(8, 12, 22))
    draw.rounded_rectangle((cx + 4, top + 805, cx + 86, top + 842), radius=10, fill=(8, 12, 22))

    # Tronco
    draw.rounded_rectangle((cx - 130, top + 188, cx + 130, top + 564), radius=44, fill=suit_dark, outline=(102, 178, 250), width=4)
    draw.polygon([(cx - 44, top + 212), (cx - 9, top + 360), (cx - 78, top + 360)], fill=suit_mid)
    draw.polygon([(cx + 44, top + 212), (cx + 9, top + 360), (cx + 78, top + 360)], fill=suit_mid)
    draw.polygon([(cx - 12, top + 212), (cx + 12, top + 212), (cx + 23, top + 338), (cx - 23, top + 338)], fill=shirt)
    draw.rectangle((cx - 7, top + 236, cx + 7, top + 430), fill=tie)
    draw.polygon([(cx - 7, top + 430), (cx + 7, top + 430), (cx, top + 486)], fill=tie)
    draw.polygon([(cx + 48, top + 290), (cx + 76, top + 290), (cx + 66, top + 312)], fill=(242, 242, 242))

    # Braços em 3 poses para dar sensação de gestos entre segmentos D-ID
    left_shoulder = (cx - 90, top + 266)
    right_shoulder = (cx + 90, top + 266)
    if pose_index % 5 == 0:
        left_elbow = (cx - 208, top + 326)
        left_hand = (cx - 256, top + 280)
        right_elbow = (cx + 188, top + 236)
        right_hand = (cx + 256, top + 200)
    elif pose_index % 5 == 1:
        left_elbow = (cx - 182, top + 266)
        left_hand = (cx - 246, top + 242)
        right_elbow = (cx + 176, top + 296)
        right_hand = (cx + 238, top + 334)
    elif pose_index % 5 == 2:
        left_elbow = (cx - 158, top + 350)
        left_hand = (cx - 204, top + 420)
        right_elbow = (cx + 172, top + 256)
        right_hand = (cx + 236, top + 228)
    elif pose_index % 5 == 3:
        left_elbow = (cx - 195, top + 292)
        left_hand = (cx - 254, top + 258)
        right_elbow = (cx + 194, top + 334)
        right_hand = (cx + 256, top + 372)
    else:
        left_elbow = (cx - 170, top + 308)
        left_hand = (cx - 212, top + 344)
        right_elbow = (cx + 206, top + 272)
        right_hand = (cx + 278, top + 248)

    draw.line([left_shoulder, left_elbow], fill=suit_mid, width=34, joint="curve")
    draw.line([left_elbow, left_hand], fill=suit_mid, width=26, joint="curve")
    draw.ellipse((left_hand[0] - 17, left_hand[1] - 17, left_hand[0] + 17, left_hand[1] + 17), fill=skin)
    draw.line([right_shoulder, right_elbow], fill=suit_mid, width=34, joint="curve")
    draw.line([right_elbow, right_hand], fill=suit_mid, width=26, joint="curve")
    draw.ellipse((right_hand[0] - 17, right_hand[1] - 17, right_hand[0] + 17, right_hand[1] + 17), fill=skin)

    # Cabeça + face enviada
    head_size = 186
    head_left = cx - head_size // 2
    head_top = top + 28
    draw.ellipse((head_left - 3, head_top - 3, head_left + head_size + 3, head_top + head_size + 3), fill=(225, 204, 182))
    if face_patch is not None:
        face = ImageOps.fit(face_patch, (head_size, head_size), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (head_size, head_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, head_size, head_size), fill=255)
        img.paste(face, (head_left, head_top), mask)
    else:
        draw.ellipse((head_left, head_top, head_left + head_size, head_top + head_size), fill=skin)
        initials = (startup_name[:2] or "AI").upper()
        draw.text((head_left + 56, head_top + 64), initials, fill=(255, 255, 255), font=_load_font(58))
    draw.ellipse((head_left, head_top, head_left + head_size, head_top + head_size), outline=(122, 206, 252), width=4)

    # Púlpito frontal para reforçar ambiente de palestra
    podium_top = top + 452
    draw.rounded_rectangle((cx - 170, podium_top, cx + 170, podium_top + 352), radius=24, fill=(20, 31, 55), outline=(86, 146, 220), width=4)
    draw.rounded_rectangle((cx - 112, podium_top + 82, cx + 112, podium_top + 152), radius=12, fill=(32, 64, 112))
    draw.text((cx - 88, podium_top + 106), (startup_name or "Startup")[:16], fill=(231, 240, 255), font=_load_font(22))
    draw.line([(cx - 25, podium_top + 8), (cx - 42, podium_top - 65)], fill=(126, 146, 176), width=5)
    draw.line([(cx + 25, podium_top + 8), (cx + 42, podium_top - 65)], fill=(126, 146, 176), width=5)
    draw.ellipse((cx - 49, podium_top - 77, cx - 35, podium_top - 63), fill=(156, 170, 190))
    draw.ellipse((cx + 35, podium_top - 77, cx + 49, podium_top - 63), fill=(156, 170, 190))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)


def build_did_presenter_source_urls(
    presenter_image_path: str | None,
    presenter_image_url: str | None,
    startup_name: str,
) -> list[str]:
    """
    Cria imagens de corpo inteiro (poses diferentes) e devolve URLs públicas.
    Útil quando a foto enviada é meio corpo e queremos palco dinâmico no D-ID.
    """
    if not presenter_image_path or not presenter_image_url:
        return []
    if not os.path.exists(presenter_image_path):
        return []

    try:
        presenter_image = _prepare_presenter_image(presenter_image_path)
        face_patch = _extract_face_patch(presenter_image)
        source_dir = os.path.dirname(presenter_image_path)
        base_name = Path(presenter_image_path).stem
        url_base = presenter_image_url.rsplit("/", 1)[0]
        urls = []

        for pose_index in range(5):
            file_name = f"{base_name}_did_fullbody_pose_{pose_index + 1}.png"
            file_path = os.path.join(source_dir, file_name)
            _render_did_fullbody_source_image(
                face_patch=face_patch,
                startup_name=startup_name,
                output_path=file_path,
                pose_index=pose_index,
            )
            urls.append(f"{url_base}/{file_name}")
        return urls
    except Exception:
        return []


def build_did_real_image_only_source_url(
    presenter_image_path: str | None,
    presenter_image_url: str | None,
) -> str | None:
    """
    Gera uma fonte visual "real-only" para o D-ID:
    - sem cenário artificial;
    - sem palco ou composição extra;
    - close-up da pessoa para minimizar qualquer fundo visível.
    """
    if not presenter_image_path or not presenter_image_url:
        return None
    if not os.path.exists(presenter_image_path):
        return None

    try:
        raw_image = Image.open(presenter_image_path)
        source_dir = os.path.dirname(presenter_image_path)
        base_name = Path(presenter_image_path).stem
        file_name = f"{base_name}_did_real_only.png"
        file_path = os.path.join(source_dir, file_name)
        url_base = presenter_image_url.rsplit("/", 1)[0]

        # No modo did_only, o foco é close-up real sem cenário.
        # Evita transparência para não cair em preenchimentos automáticos do provedor.
        presenter_image = raw_image.convert("RGB")
        face_patch = _extract_face_patch(presenter_image)
        if face_patch is not None:
            # Zoom adicional para reduzir ainda mais fundo periférico.
            zoomed = ImageOps.fit(face_patch, (1400, 1400), method=Image.Resampling.LANCZOS)
            source_img = ImageOps.fit(zoomed, (1024, 1024), method=Image.Resampling.LANCZOS)
        else:
            source_img = ImageOps.fit(presenter_image, (1024, 1024), method=Image.Resampling.LANCZOS)
        source_img = source_img.filter(ImageFilter.SMOOTH_MORE)

        os.makedirs(source_dir, exist_ok=True)
        source_img.save(file_path, format="PNG", optimize=True)
        return f"{url_base}/{file_name}"
    except Exception:
        return None


def _draw_audience(draw: ImageDraw.ImageDraw, width: int, height: int, pulse: float):
    """Cria efeito de plateia grande ao fundo para cenário de palestra."""
    base_y = height - 24
    rows = 6
    for row in range(rows):
        y = base_y - row * 34
        crowd_count = 24 + row * 7
        head_r = max(4, 10 - row)
        shade = int(26 + row * 10 + pulse * 12)
        for i in range(crowd_count):
            x = int((i + 0.5) * (width / crowd_count) + ((-1) ** i) * (row + 1) * 1.2)
            draw.ellipse((x - head_r, y - head_r, x + head_r, y + head_r), fill=(shade, shade, shade + 8))
            if row >= 2:
                draw.rectangle(
                    (x - max(2, head_r // 2), y + head_r - 1, x + max(2, head_r // 2), y + head_r + 8),
                    fill=(shade - 3, shade - 3, shade + 4),
                )


def _draw_formal_stage_elements(draw: ImageDraw.ImageDraw, width: int, height: int, pulse: float):
    """Elementos corporativos de palco para reforçar estilo formal."""
    # Trilhas de luz
    beam_color = (52, 102, 168)
    draw.polygon([(0, 0), (220, 0), (80, 300)], outline=beam_color)
    draw.polygon([(width, 0), (width - 220, 0), (width - 80, 300)], outline=beam_color)
    draw.polygon([(260, 0), (420, 0), (320, 300)], outline=beam_color)

    # Tela de conferência no fundo
    panel_top = 96
    panel_left = 450
    panel_right = width - 60
    panel_bottom = 228
    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=16,
        fill=(17, 31, 56),
        outline=(83, 142, 210),
        width=2,
    )
    title_font = _load_font(20)
    subtitle_font = _load_font(16)
    draw.text((panel_left + 22, panel_top + 24), "Investor Conference · Executive Briefing", fill=(214, 230, 255), font=title_font)
    draw.text((panel_left + 22, panel_top + 58), "Ambiente formal para apresentação institucional", fill=(170, 195, 225), font=subtitle_font)
    pulse_bar = int(200 + 28 * pulse)
    draw.rounded_rectangle((panel_right - 210, panel_top + 30, panel_right - 24, panel_top + 46), radius=6, fill=(36, 70, 118))
    draw.rounded_rectangle((panel_right - 210, panel_top + 30, panel_right - 210 + pulse_bar // 2, panel_top + 46), radius=6, fill=(90, 192, 255))


def _draw_formal_podium(draw: ImageDraw.ImageDraw, cx: int, top: int, pulse: float, startup_name: str):
    podium_left = cx - 84
    podium_top = top + 235
    podium_right = cx + 142
    podium_bottom = top + 540

    # Base do púlpito
    draw.rounded_rectangle(
        (podium_left, podium_top, podium_right, podium_bottom),
        radius=20,
        fill=(18, 28, 50),
        outline=(84, 142, 214),
        width=3,
    )
    draw.polygon(
        [(podium_left + 16, podium_top + 10), (podium_right - 16, podium_top + 10), (podium_right - 28, podium_top + 45), (podium_left + 28, podium_top + 45)],
        fill=(29, 46, 82),
    )
    # Plaqueta institucional
    plate = (podium_left + 34, podium_top + 72, podium_right - 34, podium_top + 126)
    draw.rounded_rectangle(plate, radius=10, fill=(30, 58, 102))
    plate_font = _load_font(16)
    startup_short = (startup_name or "Startup")[:18]
    draw.text((plate[0] + 10, plate[1] + 16), f"{startup_short} · CEO", fill=(230, 240, 255), font=plate_font)
    # Microfones
    mic_bounce = int(5 * pulse)
    draw.line([(podium_left + 92, podium_top + 12), (podium_left + 74, podium_top - 55 - mic_bounce)], fill=(120, 140, 170), width=4)
    draw.line([(podium_left + 128, podium_top + 14), (podium_left + 144, podium_top - 52 + mic_bounce)], fill=(120, 140, 170), width=4)
    draw.ellipse((podium_left + 68, podium_top - 66 - mic_bounce, podium_left + 82, podium_top - 52 - mic_bounce), fill=(156, 170, 190))
    draw.ellipse((podium_left + 138, podium_top - 62 + mic_bounce, podium_left + 152, podium_top - 48 + mic_bounce), fill=(156, 170, 190))


def _draw_full_body_presenter(
    img: Image.Image,
    character_name: str,
    startup_name: str,
    face_patch: Image.Image | None,
    motion_t: float,
    scene_index: int,
):
    """Desenha apresentador de corpo inteiro, em postura formal e com gestos executivos."""
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(motion_t * 2.6 + scene_index * 0.9)

    cx = 200 + int(math.sin(motion_t * 1.0 + scene_index * 0.6) * 8)
    top = 112 + int(math.sin(motion_t * 1.8 + scene_index * 0.3) * 4)
    gesture_factor = 0.45 + (0.12 if scene_index % 2 == 0 else -0.08)

    # Sombra de palco
    draw.ellipse((cx - 120, 560, cx + 120, 620), fill=(8, 11, 18))
    _draw_formal_podium(draw, cx=cx, top=top, pulse=pulse, startup_name=startup_name)

    suit_dark = (16, 28, 52)
    suit_mid = (24, 42, 75)
    shirt = (226, 232, 240)
    tie = (170, 38, 58)
    skin = (205, 156, 128)

    # Pernas e sapatos
    draw.rounded_rectangle((cx - 52, top + 360, cx - 8, top + 536), radius=16, fill=(14, 25, 46))
    draw.rounded_rectangle((cx + 8, top + 360, cx + 52, top + 536), radius=16, fill=(14, 25, 46))
    draw.rounded_rectangle((cx - 70, top + 526, cx - 2, top + 552), radius=8, fill=(8, 12, 22))
    draw.rounded_rectangle((cx + 2, top + 526, cx + 70, top + 552), radius=8, fill=(8, 12, 22))

    # Tronco
    draw.rounded_rectangle((cx - 88, top + 150, cx + 88, top + 392), radius=36, fill=suit_dark, outline=(106, 184, 255), width=3)
    draw.polygon([(cx - 34, top + 166), (cx - 7, top + 270), (cx - 54, top + 270)], fill=suit_mid)
    draw.polygon([(cx + 34, top + 166), (cx + 7, top + 270), (cx + 54, top + 270)], fill=suit_mid)
    draw.polygon([(cx - 11, top + 166), (cx + 11, top + 166), (cx + 20, top + 255), (cx - 20, top + 255)], fill=shirt)
    draw.rectangle((cx - 6, top + 182, cx + 6, top + 300), fill=tie)
    draw.polygon([(cx - 6, top + 300), (cx + 6, top + 300), (cx, top + 332)], fill=tie)
    # Pocket square para formalidade
    draw.polygon([(cx + 35, top + 220), (cx + 55, top + 220), (cx + 48, top + 236)], fill=(240, 240, 240))

    # Braços com gestual formal (amplitude reduzida e postura executiva)
    left_shoulder = (cx - 62, top + 198)
    right_shoulder = (cx + 62, top + 198)

    left_elbow = (
        left_shoulder[0] - int(44 + 18 * pulse * gesture_factor),
        left_shoulder[1] + int(26 + 12 * math.sin(motion_t * 1.7 + 1.0)),
    )
    left_hand = (
        left_elbow[0] - int(32 + 12 * math.sin(motion_t * 2.0 + 0.7)),
        left_elbow[1] - int(16 + 10 * pulse * gesture_factor),
    )

    right_elbow = (
        right_shoulder[0] + int(40 + 14 * math.sin(motion_t * 1.7 + 0.8)),
        right_shoulder[1] + int(4 - 14 * pulse * gesture_factor),
    )
    right_hand = (
        right_elbow[0] + int(42 + 10 * pulse * gesture_factor),
        right_elbow[1] - int(20 + 10 * math.sin(motion_t * 2.1 + 1.8)),
    )

    draw.line([left_shoulder, left_elbow], fill=suit_mid, width=24, joint="curve")
    draw.line([left_elbow, left_hand], fill=suit_mid, width=18, joint="curve")
    draw.ellipse((left_hand[0] - 13, left_hand[1] - 13, left_hand[0] + 13, left_hand[1] + 13), fill=skin)

    draw.line([right_shoulder, right_elbow], fill=suit_mid, width=24, joint="curve")
    draw.line([right_elbow, right_hand], fill=suit_mid, width=18, joint="curve")
    draw.ellipse((right_hand[0] - 13, right_hand[1] - 13, right_hand[0] + 13, right_hand[1] + 13), fill=skin)
    # Clicker na mão direita para estilo de conferência
    draw.rounded_rectangle((right_hand[0] + 8, right_hand[1] - 4, right_hand[0] + 22, right_hand[1] + 9), radius=3, fill=(35, 40, 50))

    # Cabeça (usa face enviada quando disponível)
    head_size = 128
    head_left = cx - head_size // 2
    head_top = top + 20
    draw.ellipse((head_left - 2, head_top - 2, head_left + head_size + 2, head_top + head_size + 2), fill=(222, 201, 180))
    if face_patch is not None:
        face = ImageOps.fit(face_patch, (head_size, head_size), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (head_size, head_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, head_size, head_size), fill=255)
        img.paste(face, (head_left, head_top), mask)
    else:
        draw.ellipse((head_left, head_top, head_left + head_size, head_top + head_size), fill=skin)
        initials = (character_name[:2] or "AI").upper()
        draw.text((head_left + 28, head_top + 40), initials, fill=(255, 255, 255), font=_load_font(46))
    draw.ellipse((head_left, head_top, head_left + head_size, head_top + head_size), outline=(125, 211, 252), width=3)

    # Reflexo no palco para sensação mais cinematográfica
    glow_r = int(40 + pulse * 18)
    glow_g = int(96 + pulse * 30)
    glow_b = int(150 + pulse * 40)
    draw.ellipse((cx - 155, 84, cx + 155, 406), outline=(glow_r, glow_g, glow_b), width=3)


def _apply_cinematic_camera_and_grade(img: Image.Image, motion_t: float, scene_index: int):
    """Aplica zoom/pan suave e leve color grading para aspecto mais formal."""
    w, h = img.size
    zoom = 1.04 + 0.03 * (0.5 + 0.5 * math.sin(motion_t * 0.42 + scene_index * 0.6))
    zw = int(w * zoom)
    zh = int(h * zoom)
    enlarged = img.resize((zw, zh), Image.Resampling.LANCZOS)
    max_x = max(0, zw - w)
    max_y = max(0, zh - h)
    crop_x = int((0.5 + 0.5 * math.sin(motion_t * 0.37 + scene_index * 0.8)) * max_x)
    crop_y = int((0.5 + 0.5 * math.cos(motion_t * 0.33 + scene_index * 0.4)) * max_y * 0.72)
    frame = enlarged.crop((crop_x, crop_y, crop_x + w, crop_y + h))

    contrast = ImageEnhance.Contrast(frame).enhance(1.08)
    color = ImageEnhance.Color(contrast).enhance(0.94)
    sharp = ImageEnhance.Sharpness(color).enhance(1.15)
    return sharp


def _draw_scene(
    scene,
    character_name: str,
    startup_name: str,
    score: float,
    index: int,
    total: int,
    presenter_image: Image.Image | None = None,
    presenter_face_patch: Image.Image | None = None,
    motion_t: float = 0.0,
):
    width, height = 1280, 720
    if presenter_image is not None:
        bg = ImageOps.fit(presenter_image.copy(), (width, height), method=Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=18))
        dark_layer = Image.new("RGBA", (width, height), (8, 14, 24, 170))
        bg = bg.convert("RGBA")
        bg.alpha_composite(dark_layer)
        img = bg.convert("RGB")
    else:
        img = Image.new("RGB", (width, height), (10, 17, 30))
    draw = ImageDraw.Draw(img)
    title_font = _load_font(48)
    body_font = _load_font(34)
    small_font = _load_font(24)
    pulse = 0.5 + 0.5 * math.sin(motion_t * 2.2 + index * 0.8)

    # Header
    draw.rectangle((0, 0, width, 86), fill=(22, 38, 67))
    draw.text((30, 22), f"{startup_name} · Potencial de Investimento", fill=(255, 255, 255), font=small_font)
    draw.text((1040, 22), f"Score {score:.1f}/10", fill=(125, 211, 252), font=small_font)

    # Spotlights de palco + plateia
    draw.ellipse((-120, 70, 260, 520), outline=(69, 112, 170), width=3)
    draw.ellipse((190, 96, 540, 512), outline=(69, 112, 170), width=2)
    draw.ellipse((80, 420, 380, 670), fill=(9, 14, 24))
    draw.ellipse((0, 470, 430, 760), fill=(7, 10, 18))
    _draw_formal_stage_elements(draw, width, height, pulse)
    _draw_audience(draw, width, height, pulse)

    # Avatar/personagem
    if presenter_image is not None:
        _draw_full_body_presenter(
            img=img,
            character_name=character_name,
            startup_name=startup_name,
            face_patch=presenter_face_patch,
            motion_t=motion_t,
            scene_index=index,
        )
    else:
        avatar_center = (
            170 + int(math.sin(motion_t * 1.6 + index * 0.7) * 9),
            320 + int(math.sin(motion_t * 2.0 + index * 0.2) * 6),
        )
        avatar_radius = 110
        draw.ellipse(
            (
                avatar_center[0] - avatar_radius,
                avatar_center[1] - avatar_radius,
                avatar_center[0] + avatar_radius,
                avatar_center[1] + avatar_radius,
            ),
            fill=(37, 99, 235),
            outline=(125, 211, 252),
            width=5,
        )
        initials = (character_name[:2] or "AI").upper()
        draw.text((avatar_center[0] - 38, avatar_center[1] - 28), initials, fill=(255, 255, 255), font=_load_font(60))
    draw.text((45, 598), f"Apresentador Executivo: {character_name}", fill=(255, 255, 255), font=small_font)
    draw.text((45, 628), "Formato: Pitch institucional para investidores", fill=(178, 198, 226), font=_load_font(18))

    # Speech card
    draw.rounded_rectangle((355, 130, 1230, 620), radius=24, fill=(15, 25, 45), outline=(59, 130, 246), width=3)
    draw.text((390, 170), scene["title"], fill=(191, 219, 254), font=title_font)
    wrapped = scene.get("_wrapped_text")
    if not wrapped:
        wrapped = textwrap.fill(scene["text"], width=49)
        scene["_wrapped_text"] = wrapped
    draw.text((390, 255), wrapped, fill=(255, 255, 255), font=body_font, spacing=10)

    draw.text((390, 585), f"Cena {index}/{total}", fill=(148, 163, 184), font=small_font)

    if presenter_image is not None:
        img = _apply_cinematic_camera_and_grade(img, motion_t=motion_t, scene_index=index)
    return np.array(img)


async def _edge_tts_save(text: str, audio_path: str, preferred_voices: list[str] | None = None) -> tuple[bool, str]:
    if edge_tts is None:
        return False, ""
    voices = [str(v).strip() for v in (preferred_voices or []) if str(v).strip()]
    if not voices:
        voices = [
            os.getenv("EDGE_TTS_VOICE_PT_AO", "").strip(),
            "pt-PT-DuarteNeural",
            "pt-PT-RaquelNeural",
            "pt-BR-AntonioNeural",
        ]
        voices = [v for v in voices if v]

    for voice in voices:
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
            await communicate.save(audio_path)
            return True, voice
        except Exception:
            continue
    return False, ""


def _generate_tts_audio(
    narration_text: str,
    audio_path: str,
    *,
    preferred_voices: list[str] | None = None,
) -> tuple[bool, str]:
    # 1) tenta voz neural (mais natural e próxima do sotaque desejado)
    try:
        ok, used_voice = asyncio.run(_edge_tts_save(narration_text, audio_path, preferred_voices=preferred_voices))
        if ok:
            return True, f"edge-tts:{used_voice}"
    except Exception:
        pass

    # 2) fallback
    try:
        tts = gTTS(text=narration_text, lang="pt", tld="pt", slow=False)
        tts.save(audio_path)
        return True, "gtts-pt"
    except Exception:
        return False, "none"


def _safe_error_text(exc: Exception) -> str:
    text = str(exc).strip()
    return text if text else exc.__class__.__name__


def generate_explainer_video(
    analysis,
    output_path: str,
    presenter_image_path: str | None = None,
    presenter_image_url: str | None = None,
    presenter_source_urls: list[str] | None = None,
    generation_mode: str = "auto",
    progress_callback=None,
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    mode = str(generation_mode or "auto").strip().lower()
    if mode not in {"auto", "did_only", "local_only"}:
        mode = "auto"
    plan = build_video_plan_from_analysis(analysis)
    payload = _analysis_payload(analysis)
    startup_name = payload["startup_name"]
    score = payload["score"]
    presenter_image = _prepare_presenter_image(presenter_image_path)
    presenter_gender = _infer_presenter_gender_from_image(presenter_image_path)
    voice_profile = _resolve_voice_profile(presenter_gender)

    realistic_meta = None
    should_try_did = mode in {"auto", "did_only"}
    allow_local_render = mode in {"auto", "local_only"}
    if should_try_did:
        realistic_meta = _try_generate_realistic_video_did(
            plan=plan,
            source_image_url=presenter_image_url or "",
            output_path=output_path,
            source_image_urls=presenter_source_urls or [],
            presenter_gender=presenter_gender,
            real_image_only=(mode == "did_only"),
            progress_callback=progress_callback,
        )
    if realistic_meta and realistic_meta.get("status") == "done":
        return {
            "output_path": output_path,
            "engine_used": f"{plan.engine_used}+did",
            "character_name": plan.character_name,
            "voice_engine": f"did:{realistic_meta.get('voice_id')}",
            "voice_gender_target": realistic_meta.get("voice_gender_target", voice_profile.get("gender", "unknown")),
            "accent_target": "angola",
            "scene_count": len(plan.scenes),
            "generated_at": timezone.now().isoformat(),
            "narration_preview": plan.narration[:300],
            "presenter_image_used": bool(presenter_image_url),
            "realistic_provider": realistic_meta.get("provider"),
            "realistic_result_url": realistic_meta.get("result_url"),
            "realistic_talk_id": realistic_meta.get("talk_id"),
            "realistic_talk_ids": realistic_meta.get("talk_ids", []),
            "realistic_segment_count": realistic_meta.get("segment_count", 1),
            "realistic_source_count": realistic_meta.get("source_count", len(presenter_source_urls or [])),
            "realistic_style_mode": realistic_meta.get("style_mode", "cinematic_stage_presenter"),
            "realistic_real_image_only": bool(realistic_meta.get("real_image_only")),
            "target_duration_sec": _plan_total_duration_seconds(plan),
            "duration_range_sec": [MIN_VIDEO_SECONDS, MAX_VIDEO_SECONDS],
            "generation_mode": mode,
            "presenter_gender_inferred": presenter_gender,
        }

    if mode == "did_only":
        did_status = (realistic_meta or {}).get("status") or "failed"
        did_error = (realistic_meta or {}).get("error") or "Falha não detalhada pela API D-ID."
        segment_errors = (realistic_meta or {}).get("segment_errors") or []
        rescue_error = (realistic_meta or {}).get("rescue_error") or ""
        details = ""
        if segment_errors:
            details = " | fontes: " + " || ".join(str(err) for err in segment_errors[:3])
        if rescue_error:
            details += f" | rescue: {rescue_error}"
        raise ExplainerVideoGenerationError(
            f"Falha na geração no modo D-ID selecionado: status={did_status}, erro={did_error}{details}",
            did_status=did_status,
            did_error=f"{did_error}{details}",
        )
    if not allow_local_render:
        raise ExplainerVideoGenerationError("Modo de geração inválido para fallback local.")

    clips = []
    final_clip = None
    audio_clip = None
    tail_clip = None
    tts_engine = "none"
    tmp_audio_path = output_path.replace(".mp4", ".mp3")
    presenter_face_patch = _extract_face_patch(presenter_image)

    try:
        for idx, scene in enumerate(plan.scenes, start=1):
            if callable(progress_callback):
                try:
                    pct = 36 + int((idx / max(1, len(plan.scenes))) * 44)
                    progress_callback(
                        pct,
                        "renderizacao",
                        f"Renderizando cena {idx}/{len(plan.scenes)}",
                    )
                except Exception:
                    pass
            duration = float(scene["duration"])
            if presenter_image is not None:
                clip = VideoClip(
                    lambda t, _scene=scene, _idx=idx: _draw_scene(
                        _scene,
                        plan.character_name,
                        startup_name,
                        score,
                        _idx,
                        len(plan.scenes),
                        presenter_image=presenter_image,
                        presenter_face_patch=presenter_face_patch,
                        motion_t=float(t) + (_idx * 0.75),
                    ),
                    duration=duration,
                )
            else:
                frame = _draw_scene(
                    scene,
                    plan.character_name,
                    startup_name,
                    score,
                    idx,
                    len(plan.scenes),
                    presenter_image=presenter_image,
                )
                clip = ImageClip(frame).with_duration(duration)
            clips.append(clip)

        final_clip = concatenate_videoclips(clips, method="compose")

        has_audio, tts_engine = _generate_tts_audio(
            plan.narration,
            tmp_audio_path,
            preferred_voices=voice_profile.get("edge_voices") or None,
        )
        if has_audio and os.path.exists(tmp_audio_path):
            audio_clip = AudioFileClip(tmp_audio_path)

            if audio_clip.duration > MAX_VIDEO_SECONDS:
                speed_factor = float(audio_clip.duration) / float(MAX_VIDEO_SECONDS)
                audio_clip = audio_clip.with_speed_scaled(speed_factor)

            target_duration = max(
                float(MIN_VIDEO_SECONDS),
                min(float(MAX_VIDEO_SECONDS), float(audio_clip.duration)),
            )
            if target_duration > final_clip.duration + 0.25:
                tail_frame = final_clip.get_frame(max(0.0, final_clip.duration - 0.05))
                tail_clip = ImageClip(tail_frame).with_duration(target_duration - final_clip.duration)
                final_clip = concatenate_videoclips([final_clip, tail_clip], method="compose")
            elif target_duration + 0.25 < final_clip.duration:
                final_clip = final_clip.subclipped(0, target_duration)

            if audio_clip.duration > final_clip.duration + 0.15:
                audio_clip = audio_clip.subclipped(0, final_clip.duration).with_effects([afx.AudioFadeOut(0.8)])
            final_clip = final_clip.with_audio(audio_clip)

        final_clip.write_videofile(
            output_path,
            fps=18,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=2,
            logger=None,
        )
    except Exception as local_exc:
        local_error = _safe_error_text(local_exc)
        did_status = (realistic_meta or {}).get("status")
        did_error = (realistic_meta or {}).get("error")

        if realistic_meta:
            raise ExplainerVideoGenerationError(
                (
                    "Falha na geração do vídeo nos dois cenários. "
                    f"Realista (D-ID): status={did_status or 'unknown'}, erro={did_error or 'não informado'}. "
                    f"Local: {local_error}"
                ),
                did_status=did_status,
                did_error=did_error,
                local_error=local_error,
            ) from local_exc

        raise ExplainerVideoGenerationError(
            f"Falha na geração local do vídeo: {local_error}",
            local_error=local_error,
        ) from local_exc
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        if final_clip is not None:
            try:
                final_clip.close()
            except Exception:
                pass
        if audio_clip is not None:
            try:
                audio_clip.close()
            except Exception:
                pass
        if tail_clip is not None:
            try:
                tail_clip.close()
            except Exception:
                pass
        if os.path.exists(tmp_audio_path):
            try:
                os.remove(tmp_audio_path)
            except Exception:
                pass

    return {
        "output_path": output_path,
        "engine_used": plan.engine_used,
        "character_name": plan.character_name,
        "voice_engine": tts_engine,
        "voice_gender_target": voice_profile.get("gender", "unknown"),
        "accent_target": "angola",
        "scene_count": len(plan.scenes),
        "generated_at": timezone.now().isoformat(),
        "narration_preview": plan.narration[:300],
        "presenter_image_used": bool(presenter_image),
        "animation_mode": "formal_executive_stage_motion" if presenter_image is not None else "static_avatar",
        "target_duration_sec": _plan_total_duration_seconds(plan),
        "duration_range_sec": [MIN_VIDEO_SECONDS, MAX_VIDEO_SECONDS],
        "did_attempted": should_try_did,
        "did_status": (realistic_meta or {}).get("status"),
        "did_error": (realistic_meta or {}).get("error"),
        "generation_mode": mode,
        "presenter_gender_inferred": presenter_gender,
    }
