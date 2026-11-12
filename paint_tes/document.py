from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from PIL import Image


@dataclass
class Document:
    image: Image.Image
    title: str = "Nowy obraz"
    path: Path | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    mask: Image.Image | None = None
    revision: int = 0
    saved_revision: int = -1
    history: list = field(default_factory=list)
    redo_history: list = field(default_factory=list)
    limit: int = 20
    metadata: dict = field(default_factory=dict)

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    def apply(self, image: Image.Image):
        self.history.append((self.image.copy(), self.revision))
        self.redo_history.clear()
        self.image = image.convert("RGBA").copy()
        self.revision = max(self.revision, self.saved_revision, *(r for _, r in self.history)) + 1
        # Snapshot history is bounded both by count and approximate memory.
        budget = 0
        kept = []
        for snapshot in reversed(self.history):
            budget += snapshot[0].width * snapshot[0].height * 4
            if len(kept) >= self.limit or budget > 256 * 1024**2:
                break
            kept.append(snapshot)
        self.history = list(reversed(kept))
        if self.mask is not None and self.mask.size != self.image.size:
            self.mask = None

    def undo(self):
        if self.history:
            self.redo_history.append((self.image, self.revision))
            self.image, self.revision = self.history.pop()
            if self.mask is not None and self.mask.size != self.image.size:
                self.mask = None

    def redo(self):
        if self.redo_history:
            self.history.append((self.image, self.revision))
            self.image, self.revision = self.redo_history.pop()
            if self.mask is not None and self.mask.size != self.image.size:
                self.mask = None
