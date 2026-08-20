from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IStorageAdapter(ABC):
    """
    Abstract Storage Adapter interface for Storage Service.

    Implementations:
    - LocalStorageAdapter
    - CloudinaryStorageAdapter
    """

    @abstractmethod
    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        thumbnail_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Save original image and optional thumbnail.

        :param file_bytes: Original image binary bytes
        :param filename: Original filename
        :param content_type: MIME type
        :param thumbnail_bytes: Thumbnail binary bytes
        :return: Storage metadata containing URLs and optional provider metadata
        """
        raise NotImplementedError
