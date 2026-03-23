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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

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


def _draw_full_body_presenter(
    img: Image.Image,
    character_name: str,
    face_patch: Image.Image | None,
    motion_t: float,
    scene_index: int,
):
    """Desenha apresentador de corpo inteiro com gestos animados."""
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(motion_t * 2.6 + scene_index * 0.9)

    cx = 205 + int(math.sin(motion_t * 1.2 + scene_index * 0.6) * 14)
    top = 120 + int(math.sin(motion_t * 2.0 + scene_index * 0.3) * 5)

    # Sombra de palco
    draw.ellipse((cx - 120, 560, cx + 120, 620), fill=(8, 11, 18))

    suit_dark = (20, 35, 66)
    suit_mid = (31, 52, 93)
    shirt = (226, 232, 240)
    tie = (192, 43, 60)
    skin = (205, 156, 128)

    # Pernas e sapatos
    draw.rounded_rectangle((cx - 55, top + 360, cx - 8, top + 530), radius=16, fill=(16, 27, 51))
    draw.rounded_rectangle((cx + 8, top + 360, cx + 55, top + 530), radius=16, fill=(16, 27, 51))
    draw.rounded_rectangle((cx - 72, top + 522, cx - 2, top + 548), radius=8, fill=(9, 13, 25))
    draw.rounded_rectangle((cx + 2, top + 522, cx + 72, top + 548), radius=8, fill=(9, 13, 25))

    # Tronco
    draw.rounded_rectangle((cx - 92, top + 150, cx + 92, top + 392), radius=36, fill=suit_dark, outline=(106, 184, 255), width=3)
    draw.polygon([(cx - 34, top + 166), (cx - 7, top + 270), (cx - 54, top + 270)], fill=suit_mid)
    draw.polygon([(cx + 34, top + 166), (cx + 7, top + 270), (cx + 54, top + 270)], fill=suit_mid)
    draw.polygon([(cx - 11, top + 166), (cx + 11, top + 166), (cx + 20, top + 255), (cx - 20, top + 255)], fill=shirt)
    draw.rectangle((cx - 6, top + 182, cx + 6, top + 300), fill=tie)
    draw.polygon([(cx - 6, top + 300), (cx + 6, top + 300), (cx, top + 332)], fill=tie)

    # Braços com gestos animados
    left_shoulder = (cx - 66, top + 196)
    right_shoulder = (cx + 66, top + 196)

    left_elbow = (
        left_shoulder[0] - int(58 + 24 * pulse),
        left_shoulder[1] + int(14 + 18 * math.sin(motion_t * 2.1 + 1.0)),
    )
    left_hand = (
        left_elbow[0] - int(50 + 20 * math.sin(motion_t * 2.7 + 0.7)),
        left_elbow[1] - int(34 + 18 * pulse),
    )

    right_elbow = (
        right_shoulder[0] + int(52 + 18 * math.sin(motion_t * 1.9 + 0.8)),
        right_shoulder[1] - int(10 + 22 * pulse),
    )
    right_hand = (
        right_elbow[0] + int(58 + 18 * pulse),
        right_elbow[1] - int(30 + 16 * math.sin(motion_t * 2.5 + 1.8)),
    )

    draw.line([left_shoulder, left_elbow], fill=suit_mid, width=26, joint="curve")
    draw.line([left_elbow, left_hand], fill=suit_mid, width=20, joint="curve")
    draw.ellipse((left_hand[0] - 15, left_hand[1] - 15, left_hand[0] + 15, left_hand[1] + 15), fill=skin)

    draw.line([right_shoulder, right_elbow], fill=suit_mid, width=26, joint="curve")
    draw.line([right_elbow, right_hand], fill=suit_mid, width=20, joint="curve")
    draw.ellipse((right_hand[0] - 15, right_hand[1] - 15, right_hand[0] + 15, right_hand[1] + 15), fill=skin)

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
    _draw_audience(draw, width, height, pulse)

    # Avatar/personagem
    if presenter_image is not None:
        _draw_full_body_presenter(
            img=img,
            character_name=character_name,
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
    draw.text((45, 600), f"Apresentador no palco: {character_name}", fill=(255, 255, 255), font=small_font)

    # Speech card
    draw.rounded_rectangle((355, 130, 1230, 620), radius=24, fill=(15, 25, 45), outline=(59, 130, 246), width=3)
    draw.text((390, 170), scene["title"], fill=(191, 219, 254), font=title_font)
    wrapped = scene.get("_wrapped_text")
    if not wrapped:
        wrapped = textwrap.fill(scene["text"], width=49)
        scene["_wrapped_text"] = wrapped
    draw.text((390, 255), wrapped, fill=(255, 255, 255), font=body_font, spacing=10)

    draw.text((390, 585), f"Cena {index}/{total}", fill=(148, 163, 184), font=small_font)

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
    presenter_face_patch = _extract_face_patch(presenter_image)
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

    tmp_audio_path = output_path.replace(".mp4", ".mp3")
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

    # Fechar recursos explícitos
    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    try:
        final_clip.close()
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
        "animation_mode": "full_body_stage_motion" if presenter_image is not None else "static_avatar",
        "did_attempted": bool(realistic_meta),
        "did_status": (realistic_meta or {}).get("status"),
        "did_error": (realistic_meta or {}).get("error"),
    }
