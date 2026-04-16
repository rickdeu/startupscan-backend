from .commom_imports import *
import hashlib
import logging

logger = logging.getLogger(__name__)


# 🔊 9. Função de Processamento de Áudio Completa
def process_audio(audio_path):
    """Processamento de áudio com Whisper e extração de features adicionais"""
    audio_features = {
        'transcription': "Transcrição não disponível",
        'mfcc_mean': 0,
        'pitch_variation': 0,
        'speech_rate': 0
    }

    if audio_path is None or not os.path.exists(audio_path):
        return audio_features

    try:
        ensure_audio_imports()
        if whisper is None or librosa is None:
            raise RuntimeError("libs de áudio indisponíveis")
        # Transcrição do texto
        whisper_model = whisper.load_model("base")
        result = whisper_model.transcribe(audio_path)
        transcription = result['text']

        # Extração de features acústicas
        y, sr = librosa.load(audio_path)
        mfcc = librosa.feature.mfcc(y=y, sr=sr)
        pitch = librosa.feature.rms(y=y)

        audio_features.update({
            'transcription': transcription,
            'mfcc_mean': float(np.mean(mfcc)),
            'pitch_variation': float(np.std(pitch)),
            'speech_rate': len(transcription.split()) / (len(y)/sr) * 60  # palavras por minuto
        })

    except Exception as e:
        logging.error(f"Erro no processamento de áudio: {str(e)}")
        try:
            # Fallback usando speech_recognition
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








# 🎥 10. Função de Processamento de Vídeo Completa
def process_video(video_path):
    """Processamento de vídeo com OpenCV e análise de expressões faciais"""
    video_features = {
        'dominant_emotion': "neutral",
        'emotion_confidence': 0,
        'frame_count': 0
    }

    if video_path is None or not os.path.exists(video_path):
        return video_features

    try:
        ensure_video_imports()
        if cv2 is None or mp is None or mp_editor is None:
            raise RuntimeError("libs base de vídeo indisponíveis")
        # Extrair áudio do vídeo primeiro
        temp_audio_path = "temp_audio.wav"
        clip = mp_editor.VideoFileClip(video_path)
        clip.audio.write_audiofile(temp_audio_path)

        # Processar áudio
        audio_features = process_audio(temp_audio_path)

        # Configurações de análise de vídeo
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

        cap = cv2.VideoCapture(video_path)
        emotions = []
        confidence_scores = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 5 == 0:  # Analisar a cada 5 frames
                try:
                    # Converter BGR (OpenCV) para RGB
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Análise com MediaPipe
                    results = face_detection.process(rgb_frame)

                    if results.detections:
                        # Análise com DeepFace
                        if DeepFace is not None:
                            result = DeepFace.analyze(rgb_frame, actions=['emotion'], enforce_detection=False)
                            emotions.append(result[0]['dominant_emotion'])
                            confidence_scores.append(result[0]['face_confidence'])
                except Exception as e:
                    logging.error(f"Erro no frame {frame_count}: {str(e)}")

            frame_count += 1

        cap.release()

        # Extrair estatísticas
        if emotions:
            emotion_counts = Counter(emotions)
            dominant_emotion = emotion_counts.most_common(1)[0][0]
            avg_confidence = float(np.mean(confidence_scores))
        else:
            dominant_emotion = "neutral"
            avg_confidence = 0.0

        video_features.update({
            'dominant_emotion': dominant_emotion,
            'emotion_confidence': avg_confidence,
            'frame_count': frame_count,
            'audio_features': audio_features
        })

    except Exception as e:
        logging.error(f"Erro no processamento de vídeo: {str(e)}")

    return video_features




