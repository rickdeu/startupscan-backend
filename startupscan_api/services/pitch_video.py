import io
import json
import os
import textwrap
import asyncio
import time
import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import requests
from django.utils import timezone
from gtts import gTTS
from moviepy import AudioFileClip, ImageClip, VideoClip, afx, concatenate_videoclips
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

    thesis = investor_pitch.get("investment_thesis", "Oportunidade com potencial relevante para investidores.")
    readiness = investor_pitch.get("funding_readiness", "Em evolução")
    suggested_ticket = investor_pitch.get("suggested_ticket", "Seed com acompanhamento estratégico")

    top_categories = []
    if isinstance(category_scores, dict):
        sorted_items = sorted(category_scores.items(), key=lambda kv: float(kv[1]), reverse=True)[:3]
        top_categories = [f"{k.replace('_', ' ').title()}: {v}/10" for k, v in sorted_items]

    scenes = [
        {
            "title": "Apresentação da Startup",
            "text": f"Olá, eu sou {character_name}. Hoje vou apresentar o potencial de {startup_name} para investidores. "
            f"O score atual da startup é {score:.1f} de 10.",
            "duration": 7,
        },
        {
            "title": "Resumo Estratégico",
            "text": summary or "A startup apresenta uma proposta consistente, com sinais de tração e escalabilidade.",
            "duration": 8,
        },
        {
            "title": "Pontos Fortes",
            "text": " • ".join(strengths) if strengths else "Execução orientada por métricas, foco em crescimento e base para escala.",
            "duration": 8,
        },
        {
            "title": "Indicadores de Mercado",
            "text": (
                f"Receita: AOA {payload['revenue']:,.0f}. "
                f"Crescimento: {payload['growth_rate']:.1f}%. "
                f"Margem: {payload['profit_margin']:.1f}%. "
                "No contexto angolano, estes sinais mostram base sólida para escalar."
            ),
            "duration": 7,
        },
        {
            "title": "Potencial para Investimento",
            "text": f"{thesis} Prontidão: {readiness}. Ticket sugerido: {suggested_ticket}.",
            "duration": 8,
        },
        {
            "title": "Categorias com Maior Destaque",
            "text": " • ".join(top_categories) if top_categories else "Clareza de proposta, viabilidade e potencial de mercado.",
            "duration": 7,
        },
        {
            "title": "Próximos Passos",
            "text": " • ".join(recommendations)
            if recommendations
            else "Recomendamos acelerar estratégia comercial, fortalecer produto e preparar a captação com foco no mercado angolano.",
            "duration": 8,
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
        prompt = {
            "task": (
                "Crie um roteiro criativo em portugues para video explicativo de potencial de startup. "
                "Retorne JSON com: character_name, narration, scenes(list de objetos com title,text,duration). "
                "Duração total entre 45 e 70 segundos."
            ),
            "analysis_payload": payload,
        }
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0.45,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Você é roteirista de vídeos de investimento para startups."},
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
            duration = int(float(s.get("duration", 7) or 7))
            duration = max(4, min(12, duration))
            fixed_scenes.append({"title": title, "text": text, "duration": duration})
        narration = str(data.get("narration", "")).strip() or " ".join(scene["text"] for scene in fixed_scenes)
        character_name = str(data.get("character_name", payload["startup_name"])).strip() or payload["startup_name"]
        return VideoPlan(
            scenes=fixed_scenes[:9],
            narration=narration,
            character_name=character_name,
            engine_used="gpt",
        )
    except Exception:
        return None


def build_video_plan_from_analysis(analysis) -> VideoPlan:
    payload = _analysis_payload(analysis)
    plan = _gpt_video_plan(payload)
    if plan is not None:
        return plan
    return _local_video_plan(payload)


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


def _try_generate_realistic_video_did(plan: VideoPlan, source_image_url: str, output_path: str):
    """
    Usa D-ID para gerar vídeo de avatar realista com gestos/lip-sync.
    Retorna metadados ou None em caso de falha/sem configuração.
    """
    api_key = os.getenv("DID_API_KEY", "").strip()
    if not api_key or not source_image_url:
        return None

    auth_value = api_key if api_key.lower().startswith("basic ") else f"Basic {api_key}"
    base_url = os.getenv("DID_API_BASE_URL", "https://api.d-id.com").rstrip("/")
    create_url = f"{base_url}/talks"
    voice_id = os.getenv("DID_VOICE_ID", "pt-PT-DuarteNeural")

    script_text = plan.narration.strip()
    if len(script_text) > 1600:
        script_text = script_text[:1600].rsplit(" ", 1)[0] + "."

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
    headers = {
        "Authorization": auth_value,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        create_resp = requests.post(create_url, headers=headers, data=json.dumps(payload), timeout=120)
        if create_resp.status_code >= 400:
            body_preview = (create_resp.text or "")[:400]
            return {
                "provider": "did",
                "status": "failed",
                "voice_id": voice_id,
                "error": f"create_failed:{create_resp.status_code}:{body_preview}",
            }
        create_data = create_resp.json() if create_resp.content else {}
        talk_id = create_data.get("id")
        if not talk_id:
            return {
                "provider": "did",
                "status": "failed",
                "voice_id": voice_id,
                "error": "missing_talk_id",
            }

        status_url = f"{create_url}/{talk_id}"
        result_url = None
        status_value = "created"
        error_message = ""
        for _ in range(90):
            poll_resp = requests.get(status_url, headers=headers, timeout=60)
            if poll_resp.status_code >= 400:
                error_message = f"poll_failed:{poll_resp.status_code}:{(poll_resp.text or '')[:300]}"
                break
            poll_data = poll_resp.json() if poll_resp.content else {}
            status_value = str(poll_data.get("status", "")).lower()
            if status_value == "done":
                result_url = poll_data.get("result_url")
                break
            if status_value in {"error", "failed", "rejected"}:
                error_message = str(poll_data.get("error", "failed"))
                break
            time.sleep(2.2)

        if not result_url:
            return {
                "provider": "did",
                "talk_id": talk_id,
                "status": status_value or "failed",
                "voice_id": voice_id,
                "error": error_message or "no_result_url",
            }

        ok = _download_binary_file(result_url, output_path)
        if not ok:
            return {
                "provider": "did",
                "talk_id": talk_id,
                "status": "failed",
                "voice_id": voice_id,
                "error": "result_download_failed",
            }

        return {
            "provider": "did",
            "talk_id": talk_id,
            "result_url": result_url,
            "status": "done",
            "voice_id": voice_id,
            "error": error_message,
        }
    except Exception as exc:
        return {
            "provider": "did",
            "status": "failed",
            "voice_id": voice_id,
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


async def _edge_tts_save(text: str, audio_path: str) -> bool:
    if edge_tts is None:
        return False
    preferred_voices = [
        os.getenv("EDGE_TTS_VOICE_PT_AO", "").strip(),
        "pt-PT-DuarteNeural",
        "pt-PT-RaquelNeural",
        "pt-BR-AntonioNeural",
    ]
    preferred_voices = [v for v in preferred_voices if v]

    for voice in preferred_voices:
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
            await communicate.save(audio_path)
            return True
        except Exception:
            continue
    return False


def _generate_tts_audio(narration_text: str, audio_path: str) -> tuple[bool, str]:
    # 1) tenta voz neural (mais natural e próxima do sotaque desejado)
    try:
        ok = asyncio.run(_edge_tts_save(narration_text, audio_path))
        if ok:
            return True, "edge-tts-pt"
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
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plan = build_video_plan_from_analysis(analysis)
    payload = _analysis_payload(analysis)
    startup_name = payload["startup_name"]
    score = payload["score"]
    presenter_image = _prepare_presenter_image(presenter_image_path)

    realistic_meta = _try_generate_realistic_video_did(
        plan=plan,
        source_image_url=presenter_image_url or "",
        output_path=output_path,
    )
    if realistic_meta and realistic_meta.get("status") == "done":
        return {
            "output_path": output_path,
            "engine_used": f"{plan.engine_used}+did",
            "character_name": plan.character_name,
            "voice_engine": f"did:{realistic_meta.get('voice_id')}",
            "accent_target": "angola",
            "scene_count": len(plan.scenes),
            "generated_at": timezone.now().isoformat(),
            "narration_preview": plan.narration[:300],
            "presenter_image_used": bool(presenter_image_url),
            "realistic_provider": realistic_meta.get("provider"),
            "realistic_result_url": realistic_meta.get("result_url"),
            "realistic_talk_id": realistic_meta.get("talk_id"),
        }

    clips = []
    final_clip = None
    audio_clip = None
    tts_engine = "none"
    tmp_audio_path = output_path.replace(".mp4", ".mp3")
    presenter_face_patch = _extract_face_patch(presenter_image)

    try:
        for idx, scene in enumerate(plan.scenes, start=1):
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

        has_audio, tts_engine = _generate_tts_audio(plan.narration, tmp_audio_path)
        if has_audio and os.path.exists(tmp_audio_path):
            audio_clip = AudioFileClip(tmp_audio_path)
            if audio_clip.duration < final_clip.duration:
                audio_clip = audio_clip.with_effects([afx.AudioLoop(duration=final_clip.duration)])
            elif audio_clip.duration > final_clip.duration:
                audio_clip = audio_clip.subclipped(0, final_clip.duration)
            final_clip = final_clip.with_audio(audio_clip)

        final_clip.write_videofile(
            output_path,
            fps=24,
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
        "accent_target": "angola",
        "scene_count": len(plan.scenes),
        "generated_at": timezone.now().isoformat(),
        "narration_preview": plan.narration[:300],
        "presenter_image_used": bool(presenter_image),
        "animation_mode": "formal_executive_stage_motion" if presenter_image is not None else "static_avatar",
        "did_attempted": bool(realistic_meta),
        "did_status": (realistic_meta or {}).get("status"),
        "did_error": (realistic_meta or {}).get("error"),
    }
