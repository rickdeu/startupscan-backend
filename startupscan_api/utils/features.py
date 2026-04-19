from ..commom_imports import np, pd
from .audio import process_audio
from .video import process_video
from .text_analysis import analyze_text


def prepare_features(pitch_row, financial_row):
    audio_path = pitch_row.get('audio_path')
    video_path = pitch_row.get('video_path')

    audio_features = (
        process_audio(audio_path)
        if audio_path and pd.notna(audio_path)
        else process_audio(None)
    )
    video_features = (
        process_video(video_path)
        if video_path and pd.notna(video_path)
        else process_video(None)
    )
    text_features = (
        analyze_text(pitch_row['text'])
        if 'text' in pitch_row
        else analyze_text("")
    )

    emotion_map = {
        'happy': 1, 'neutral': 0, 'sad': -1,
        'angry': -1, 'surprise': 0.5, 'fear': -0.5,
    }

    features = [
        text_features['sentiment_score'],
        text_features['topic_score'],
        text_features['readability'] / 100,
        audio_features['mfcc_mean'],
        audio_features['pitch_variation'],
        audio_features['speech_rate'] / 200,
        emotion_map.get(video_features['dominant_emotion'], 0),
        video_features['emotion_confidence'],
        financial_row['revenue'] / 1e6 if 'revenue' in financial_row else 0,
        financial_row['growth_rate'] / 100 if 'growth_rate' in financial_row else 0,
        financial_row['profit_margin'] / 100 if 'profit_margin' in financial_row else 0,
    ]

    return np.array(features), {
        'text': text_features,
        'audio': audio_features,
        'video': video_features,
        'financial': dict(financial_row) if isinstance(financial_row, (pd.Series, dict)) else {},
    }