# 📄 11. Função de Análise de Texto Completa
def analyze_text(text):
    """Análise de texto com modelos state-of-the-art"""
    text_features = {
        'sentiment': "neutral",
        'sentiment_score': 0.5,
        'dominant_topic': "general",
        'topic_score': 0.5,
        'readability': 50.0
    }

    if not text or not isinstance(text, str):
        return text_features

    try:
        ensure_nlp_imports()
        pipeline_fn = globals().get("pipeline")
        textstat_module = globals().get("textstat")

        # Fallback leve quando transformers/textstat não estiverem disponíveis
        if not callable(pipeline_fn) or textstat_module is None:
            lowered = text.lower()
            positive_words = ("crescimento", "receita", "lucro", "escala", "inovação", "cliente")
            hits = sum(1 for w in positive_words if w in lowered)
            sentiment_score = min(1.0, 0.4 + hits * 0.1)
            readability = max(20.0, min(90.0, 100.0 - (len(text.split()) / 12.0)))
            topic = "technology" if any(k in lowered for k in ("ia", "software", "app", "plataforma")) else "general"
            text_features.update({
                "sentiment": "positive" if sentiment_score >= 0.6 else "neutral",
                "sentiment_score": float(sentiment_score),
                "dominant_topic": topic,
                "topic_score": 0.6,
                "readability": float(readability),
            })
            return text_features

        # Análise de sentimento
        sentiment_analyzer = pipeline_fn("text-classification",
                                   model="finiteautomata/bertweet-base-sentiment-analysis")
        sentiment_result = sentiment_analyzer(text[:512])[0]  # Limitar tamanho para o modelo

        # Análise de tópicos
        topic_analyzer = pipeline_fn("zero-shot-classification",
                                model="facebook/bart-large-mnli")
        topics = topic_analyzer(text[:512],  # Limitar tamanho
                              candidate_labels=["technology", "finance", "marketing", "product", "team"])

        # Métricas de legibilidade
        readability = textstat_module.flesch_reading_ease(text)

        text_features.update({
            'sentiment': sentiment_result['label'],
            'sentiment_score': float(sentiment_result['score']),
            'dominant_topic': topics['labels'][0],
            'topic_score': float(topics['scores'][0]),
            'readability': float(readability)
        })

    except Exception as e:
        logging.error(f"Erro na análise de texto: {str(e)}")

    return text_features


# 📊 12. Função de Preparação de Features
def prepare_features(pitch_row, financial_row):
    """Prepara features para o modelo de ML"""
    # Processar cada modalidade
    audio_features = process_audio(pitch_row['audio_path']) if 'audio_path' in pitch_row and pd.notna(pitch_row['audio_path']) else process_audio(None)
    video_features = process_video(pitch_row['video_path']) if 'video_path' in pitch_row and pd.notna(pitch_row['video_path']) else process_video(None)
    text_features = analyze_text(pitch_row['text']) if 'text' in pitch_row else analyze_text("")

    # Mapeamento de emoções para valores numéricos
    emotion_map = {'happy': 1, 'neutral': 0, 'sad': -1, 'angry': -1, 'surprise': 0.5, 'fear': -0.5}

    # Criar vetor de features
    features = [
        text_features['sentiment_score'],
        text_features['topic_score'],
        text_features['readability'] / 100,  # Normalizar
        audio_features['mfcc_mean'],
        audio_features['pitch_variation'],
        audio_features['speech_rate'] / 200,  # Normalizar
        emotion_map.get(video_features['dominant_emotion'], 0),
        video_features['emotion_confidence'],
        
        financial_row['revenue'] / 1e6 if 'revenue' in financial_row else 0,  # Milhões
        financial_row['growth_rate'] / 100 if 'growth_rate' in financial_row else 0,  # Percentual
        financial_row['profit_margin'] / 100 if 'profit_margin' in financial_row else 0  # Percentual
    ]

    return np.array(features), {
        'text': text_features,
        'audio': audio_features,
        'video': video_features,
        'financial': dict(financial_row) if isinstance(financial_row, (pd.Series, dict)) else {}
    }




# 🧠 13. Função de Treinamento e Avaliação
def train_and_evaluate(df, financial_df):
    """Treina e avalia o modelo com validação cruzada"""
    # Preparar dados
    X = []
    y = []
    metadata = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="A treinar o modelo: "):
        financial_idx = idx % len(financial_df)
        financial_row = financial_df.iloc[financial_idx] if isinstance(financial_df, pd.DataFrame) else financial_df[financial_idx]

        features, meta = prepare_features(row, financial_row)
        X.append(features)

        if 'success_score' in row:
            y.append(row['success_score'])
        else:
            y.append(5.0)  # Valor padrão se não houver score

        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)

    # Pipeline de modelagem
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        ))
    ])

    # Validação cruzada
    if len(X) > 1:  # Só faz validação cruzada se tiver dados suficientes
        scores = cross_val_score(model, X, y, cv=min(5, len(X)), scoring='r2')
        logging.info(f"R2 médio na validação cruzada: {np.mean(scores):.2f} (±{np.std(scores):.2f})")

    # Treinar modelo final
    model.fit(X, y)

    return model, metadata






