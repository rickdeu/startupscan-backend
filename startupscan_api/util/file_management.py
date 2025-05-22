from contextlib import contextmanager
import os
import tempfile

@contextmanager
def TempFileManager(audio_file=None, video_file=None):
    """Gerenciador de contexto para arquivos temporários"""
    audio_path = None
    video_path = None
    
    try:
        # Processar áudio
        if audio_file:
            _, audio_path = tempfile.mkstemp(suffix='.mp3')
            with open(audio_path, 'wb+') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
        
        # Processar vídeo
        if video_file:
            _, video_path = tempfile.mkstemp(suffix='.mp4')
            with open(video_path, 'wb+') as f:
                for chunk in video_file.chunks():
                    f.write(chunk)
        
        yield (audio_path, video_path)
        
    finally:
        # Limpeza garantida
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
