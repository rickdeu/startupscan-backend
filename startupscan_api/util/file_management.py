from contextlib import contextmanager
import os
import tempfile

@contextmanager
def TempFileManager(audio_file=None, video_file=None):
    """Context manager for temporary files"""
    audio_path = None
    video_path = None

    try:
        # Process audio
        if audio_file:
            audio_suffix = os.path.splitext(getattr(audio_file, "name", ""))[1] or ".mp3"
            _, audio_path = tempfile.mkstemp(suffix=audio_suffix)
            with open(audio_path, 'wb+') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
        
        # Process video
        if video_file:
            video_suffix = os.path.splitext(getattr(video_file, "name", ""))[1] or ".mp4"
            _, video_path = tempfile.mkstemp(suffix=video_suffix)
            with open(video_path, 'wb+') as f:
                for chunk in video_file.chunks():
                    f.write(chunk)
        
        yield (audio_path, video_path)
        
    finally:
        # Guaranteed cleanup
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