# ⚙️ FUNÇÃO DE TREINAMENTO COM RANDOM FOREST
def train_with_random_forest(df, financial_df):
    ensure_plot_imports()
    X, y, metadata = [], [], []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Treinando com Random Forest"):
        financial_idx = idx % len(financial_df)
        financial_row = financial_df.iloc[financial_idx] if isinstance(financial_df, pd.DataFrame) else financial_df[financial_idx]
        features, meta = prepare_features(row, financial_row)

        X.append(features)
        y.append(row.get('success_score', 5.0))
        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    # Métricas
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    logging.info(f"Random Forest - MSE: {mse:.2f}, R2: {r2:.2f}")

    # Gráfico de desempenho
    if plt is not None:
        plt.figure()
        plt.scatter(y_test, predictions, alpha=0.7)
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'r--')
        plt.xlabel('Valor Real')
        plt.ylabel('Predição')
        plt.title('Random Forest: Real vs Previsto')
        plt.grid(True)
        plt.show()

    # Matriz de Confusão Multiclasse
    y_true_class = np.clip(np.round(y_test), 1, 10).astype(int)
    y_pred_class = np.clip(np.round(predictions), 1, 10).astype(int)

    cm = confusion_matrix(y_true_class, y_pred_class, labels=range(1, 11))
    if plt is not None:
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=range(1, 11))
        disp.plot(cmap=plt.cm.Blues, values_format='d')
        plt.title("Matriz de Confusão Multiclasse - Random Forest")
        plt.xlabel("Previsto")
        plt.ylabel("Real")
        plt.grid(False)
        plt.show()

    return model, metadata







# ⚙️ FUNÇÃO DE TREINAMENTO COM XGBOOST
def train_with_xgboost(df, financial_df):
    ensure_plot_imports()
    X, y, metadata = [], [], []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Treinando com XGBoost"):
        financial_idx = idx % len(financial_df)
        financial_row = financial_df.iloc[financial_idx] if isinstance(financial_df, pd.DataFrame) else financial_df[financial_idx]
        features, meta = prepare_features(row, financial_row)

        X.append(features)
        y.append(row.get('success_score', 5.0))
        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42))
    ])

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    # Métricas
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    logging.info(f"XGBoost - MSE: {mse:.2f}, R2: {r2:.2f}")

    # Gráfico de desempenho
    if plt is not None:
        plt.figure()
        plt.scatter(y_test, predictions, alpha=0.6, color='orange')
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'b--')
        plt.xlabel("Real")
        plt.ylabel("Previsto")
        plt.title("XGBoost: Real vs Previsto")
        plt.grid(True)
        plt.show()

    # Matriz de Confusão Multiclasse
    y_true_class = np.clip(np.round(y_test), 1, 10).astype(int)
    y_pred_class = np.clip(np.round(predictions), 1, 10).astype(int)

    cm = confusion_matrix(y_true_class, y_pred_class, labels=range(1, 11))
    if plt is not None:
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=range(1, 11))
        disp.plot(cmap=plt.cm.Blues, values_format='d')
        plt.title("Matriz de Confusão Multiclasse - XGBoost")
        plt.xlabel("Previsto")
        plt.ylabel("Real")
        plt.grid(False)
        plt.show()

    return model, metadata













