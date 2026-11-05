# fontmask

Patch a font with the secret-masking rules from [Obel Mono Masked](https://typographic.systems/obel-mono/).

`fontmask` copies the `ccmp` rule set from the bundled Obel font, maps its
glyphs to the target through Unicode, adds note glyphs that copy the target's
own outlines, and adds the mask dots. The output family is `<Family> Masked`.

The mask is visual only. Copy and paste still returns the real text.

## Install

With Nix:

```sh
nix develop
uv sync --extra test
```

From PyPI:

```sh
uvx fontmask inspect Font.ttf
uvx --from 'fontmask==0.1.0' fontmask inspect Font.ttf
```

From a git tag:

```sh
uvx git+https://github.com/mattrobenolt/fontmask@v0.1.0 inspect Font.ttf
uvx git+https://github.com/mattrobenolt/fontmask@v0.1.0 patch Font.ttf -o FontMasked.ttf
```

The PyPI commands use the latest release. The git commands pin the `v0.1.0` tag.

## Use

```sh
fontmask inspect Font.ttf
fontmask patch Font.ttf -o FontMasked.ttf
fontmask patch Variable.ttf --instance wght=400 -o VariableMasked.ttf
```

`patch --dry-run` prints the plan and writes no file.

## Turn it on

Install the output font and select `<Family> Masked` in the app. The masking is
always on; there is no separate switch.

| App | Setting |
| --- | --- |
| Terminal.app | Settings → Profiles → Text → Font → Change → `<Family> Masked` |
| iTerm2 | Settings → Profiles → Text → Font → `<Family> Masked`, then enable **Use ligatures** |
| VS Code | `"editor.fontFamily": "<Family> Masked"` and `"editor.fontLigatures": true` |
| Zed | `"buffer_font_family": "<Family> Masked"` |
| Ghostty | `font-family = "<Family> Masked"` |
| Kitty | `font_family <Family> Masked` |
| WezTerm | `font = wezterm.font("<Family> Masked")` |
| Windows Terminal | Settings → Profiles → Appearance → Font face → `<Family> Masked` |

Zed shapes each syntax-highlighted span separately. Rules that need context from
a previous span may not mask. Use the terminal or set the file to plain text
when you need the full line masked.


Apps that do not shape text, like Alacritty, show the plain string.

## Supported fonts

TrueType, CFF, WOFF/WOFF2, static and variable fonts, proportional fonts, fonts
with no GSUB, and TTC collections. CFF2 variable output is not supported.
Variable fonts are instanced to a static font. Proportional fonts get one mask
glyph per advance width, so the line width does not change.

## How it works

Obel Mono keeps the rules in `ccmp`. `fontmask` copies the 108-lookup closure,
maps its glyph names to the target, adds the note and mask glyphs, and appends
the lookups to the target's GSUB table. `tests/test_patch.py` shapes 520
strings in both fonts and compares the output.

## Limits

- The mask changes pixels only. It does not change the text buffer.
- Mask glyphs are unencoded. The tool does not add cmap entries.
- Color fonts are not supported. Mask glyphs render as monochrome outlines.
- Check the target font's license before distributing the patched font.

## Development

`nix develop`, then `uv sync --extra test`, `uv check`, and `uv run pytest -q`.

## Credit

The rules and the mask dot are from [Obel Mono](https://typographic.systems/obel-mono/)
by Cody Collier and the Obel Mono Project Authors. Read the original post,
[A typeface that keeps a secret](https://typographic.systems/journal/a-typeface-that-keeps-a-secret).

## License

The tool is MIT. The bundled rules font is SIL OFL 1.1; see
`src/fontmask/data/OFL.txt`. The patched font is a derivative of the target and
the Obel material. Check the target's license before distribution.
