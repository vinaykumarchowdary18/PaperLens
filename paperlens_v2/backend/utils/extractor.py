import pdfplumber
import docx
import io
from fastapi import UploadFile, HTTPException

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def extract_text(file: UploadFile) -> tuple[str, int]:
    """
    Extract plain text from an uploaded PDF, DOCX, or TXT file.
    Returns (text, word_count).
    """
    content_type = file.content_type or ""
    file_ext = (file.filename or "").rsplit(".", 1)[-1].lower()

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 10 MB.")

    text = ""

    # --- PDF ---
    if content_type == "application/pdf" or file_ext == "pdf":
        try:
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")

    # --- DOCX ---
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_ext == "docx":
        try:
            doc = docx.Document(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not read DOCX: {e}")

    # --- Plain text ---
    elif content_type == "text/plain" or file_ext == "txt":
        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not read text file: {e}")

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT file.",
        )

    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract any text from the file.")

    word_count = len(text.split())
    if word_count < 50:
        raise HTTPException(
            status_code=422,
            detail="File has too little text (under 50 words). Please upload a proper document.",
        )

    return text, word_count
