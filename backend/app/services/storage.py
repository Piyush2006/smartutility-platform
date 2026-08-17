"""
Local-filesystem storage abstraction (CLAUDE.md: "Local filesystem in
development; storage abstraction so S3-compatible storage can be added
later"). Every caller goes through save_upload() so extension + MIME +
size validation happens in exactly one place (never trust the client's
extension alone).
"""
import mimetypes
import os
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@dataclass
class StoredFile:
    path: str
    url: str


def _ensure_dir(sub_dir: str) -> str:
    full_dir = os.path.join(settings.UPLOAD_DIR, sub_dir)
    os.makedirs(full_dir, exist_ok=True)
    return full_dir


def save_upload(file: UploadFile, *, sub_dir: str, allowed_extensions: set[str], max_mb: int) -> StoredFile:
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Never trust the client-provided content_type either -- cross-check
    # against the extension's expected MIME family.
    expected_mime = _MIME_BY_EXT.get(ext)
    guessed_mime, _ = mimetypes.guess_type(filename)
    content_type = file.content_type or guessed_mime
    if expected_mime and content_type and not content_type.startswith(expected_mime.split("/")[0]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content does not match its extension.")

    contents = file.file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > max_mb:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large. Max {max_mb}MB.")

    directory = _ensure_dir(sub_dir)
    stored_name = f"{uuid.uuid4()}{ext}"
    full_path = os.path.join(directory, stored_name)
    with open(full_path, "wb") as out:
        out.write(contents)

    return StoredFile(path=full_path, url=f"/uploads/{sub_dir}/{stored_name}")
