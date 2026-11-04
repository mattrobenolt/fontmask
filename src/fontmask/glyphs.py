"""Add glyphs to TrueType and CFF fonts."""

from __future__ import annotations

import copy
from collections import Counter

from fontTools.misc.transform import Transform
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import Glyph


class Backend:
    def __init__(self, font):
        self.font = font
        self.order = list(font.getGlyphOrder())
        self.glyph_set = set(self.order)
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm
        widths = [width for width, _ in self.hmtx.metrics.values() if width > 0]
        self.default_width = Counter(widths).most_common(1)[0][0] if widths else self.upm // 2
        font.setGlyphOrder(self.order)

    def unique_name(self, base: str) -> str:
        if base not in self.glyph_set:
            return base
        index = 1
        while f"{base}.fm{index}" in self.glyph_set:
            index += 1
        return f"{base}.fm{index}"

    def _add_order(self, name: str) -> None:
        if name not in self.glyph_set:
            self.order.append(name)
            self.glyph_set.add(name)

    def width(self, name: str) -> int:
        return self.hmtx[name][0]

    def add_copy(self, name: str, base: str) -> None:
        raise NotImplementedError

    def add_empty(self, name: str, width: int = 0) -> None:
        raise NotImplementedError

    def add_dot(self, name: str, width: int, rules) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        self.font.setGlyphOrder(self.order)
        self.font["maxp"].numGlyphs = len(self.order)


class TTFBackend(Backend):
    def __init__(self, font):
        super().__init__(font)
        self.glyf = font["glyf"]
        self.glyf.glyphOrder = self.order

    def add_copy(self, name: str, base: str) -> None:
        if base not in self.glyf:
            self.add_empty(name, self.default_width)
            return
        self.glyf[name] = copy.deepcopy(self.glyf[base])
        self.hmtx[name] = self.hmtx[base]
        self.glyph_set.add(name)

    def add_empty(self, name: str, width: int = 0) -> None:
        glyph = Glyph()
        glyph.numberOfContours = 0
        glyph.recalcBounds(self.glyf)
        self.glyf[name] = glyph
        self.hmtx[name] = (width, 0)
        self.glyph_set.add(name)

    def add_dot(self, name: str, width: int, rules) -> None:
        width = width or self.default_width
        scale = self.upm / rules.upm
        xmin, ymin, xmax, ymax = rules.dot_bounds
        natural_width = (xmax - xmin) * scale
        if natural_width > width * 0.9:
            scale *= (width * 0.9) / natural_width
        center_x = (xmin + xmax) / 2
        center_y = (ymin + ymax) / 2
        natural_scale = self.upm / rules.upm
        dx = width / 2 - center_x * scale
        dy = center_y * natural_scale - center_y * scale
        pen = TTGlyphPen(None)
        rules.dot_recording.replay(TransformPen(pen, Transform(scale, 0, 0, scale, dx, dy)))
        glyph = pen.glyph()
        glyph.recalcBounds(self.glyf)
        self.glyf[name] = glyph
        self.hmtx[name] = (width, glyph.xMin)
        self.glyph_set.add(name)

    def finish(self) -> None:
        self.font.setGlyphOrder(self.glyf.glyphOrder)
        self.font["maxp"].numGlyphs = len(self.glyf.glyphOrder)


class CFFBackend(Backend):
    def __init__(self, font):
        super().__init__(font)
        self.cff = font["CFF "].cff
        self.top = self.cff.topDictIndex[0]
        self.charstrings = self.top.CharStrings
        self.glyphset = font.getGlyphSet()
        self.reference = self.charstrings[".notdef"]

    def _add_charstring(self, name: str, charstring) -> None:
        charstring.private = self.reference.private
        charstring.globalSubrs = self.reference.globalSubrs
        if self.charstrings.charStringsAreIndexed:
            self.charstrings.charStrings[name] = len(self.charstrings.charStringsIndex)
            self.charstrings.charStringsIndex.append(charstring)
        else:
            self.charstrings.charStrings[name] = charstring
        if self.top.charset is not None:
            self.top.charset.append(name)
        self._add_order(name)

    def add_copy(self, name: str, base: str) -> None:
        if base not in self.glyphset:
            self.add_empty(name, self.default_width)
            return
        width = self.hmtx[base][0]
        pen = T2CharStringPen(width, self.glyphset)
        self.glyphset[base].draw(pen)
        self._add_charstring(name, pen.getCharString())
        self.hmtx[name] = self.hmtx[base]

    def add_empty(self, name: str, width: int = 0) -> None:
        pen = T2CharStringPen(width, None)
        self._add_charstring(name, pen.getCharString())
        self.hmtx[name] = (width, 0)

    def add_dot(self, name: str, width: int, rules) -> None:
        width = width or self.default_width
        scale = self.upm / rules.upm
        xmin, ymin, xmax, ymax = rules.dot_bounds
        natural_width = (xmax - xmin) * scale
        if natural_width > width * 0.9:
            scale *= (width * 0.9) / natural_width
        center_x = (xmin + xmax) / 2
        center_y = (ymin + ymax) / 2
        natural_scale = self.upm / rules.upm
        dx = width / 2 - center_x * scale
        dy = center_y * natural_scale - center_y * scale
        pen = T2CharStringPen(width, None)
        rules.dot_recording.replay(TransformPen(pen, Transform(scale, 0, 0, scale, dx, dy)))
        self._add_charstring(name, pen.getCharString())
        left = xmin * scale + dx
        self.hmtx[name] = (width, round(left))


def make_backend(font) -> Backend:
    if "CFF " in font:
        return CFFBackend(font)
    if "CFF2" in font:
        raise NotImplementedError("CFF2 variable fonts are not supported yet; instance the font first")
    if "glyf" in font:
        return TTFBackend(font)
    raise ValueError("font has neither glyf nor CFF outlines")