# 📝 15. Função de Geração de Relatório com ChatGPT
def generate_interpretable_report(score, metadata):
    """Gera relatório orientado a investidores, com fallback local robusto."""
    score = float(max(0.0, min(10.0, score)))
    financial = metadata.get("financial", {}) if isinstance(metadata, dict) else {}
    revenue = float(financial.get("revenue", 0) or 0)
    growth_rate = float(financial.get("growth_rate", 0) or 0)
    profit_margin = float(financial.get("profit_margin", 0) or 0)
    text_meta = metadata.get("text", {}) if isinstance(metadata, dict) else {}
    readability = float(text_meta.get("readability", 50) or 50)
    sentiment_score = float(text_meta.get("sentiment_score", 0.5) or 0.5)
    startup_name = str((metadata or {}).get("startup_name", "") or "").strip() if isinstance(metadata, dict) else ""
    industry = str((metadata or {}).get("industry", "") or "").strip() if isinstance(metadata, dict) else ""
    uniqueness_raw = (
        f"{startup_name}|{industry}|{score:.3f}|{revenue:.2f}|{growth_rate:.2f}|{profit_margin:.2f}|"
        f"{text_meta.get('word_count', 0)}|{text_meta.get('dominant_topic', '')}"
    )
    uniqueness_key = hashlib.sha256(uniqueness_raw.encode("utf-8")).hexdigest()[:10]
    startup_label = startup_name or "startup avaliada"

    clarity = max(0.0, min(10.0, (readability / 10.0)))
    proposta_valor = max(0.0, min(10.0, score * 0.95 + sentiment_score))
    inovacao = max(0.0, min(10.0, score * 0.9 + 0.8))
    viabilidade = max(0.0, min(10.0, (growth_rate / 20.0) + (profit_margin / 18.0) + 2.5))
    escalabilidade = max(0.0, min(10.0, (growth_rate / 16.0) + 2.8))
    mercado_alvo = max(0.0, min(10.0, score * 0.8 + 1.5))
    equipe_fundadora = max(0.0, min(10.0, score * 0.75 + 1.8))
    sustentabilidade = max(0.0, min(10.0, (profit_margin / 15.0) + 3.2))

    category_scores = {
        "clareza_da_ideia": round(clarity, 1),
        "proposta_de_valor": round(proposta_valor, 1),
        "inovacao": round(inovacao, 1),
        "viabilidade_tecnica_financeira": round(viabilidade, 1),
        "escalabilidade": round(escalabilidade, 1),
        "mercado_alvo": round(mercado_alvo, 1),
        "equipe_fundadora": round(equipe_fundadora, 1),
        "sustentabilidade": round(sustentabilidade, 1),
    }

    maturity = "Inicial"
    if score >= 7.5:
        maturity = "Pronta para escala"
    elif score >= 5.0:
        maturity = "Em validação comercial"

    base_strengths = [
        f"Score preditivo de sucesso em {score:.1f}/10.",
        f"Crescimento reportado de {growth_rate:.1f}% com margem de {profit_margin:.1f}%.",
        f"Clareza do pitch estimada em {category_scores['clareza_da_ideia']:.1f}/10.",
        "Estrutura de pitch com dados financeiros objetivos.",
    ]
    base_weaknesses = [
        "Necessidade de ampliar previsibilidade de receita recorrente.",
        "Risco de execução em expansão sem governança operacional robusta.",
        "Dependência de melhoria contínua do storytelling para captação.",
    ]
    base_recommendations = [
        "Apresentar roadmap de 12 meses com marcos trimestrais e KPIs de tração.",
        "Demonstrar unit economics com CAC, LTV e payback por canal de aquisição.",
        "Priorizar investimento em receita previsível e retenção de clientes estratégicos.",
        "Reforçar o pitch com provas de mercado (pilotos, LOIs e cases de clientes).",
    ]

    narrative_angles = [
        f"Abordagem orientada a expansão comercial para {startup_label}.",
        f"Abordagem focada em eficiência operacional e retenção para {startup_label}.",
        f"Abordagem centrada em diferenciação competitiva para {startup_label}.",
    ]
    angle = narrative_angles[int(uniqueness_key, 16) % len(narrative_angles)]
    base_recommendations.insert(
        0,
        f"Assinatura narrativa única ({uniqueness_key}): {angle}",
    )

    investment_thesis = (
        "Startup com sinais claros de escalabilidade e capacidade de geração de valor."
        if score >= 7.5
        else "Startup com potencial relevante, recomendada para rodada com metas condicionadas."
        if score >= 5
        else "Startup em estágio inicial, indicada para investimento de risco controlado."
    )
    suggested_ticket = (
        "Rodada growth/seed+ com participação estratégica"
        if score >= 7.5
        else "Rodada seed com cláusulas de performance e governança"
        if score >= 5
        else "Pré-seed com foco em validação de produto e mercado"
    )

    return {
        "status": "local_report",
        "summary": (
            f"Classificação: {maturity}. Para {startup_label}, o modelo indica score {score:.1f}/10, "
            f"com crescimento de {growth_rate:.1f}% e margem de {profit_margin:.1f}%. "
            f"Ângulo estratégico: {angle}"
        ),
        "final_score": round(score, 1),
        "narrative_uniqueness_key": uniqueness_key,
        "category_scores": category_scores,
        "strengths": base_strengths,
        "weaknesses": base_weaknesses,
        "recommendations": base_recommendations,
        "investor_pitch": {
            "investment_thesis": investment_thesis,
            "funding_readiness": maturity,
            "suggested_ticket": suggested_ticket,
            "capital_use_plan": [
                "Acelerar aquisição de clientes com foco em canais de maior ROI.",
                "Fortalecer produto para elevar retenção e expansão de receita.",
                "Estruturar governança e eficiência operacional para escala.",
            ],
            "risk_mitigation": [
                "Definir metas de unit economics com monitoramento mensal.",
                "Estabelecer ritos de governança e prestação de contas aos investidores.",
                "Validar hipóteses comerciais com experimentos controlados.",
            ],
            "investor_fit": [
                "Fundos seed/growth com atuação ativa em GTM.",
                "Investidores com experiência em SaaS/fintech B2B.",
            ],
        },
    }







# 📈 14. Função de Visualização
def plot_feature_importance(model, feature_names):
    """Visualiza a importância das features"""
    ensure_plot_imports()
    if plt is None:
        logging.warning("Matplotlib indisponível no runtime para plotagem.")
        return
    if hasattr(model.named_steps['regressor'], 'feature_importances_'):
        importances = model.named_steps['regressor'].feature_importances_
        indices = np.argsort(importances)[::-1]

        plt.figure(figsize=(10, 6))
        plt.title("Importância das Features")
        plt.bar(range(len(importances)), importances[indices], align="center")
        plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=90)
        plt.tight_layout()
        plt.show()
    else:
        logging.warning("O modelo não suporta visualização de importância de features")