from pathlib import Path

import uharfbuzz as hb


def shape(path, text):
    blob = hb.Blob.from_file_path(str(path))
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)
    return (
        [font.get_glyph_name(info.codepoint) for info in buf.glyph_infos],
        [pos.x_advance for pos in buf.glyph_positions],
    )


def is_mask(name):
    return name.startswith("secret.mask")
