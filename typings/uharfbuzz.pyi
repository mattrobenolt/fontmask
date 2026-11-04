from typing import Any

class Blob:
    @classmethod
    def from_file_path(cls, path: str) -> Blob: ...

class Face:
    def __init__(self, blob: Blob) -> None: ...

class Font:
    def __init__(self, face: Face) -> None: ...
    def get_glyph_name(self, glyph_id: int) -> str: ...

class GlyphInfo:
    codepoint: int

class GlyphPosition:
    x_advance: int

class Buffer:
    glyph_infos: list[GlyphInfo]
    glyph_positions: list[GlyphPosition]
    def __init__(self) -> None: ...
    def add_str(self, text: str) -> None: ...
    def guess_segment_properties(self) -> None: ...

def shape(font: Font, buf: Buffer, features: Any = ...) -> None: ...
