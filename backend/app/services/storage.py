"""Private file storage abstraction for uploaded resumes."""

import os
import uuid
from typing import Tuple
from app.core.config import get_settings

settings = get_settings()


class StorageService:
    """Manages secure file persistence outside the public web root."""

    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = os.path.abspath(upload_dir)
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(self, content: bytes, extension: str) -> Tuple[str, str]:
        """Save raw bytes to a private location using an opaque random UUID filename."""
        file_key = uuid.uuid4().hex
        clean_ext = extension.lstrip(".").lower()
        filename = f"{file_key}.{clean_ext}"
        file_path = os.path.join(self.upload_dir, filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_key, file_path

    def delete_file(self, file_path: str) -> bool:
        """Remove a file from disk if it exists."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except OSError:
            return False
        return False

    def read_file(self, file_path: str) -> bytes:
        """Read file contents from storage."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File at {file_path} does not exist.")
        with open(file_path, "rb") as f:
            return f.read()


storage_service = StorageService()

