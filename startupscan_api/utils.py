from .commom_imports import *


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
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio_data = r.record(source)
                transcription = r.recognize_google(audio_data, language='pt-BR')
                audio_features['transcription'] = transcription
        except:
            pass

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
        'sentiment_score': 0,
        'dominant_topic': "general",
        'topic_score': 0,
        'readability': 0
    }

    if not text or not isinstance(text, str):
        return text_features

    try:
        # Análise de sentimento
        sentiment_analyzer = pipeline("text-classification",
                                   model="finiteautomata/bertweet-base-sentiment-analysis")
        sentiment_result = sentiment_analyzer(text[:512])[0]  # Limitar tamanho para o modelo

        # Análise de tópicos
        topic_analyzer = pipeline("zero-shot-classification",
                                model="facebook/bart-large-mnli")
        topics = topic_analyzer(text[:512],  # Limitar tamanho
                              candidate_labels=["technology", "finance", "marketing", "product", "team"])

        # Métricas de legibilidade
        readability = textstat.flesch_reading_ease(text)

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
    """Gera um relatório detalhado e interpretável com recomendações do ChatGPT"""
    print("\n📊 Relatório Detalhado:")
    print(f"Pontuação Geral Prevista: {score:.2f}/10")

    # Seção de Texto
    print("\n🔍 Análise de Texto:")
    print(f"- Sentimento: {metadata['text']['sentiment']} (confiança: {metadata['text']['sentiment_score']:.2f})")
    print(f"- Tópico Dominante: {metadata['text']['dominant_topic']} (score: {metadata['text']['topic_score']:.2f})")
    print(f"- Legibilidade: {metadata['text']['readability']:.1f} (escala 0-100)")

    # Seção de Áudio
    print("\n🎧 Análise de Áudio:")
    print(f"- Taxa de Fala: {metadata['audio']['speech_rate']:.1f} palavras/min")
    print(f"- Variação de Tom: {metadata['audio']['pitch_variation']:.2f}")
    if 'transcription' in metadata['audio']:
        print("\n📝 Transcrição (resumo):")
        print(metadata['audio']['transcription'][:200] + "...")

    # Seção de Vídeo
    print("\n🎬 Análise de Vídeo:")
    print(f"- Emoção Dominante: {metadata['video']['dominant_emotion']}")
    print(f"- Confiança na Detecção: {metadata['video']['emotion_confidence']:.2f}")

    # Seção Financeira
    print("\n💰 Análise Financeira:")
    financial = metadata.get('financial', {})
    if 'revenue' in financial:
        print(f"- Receita: ${financial['revenue']:,.2f}")
    if 'growth_rate' in financial:
        print(f"- Taxa de Crescimento: {financial['growth_rate']}%")
    if 'profit_margin' in financial:
        print(f"- Margem de Lucro: {financial['profit_margin']}%")

    # Recomendações via ChatGPT
    print("\n💡 Recomendações Personalizadas pelo ChatGPT:")

    try:
        import openai

        # Construir o contexto para o ChatGPT
        context = f"""
        Como especialista em análise de pitches de startups, forneça recomendações concisas e acionáveis baseadas nos seguintes dados:

        Pontuação Geral: {score:.2f}/10
        Análise de Texto:
        - Sentimento: {metadata['text']['sentiment']}
        - Tópico Dominante: {metadata['text']['dominant_topic']}
        - Legibilidade: {metadata['text']['readability']}/100

        Análise de Áudio:
        - Taxa de Fala: {metadata['audio']['speech_rate']} palavras/min
        - Variação de Tom: {metadata['audio']['pitch_variation']}

        Análise de Vídeo:
        - Emoção Dominante: {metadata['video']['dominant_emotion']}
        - Confiança: {metadata['video']['emotion_confidence']:.2f}

        Dados Financeiros:
        - Receita: ${financial.get('revenue', 'N/A')}
        - Crescimento: {financial.get('growth_rate', 'N/A')}%
        - Margem: {financial.get('profit_margin', 'N/A')}%

        Por favor, forneça:
        1. 5 pontos fortes identificados
        2. 5 áreas prioritárias para melhoria
        3. 2 sugestões específicas para cada área
        4. 2 estratégia de apresentação recomendada
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um consultor especializado em análise e melhoria de pitches para startups."},
                {"role": "user", "content": context}
            ],
            temperature=0.7,
            max_tokens=500
        )

        recommendations = response.choices[0].message['content'].strip()
        print(recommendations)
        return recommendations

    except Exception as e:
        #logging.error(f"Erro ao consultar ChatGPT: {str(e)}")
        print("\n⚠️ Sistema de recomendações avançado indisponível. Recomendações básicas:")
        recommendations = {
        "status": "Sistema de recomendações avançado indisponível.",
        "recommendations": []
            }

        if score < 5:
            print("- Revisar proposta de valor e diferenciação")
            print("- Melhorar clareza da comunicação")
            print("- Reavaliar modelo financeiro")
            recommendations["recommendations"] = [
                "Revisar proposta de valor e diferenciação",
                "Melhorar clareza da comunicação",
                "Reavaliar modelo financeiro"
            ]
        elif score < 7.5:
            print("- Aumentar entusiasmo na apresentação")
            print("- Refinar métricas financeiras")
            print("- Melhorar estrutura do pitch")
            recommendations["recommendations"] = [
                "Aumentar entusiasmo na apresentação",
                "Refinar métricas financeiras",
                "Melhorar estrutura do pitch"
            ]
        else:
            print("- Aprimorar storytelling")
            print("- Adicionar dados de tração adicional")
            print("- Preparar respostas para objeções comuns")
            recommendations["recommendations"] = [
                "Aprimorar storytelling",
                "Adicionar dados de tração adicional",
                "Preparar respostas para objeções comuns"
            ]

        return recommendations







# 📈 14. Função de Visualização
def plot_feature_importance(model, feature_names):
    """Visualiza a importância das features"""
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