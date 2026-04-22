import logging
from ..commom_imports import (
    ensure_audio_imports, whisper, librosa, sf, sr, np
)

logger = logging.getLogger(__name__)


def process_audio(audio_path):
    audio_features = {
        'transcription': "Transcrição não disponível",
        'mfcc_mean': 0,
        'pitch_variation': 0,
        'speech_rate': 0,
    }

    if audio_path is None:
        return audio_features

    import os
    if not os.path.exists(audio_path):
        return audio_features

    try:
        ensure_audio_imports()
        if whisper is None or librosa is None:
            raise RuntimeError("libs de áudio indisponíveis")

        whisper_model = whisper.load_model("base")
        result = whisper_model.transcribe(audio_path)
        transcription = result['text']

        y, sr_rate = librosa.load(audio_path)
        mfcc = librosa.feature.mfcc(y=y, sr=sr_rate)
        pitch = librosa.feature.rms(y=y)

        audio_features.update({
            'transcription': transcription,
            'mfcc_mean': float(np.mean(mfcc)),
            'pitch_variation': float(np.std(pitch)),
            'speech_rate': len(transcription.split()) / (len(y) / sr_rate) * 60,
        })

    except Exception as e:
        logging.error(f"Erro no processamento de áudio: {str(e)}")
        try:
            if sr is None:
                ensure_audio_imports()
            if sr is None:
                raise RuntimeError("speech_recognition indisponível")
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio_data = r.record(source)
                transcription = r.recognize_google(audio_data, language='pt-BR')
                audio_features['transcription'] = transcription
        except Exception:
            logger.warning("Fallback speech_recognition também falhou para %s", audio_path)

    return audio_features
