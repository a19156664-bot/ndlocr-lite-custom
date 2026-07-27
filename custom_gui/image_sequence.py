import os
from typing import List, Optional

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

def list_images_in_folder(folder: str) -> List[str]:
    """
    Returns full paths of supported images directly inside the given folder,
    sorted alphabetically by filename.
    """
    if not os.path.exists(folder) or not os.path.isdir(folder):
        return []
        
    image_paths = []
    for entry in os.scandir(folder):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                image_paths.append(entry.path)
                
    # Sort by filename
    image_paths.sort(key=lambda path: os.path.basename(path))
    return image_paths


class ImageSequence:
    def __init__(self, paths: List[str]):
        self._paths = list(paths)
        self._index = -1 if not self._paths else 0

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._paths)

    def current(self) -> Optional[str]:
        if self._index == -1 or not self._paths:
            return None
        return self._paths[self._index]

    def has_next(self) -> bool:
        if not self._paths:
            return False
        return self._index < len(self._paths) - 1

    def has_prev(self) -> bool:
        if not self._paths:
            return False
        return self._index > 0

    def next(self) -> Optional[str]:
        if not self._paths:
            return None
        if self.has_next():
            self._index += 1
        return self.current()

    def prev(self) -> Optional[str]:
        if not self._paths:
            return None
        if self.has_prev():
            self._index -= 1
        return self.current()

    def goto(self, i: int) -> Optional[str]:
        if not self._paths:
            return None
        # Clamp to bounds
        if i < 0:
            i = 0
        elif i >= len(self._paths):
            i = len(self._paths) - 1
            
        self._index = i
        return self.current()
