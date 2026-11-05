# fontmask

Patch an existing font with the secret-masking rules from Obel Mono Masked.

The tool reads the `ccmp` rule set from a bundled Obel Mono Masked font. It
maps the rule glyphs to the target font through Unicode, adds note glyphs that
copy the target's own outlines, adds mask dots, and merges the rules into the
target's GSUB table. The output family is `<Family> Masked` by default.

The mask is visual only. Copy and paste returns the real text. An application
that does not shape text shows the real characters. Alacritty is one example.

## Credit

The masking idea, the compiled `ccmp` rule set, and the mask dot come from
[Obel Mono](https://typographic.systems/obel-mono/) by Cody Collier and the
Obel Mono Project Authors. Read the original write-up:
[A typeface that keeps a secret](https://typographic.systems/journal/a-typeface-that-keeps-a-secret).

This project only transplants their work into other fonts. Thank you.

## Install

The development environment uses Nix and `uv`:

```sh
nix develop
uv sync --extra test
uv run fontmask inspect tests/fonts/Hack-Regular.ttf
```

## Run without installing

`uvx` builds the tool from the repository and runs it:

```sh
uvx git+https://github.com/mattrobenolt/fontmask inspect Font.ttf
uvx git+https://github.com/mattrobenolt/fontmask patch Font.ttf -o FontMasked.ttf
```

## Use

```sh
fontmask inspect Font.ttf
fontmask patch Font.ttf -o FontMasked.ttf
```

Examples:

```sh
fontmask patch tests/fonts/Hack-Regular.ttf -o HackMasked.ttf
fontmask patch RobotoMono\[wght\].ttf --instance wght=400 -o RobotoMonoMasked.ttf
fontmask patch Variable.ttf --instance Bold -o VariableBoldMasked.ttf
```

Select the new family in the terminal or editor font menu. On macOS, install
the output file with Font Book or copy it to `~/Library/Fonts`.

`patch --dry-run` prints the plan and writes no file.

## Supported fonts

- TrueType (`glyf`) and CFF (`OTF`) outlines.
- WOFF and WOFF2 input and output. HarfBuzz builds without WOFF2 support cannot
  shape the output directly; convert it to TTF for testing.
- Static fonts and variable fonts. A variable font is instanced to a static
  font at the default axes or at the axes from `--instance`.
- Proportional fonts. The tool creates one mask glyph per advance width, so the
  line width does not change.
- Fonts with no GSUB table. The tool creates the table.
- Fonts with an existing `ccmp` feature. The tool appends the mask lookups to
  the existing feature.
- TTC collections with `--font-number`.

CFF2 variable output is not supported yet. Instance the font first.

## How it works

1. `fontmask.rules` extracts the `ccmp` closure from Obel Mono Masked. The
   closure has 108 lookups, 19 mask classes, and 700 referenced glyph names.
2. The patcher maps each source glyph name to the target glyph with the same
   Unicode codepoint.
3. Note glyphs copy the target's visible base glyph. The mask dot comes from
   Obel and is scaled to the target's units per em.
4. The patcher groups mask glyphs by the source advance width. A source glyph
   maps to the dot with its own width. This preserves monospaced cells and
   proportional line widths.
5. The copied lookups are renamed, remapped, sorted, and appended to the
   target's GSUB table under `ccmp`.
6. The name table gets the new family name and an OFL notice.

`tests/test_patch.py` shapes 520 strings with HarfBuzz in both fonts and
compares the output. The suite also covers proportional fonts, CFF, variable
fonts, WOFF2, and fonts without GSUB.

## Limits

- The mask changes pixels only. It does not change the text buffer.
- The tool does not add cmap entries. Mask glyphs are unencoded.
- Color fonts are not supported. Mask glyphs render as monochrome outlines.
- The font must contain the characters to mask. The tool adds empty
  placeholders for missing encoded glyphs and reports them.
- The bundled rules are OFL 1.1. The patched font is a derivative work. Check
  the target font's license before distribution.

## Development

```sh
nix develop
uv sync --extra test
uv check
uv run pytest -q
```

The flake provides `uv`, HarfBuzz, and test fonts from DejaVu, Source Code
Pro, and Roboto Mono. `uv sync --extra test` installs fontTools, uharfbuzz,
and pytest into `.venv`.

## License

The tool code is MIT licensed. The bundled Obel Mono Masked rules font is
licensed under the SIL Open Font License 1.1. See
`src/fontmask/data/OFL.txt`.
