"""Small shared helpers."""
from __future__ import annotations

import re

_SUFFIXES = r"\b(ltd|limited|inc|plc|llc|co|company|corporation|corp|group|holdings|sa|ag|nv|gmbh|pte|pvt|private|the)\b"


def normalize_name(name: str) -> str:
    """Canonical key for de-duplicating buyer entities across sources."""
    s = (name or "").lower()
    s = re.sub(_SUFFIXES, " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s.strip()
