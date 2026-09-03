import io

from docx import Document
from pypdf import PdfReader


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    Extract text from .txt/.md/.pdf/.docx uploads.
    """
    if not uploaded_file:
        return ""

    name = (uploaded_file.name or "").lower()
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    if not raw_bytes:
        return ""

    if name.endswith((".txt", ".md", ".csv")):
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return raw_bytes.decode(encoding, errors="ignore")
            except Exception:
                continue
        return ""

    if name.endswith(".pdf"):
        text_parts = []
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        except Exception:
            return ""
        return "\n".join(text_parts).strip()

    if name.endswith(".docx"):
        try:
            doc = Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        except Exception:
            return ""

    # For unsupported formats, attempt a text fallback.
    try:
        return raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def merge_pitch_text(user_text: str, extracted_text: str, youtube_link: str) -> str:
    final_text = (user_text or "").strip()
    extracted_text = (extracted_text or "").strip()
    youtube_link = (youtube_link or "").strip()

    if extracted_text:
        if final_text:
            final_text += "\n\n[Conteúdo adicional anexado]\n" + extracted_text
        else:
            final_text = extracted_text

    if youtube_link:
        final_text += f"\n\n[Referência de vídeo do pitch]: {youtube_link}"

    return final_text.strip()
