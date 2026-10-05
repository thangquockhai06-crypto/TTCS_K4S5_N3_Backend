"""Avatar validation, image processing, and local storage."""

from __future__ import annotations

import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings


MAX_AVATAR_BYTES = 2 * 1024 * 1024
SUPPORTED_CONTENT_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG"}
JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SAFE_FILENAME = re.compile(r"^[0-9a-f]{32}(?:_thumb)?\.(?:jpg|png)$")
STATUS_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
STATUS_INVALID_IMAGE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class AvatarStorage:
    """Stores processed avatars below the configured local media directory."""

    def __init__(self) -> None:
        self.media_root = Path(settings.AVATAR_STORAGE_DIR).resolve()
        self.avatar_root = self.media_root / "avatars"
        self.avatar_root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, content_type: str) -> Tuple[str, str]:
        square, image_format = _process_image(content, content_type)
        extension = "png" if image_format == "PNG" else "jpg"
        file_id = uuid.uuid4().hex
        avatar_name = f"{file_id}.{extension}"
        thumbnail_name = f"{file_id}_thumb.{extension}"
        avatar_path = self.avatar_root / avatar_name
        thumbnail_path = self.avatar_root / thumbnail_name

        try:
            avatar_bytes = _encode_image(square, image_format)
            thumbnail = square.resize(
                (settings.AVATAR_THUMBNAIL_SIZE, settings.AVATAR_THUMBNAIL_SIZE),
                Image.Resampling.LANCZOS,
            )
            thumbnail_bytes = _encode_image(thumbnail, image_format)
            avatar_path.write_bytes(avatar_bytes)
            thumbnail_path.write_bytes(thumbnail_bytes)
        except Exception:
            self._delete_file(avatar_name)
            self._delete_file(thumbnail_name)
            raise
        finally:
            square.close()

        base_url = settings.MEDIA_URL.rstrip("/")
        return (
            f"{base_url}/avatars/{avatar_name}",
            f"{base_url}/avatars/{thumbnail_name}",
        )

    def delete_url(self, url: Optional[str]) -> None:
        """Delete only files belonging to this storage, never arbitrary paths."""
        if not url:
            return
        parsed_path = urlparse(url).path
        prefix = f"{settings.MEDIA_URL.rstrip('/')}/avatars/"
        if not parsed_path.startswith(prefix):
            return
        filename = parsed_path[len(prefix) :]
        if not _SAFE_FILENAME.fullmatch(filename):
            return
        self._delete_file(filename)

    def delete_urls(self, avatar_url: Optional[str], thumbnail_url: Optional[str]) -> None:
        self.delete_url(avatar_url)
        self.delete_url(thumbnail_url)

    def _delete_file(self, filename: str) -> None:
        path = (self.avatar_root / filename).resolve()
        try:
            path.relative_to(self.avatar_root)
        except ValueError:
            return
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _process_image(content: bytes, content_type: str) -> Tuple[Image.Image, str]:
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=STATUS_TOO_LARGE,
            detail="Avatar không được vượt quá 2 MB.",
        )

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    expected_format = SUPPORTED_CONTENT_TYPES.get(normalized_type)
    if expected_format is None:
        raise HTTPException(
            status_code=STATUS_INVALID_IMAGE,
            detail="Chỉ chấp nhận tệp JPG/JPEG hoặc PNG.",
        )

    if expected_format == "JPEG" and not content.startswith(JPEG_SIGNATURE):
        _raise_invalid_image()
    if expected_format == "PNG" and not content.startswith(PNG_SIGNATURE):
        _raise_invalid_image()

    try:
        with Image.open(BytesIO(content)) as source:
            if source.format != expected_format:
                _raise_invalid_image()
            oriented = ImageOps.exif_transpose(source)
            oriented.load()
            width, height = oriented.size
            if width <= 0 or height <= 0:
                _raise_invalid_image()
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            square = oriented.crop((left, top, left + side, top + side))
            if expected_format == "JPEG" and square.mode not in ("L", "RGB"):
                square = square.convert("RGB")
            return square, expected_format
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        _raise_invalid_image()
    raise AssertionError("unreachable")


def _encode_image(image: Image.Image, image_format: str) -> bytes:
    output = BytesIO()
    if image_format == "JPEG":
        image.save(output, format="JPEG", quality=90, optimize=True)
    else:
        image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _raise_invalid_image() -> None:
    raise HTTPException(
        status_code=STATUS_INVALID_IMAGE,
        detail="Tệp avatar không phải là ảnh hợp lệ hoặc đã bị hỏng.",
    )
