import io
import json
import os
import textwrap
import asyncio
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from django.utils import timezone
from gtts import gTTS
from moviepy import AudioFileClip, ImageClip, afx, concatenate_videoclips
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


def _prepare_presenter_image(image_path: str | None):
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGB")
        return img
    except Exception:
        return None


def _draw_scene(
    scene,
    character_name: str,
    startup_name: str,
    score: float,
    index: int,
    total: int,
    presenter_image: Image.Image | None = None,
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

    # Header
    draw.rectangle((0, 0, width, 86), fill=(22, 38, 67))
    draw.text((30, 22), f"{startup_name} · Potencial de Investimento", fill=(255, 255, 255), font=small_font)
    draw.text((1040, 22), f"Score {score:.1f}/10", fill=(125, 211, 252), font=small_font)

    # Avatar/personagem
    if presenter_image is not None:
        portrait = ImageOps.fit(presenter_image.copy(), (310, 430), method=Image.Resampling.LANCZOS)
        img.paste(portrait, (30, 145))
        draw.rounded_rectangle((25, 140, 345, 580), radius=18, outline=(125, 211, 252), width=4)
    else:
        avatar_center = (170, 320)
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
    draw.text((45, 600), f"Apresentador: {character_name}", fill=(255, 255, 255), font=small_font)

    # Speech card
    draw.rounded_rectangle((320, 130, 1220, 620), radius=24, fill=(15, 25, 45), outline=(59, 130, 246), width=3)
    draw.text((360, 170), scene["title"], fill=(191, 219, 254), font=title_font)
    wrapped = textwrap.fill(scene["text"], width=55)
    draw.text((360, 255), wrapped, fill=(255, 255, 255), font=body_font, spacing=10)

    draw.text((360, 585), f"Cena {index}/{total}", fill=(148, 163, 184), font=small_font)

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


def generate_explainer_video(analysis, output_path: str, presenter_image_path: str | None = None):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plan = build_video_plan_from_analysis(analysis)
    payload = _analysis_payload(analysis)
    startup_name = payload["startup_name"]
    score = payload["score"]
    presenter_image = _prepare_presenter_image(presenter_image_path)

    clips = []
    for idx, scene in enumerate(plan.scenes, start=1):
        frame = _draw_scene(
            scene,
            plan.character_name,
            startup_name,
            score,
            idx,
            len(plan.scenes),
            presenter_image=presenter_image,
        )
        clip = ImageClip(frame).with_duration(float(scene["duration"]))
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
    }
