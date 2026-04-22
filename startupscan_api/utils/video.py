import logging
from ..commom_imports import (
    ensure_video_imports, cv2, mp, DeepFace, mp_editor, np, Counter
)
from .audio import process_audio


def process_video(video_path):
    video_features = {
        'dominant_emotion': "neutral",
        'emotion_confidence': 0,
        'frame_count': 0,
    }

    if video_path is None:
        return video_features

    import os
    if not os.path.exists(video_path):
        return video_features

    try:
        ensure_video_imports()
        if cv2 is None or mp is None or mp_editor is None:
            raise RuntimeError("libs base de vídeo indisponíveis")

        temp_audio_path = "temp_audio.wav"
        clip = mp_editor.VideoFileClip(video_path)
        clip.audio.write_audiofile(temp_audio_path)

        audio_features = process_audio(temp_audio_path)

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

            if frame_count % 5 == 0:
                try:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_detection.process(rgb_frame)

                    if results.detections:
                        if DeepFace is not None:
                            result = DeepFace.analyze(
                                rgb_frame, actions=['emotion'], enforce_detection=False
                            )
                            emotions.append(result[0]['dominant_emotion'])
                            confidence_scores.append(result[0]['face_confidence'])
                except Exception as e:
                    logging.error(f"Erro no frame {frame_count}: {str(e)}")

            frame_count += 1

        cap.release()

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
            'audio_features': audio_features,
        })

    except Exception as e:
        logging.error(f"Erro no processamento de vídeo: {str(e)}")

    return video_features
