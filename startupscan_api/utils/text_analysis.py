import logging
from ..commom_imports import ensure_nlp_imports


def analyze_text(text):
    text_features = {
        'sentiment': "neutral",
        'sentiment_score': 0.5,
        'dominant_topic': "general",
        'topic_score': 0.5,
        'readability': 50.0,
    }

    if not text or not isinstance(text, str):
        return text_features

    try:
        ensure_nlp_imports()
        pipeline_fn = globals().get("pipeline")
        textstat_module = globals().get("textstat")

        if not callable(pipeline_fn) or textstat_module is None:
            lowered = text.lower()
            positive_words = ("crescimento", "receita", "lucro", "escala", "inovação", "cliente")
            hits = sum(1 for w in positive_words if w in lowered)
            sentiment_score = min(1.0, 0.4 + hits * 0.1)
            readability = max(20.0, min(90.0, 100.0 - (len(text.split()) / 12.0)))
            topic = (
                "technology"
                if any(k in lowered for k in ("ia", "software", "app", "plataforma"))
                else "general"
            )
            text_features.update({
                "sentiment": "positive" if sentiment_score >= 0.6 else "neutral",
                "sentiment_score": float(sentiment_score),
                "dominant_topic": topic,
                "topic_score": 0.6,
                "readability": float(readability),
            })
            return text_features

        sentiment_analyzer = pipeline_fn(
            "text-classification",
            model="finiteautomata/bertweet-base-sentiment-analysis",
        )
        sentiment_result = sentiment_analyzer(text[:512])[0]

        topic_analyzer = pipeline_fn(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )
        topics = topic_analyzer(
            text[:512],
            candidate_labels=["technology", "finance", "marketing", "product", "team"],
        )

        readability = textstat_module.flesch_reading_ease(text)

        text_features.update({
            'sentiment': sentiment_result['label'],
            'sentiment_score': float(sentiment_result['score']),
            'dominant_topic': topics['labels'][0],
            'topic_score': float(topics['scores'][0]),
            'readability': float(readability),
        })

    except Exception as e:
        logging.error(f"Erro na análise de texto: {str(e)}")

    return text_features
