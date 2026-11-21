#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypinyin import Style, pinyin

GLYPH_SIZE = 128
GLYPH_BYTES = GLYPH_SIZE * GLYPH_SIZE // 2

# The compiled pinyin strings use one-byte tokens so the MIPS renderer can
# iterate safely. Uppercase tokens map to precomposed Unicode tone-marked glyphs.
TOKEN_TO_GLYPH = {
    **{chr(ord("A") + i): glyph for i, glyph in enumerate(
        "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
    )},
    "Y": "ü",
}
TOKEN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY"
GLYPH_CHARS = "abcdefghijklmnopqrstuvwxyz" + "".join(TOKEN_TO_GLYPH[token] for token in TOKEN_CHARS[26:])


def tone3_to_marked(syllable: str) -> str:
    """Convert pypinyin TONE3 output (e.g. liu2, nv3) to marked pinyin."""
    match = re.fullmatch(r"([a-zv:]+)([1-5]?)", syllable.lower())
    if not match:
        raise ValueError(f"Unexpected TONE3 syllable: {syllable!r}")

    base, tone_text = match.groups()
    tone = int(tone_text) if tone_text else 5
    base = base.replace("u:", "ü").replace("v", "ü")

    if tone == 5:
        return base

    vowels = "aeiouü"
    if "a" in base:
        index = base.index("a")
    elif "e" in base:
        index = base.index("e")
    elif "ou" in base:
        index = base.index("o")
    else:
        vowel_indices = [i for i, char in enumerate(base) if char in vowels]
        if not vowel_indices:
            return base
        index = vowel_indices[-1]

    tone_glyphs = {
        ("a", 1): "ā", ("a", 2): "á", ("a", 3): "ǎ", ("a", 4): "à",
        ("e", 1): "ē", ("e", 2): "é", ("e", 3): "ě", ("e", 4): "è",
        ("i", 1): "ī", ("i", 2): "í", ("i", 3): "ǐ", ("i", 4): "ì",
        ("o", 1): "ō", ("o", 2): "ó", ("o", 3): "ǒ", ("o", 4): "ò",
        ("u", 1): "ū", ("u", 2): "ú", ("u", 3): "ǔ", ("u", 4): "ù",
        ("ü", 1): "ǖ", ("ü", 2): "ǘ", ("ü", 3): "ǚ", ("ü", 4): "ǜ",
    }
    char = base[index]
    marked = tone_glyphs.get((char, tone))
    if marked is None:
        raise ValueError(f"Cannot place tone {tone} on {base!r}")
    return base[:index] + marked + base[index + 1:]


GLYPH_TO_TOKEN = {glyph: token for token, glyph in TOKEN_TO_GLYPH.items()}


def encode_syllable(marked: str) -> str:
    """Encode accented Unicode vowels as single-byte atlas tokens."""
    output = []
    for char in marked:
        if char in GLYPH_TO_TOKEN:
            output.append(GLYPH_TO_TOKEN[char])
        elif "a" <= char <= "z":
            output.append(char)
        else:
            raise ValueError(f"Unsupported pinyin glyph {char!r} in {marked!r}")
    return "".join(output)


def glyph_width_percent(character: str, font: ImageFont.FreeTypeFont) -> int:
    """Return the natural glyph advance as a percentage of the atlas square."""
    width = float(font.getlength(character))
    return max(12, min(100, int(round(width * 100.0 / float(font.size)))))


def pack_i4(character: str, font: ImageFont.FreeTypeFont) -> bytes:
    image = Image.new("L", (GLYPH_SIZE, GLYPH_SIZE), 0)
    draw = ImageDraw.Draw(image)

    # Keep a common typographic baseline AND a common left origin. The game
    # advances the pen by each glyph's measured font advance; centering glyphs
    # inside their square atlas tiles adds a different hidden left bearing to
    # every letter (most visibly around pairs such as "g r"). Left-aligning the
    # ink in every tile makes that measured advance correspond to visible text.
    # The fixed inset leaves room for antialiasing/negative bearings; baseline
    # 96 reserves headroom for tone marks and descenders such as y and g.
    bbox = draw.textbbox((0, 0), character, font=font, anchor="ls")
    left_inset = 12
    x = left_inset - bbox[0]
    baseline = 96
    draw.text((x, baseline), character, fill=255, font=font, anchor="ls")
    pixels = list(image.getdata())
    output = bytearray(GLYPH_BYTES)
    for index in range(0, len(pixels), 2):
        output[index // 2] = ((pixels[index] >> 4) << 4) | (pixels[index + 1] >> 4)
    if not any(output):
        raise ValueError(f"Font produced a blank bitmap for {character!r}")
    return bytes(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnmod-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    root = args.cnmod_root.resolve()
    texts = []
    for name in ("mm_text_cn.reviewed.txt", "mm_text_cn.supplemental.txt"):
        path = root / name
        if path.exists():
            texts.append(path.read_text(encoding="utf-8"))
    if not texts:
        raise SystemExit(f"No translation text files found under {root}")

    characters = sorted(set(re.findall(r"[\u3400-\u9fff]", "\n".join(texts))))
    rows = []
    for character in characters:
        result = pinyin(character, style=Style.TONE3, heteronym=False, strict=False)
        if not result or not result[0]:
            continue
        tone3 = result[0][0].lower()
        try:
            marked = tone3_to_marked(tone3)
            encoded = encode_syllable(marked)
        except ValueError as error:
            raise SystemExit(f"Pinyin generation failed for {character!r} U+{ord(character):04X}: {error}")
        rows.append((ord(character), encoded))

    # Bold Windows font with Latin Extended coverage for macron, acute,
    # caron, grave and diaeresis vowels.
    font_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\tahomabd.ttf"),
    ]
    font_path = next((candidate for candidate in font_candidates if candidate.exists()), None)
    if font_path is None:
        raise SystemExit("No supported bold Windows font found for pinyin glyphs.")
    font = ImageFont.truetype(str(font_path), 104)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        output.write("/* Generated marked pinyin; uppercase bytes are tone-mark glyph tokens. */\n")
        output.write("static const CnPinyinEntry gCnPinyinEntries[] = {\n")
        for codepoint, syllable in rows:
            output.write(f'    {{ 0x{codepoint:04X}, "{syllable}" }},\n')
        output.write("};\n\n")

        output.write(f'static const char gCnPinyinGlyphCharacters[] = "{TOKEN_CHARS}";\n')
        glyphs_by_token = {**{char: char for char in "abcdefghijklmnopqrstuvwxyz"}, **TOKEN_TO_GLYPH}
        glyph_widths = [glyph_width_percent(glyphs_by_token[token], font) for token in TOKEN_CHARS]
        output.write(f"static const u8 gCnPinyinGlyphWidthPercent[{len(TOKEN_CHARS)}] = {{\n")
        for offset in range(0, len(glyph_widths), 13):
            output.write("    " + ", ".join(str(value) for value in glyph_widths[offset:offset + 13]) + ",\n")
        output.write("};\n")
        output.write(f"static const u8 gCnPinyinGlyphBitmaps[{len(TOKEN_CHARS)}][{GLYPH_BYTES}] = {{\n")
        for token in TOKEN_CHARS:
            visible_glyph = glyphs_by_token[token]
            bitmap = pack_i4(visible_glyph, font)
            output.write("    {\n")
            for offset in range(0, len(bitmap), 16):
                row = bitmap[offset:offset + 16]
                output.write("        " + ", ".join(f"0x{value:02X}" for value in row) + ",\n")
            output.write("    },\n")
        output.write("};\n")

    # Assert orthographic placement for common cases before packaging.
    examples = {
        "ni3": "nǐ",
        "hao3": "hǎo",
        "xue2": "xué",
        "liu2": "liú",
        "gui3": "guǐ",
        "nv3": "nǚ",
        "ma5": "ma",
    }
    for source_syllable, expected in examples.items():
        actual = tone3_to_marked(source_syllable)
        if actual != expected:
            raise SystemExit(f"Tone-mark self-test failed for {source_syllable}: {actual!r} != {expected!r}")
        encode_syllable(actual)

    print(f"Generated marked pinyin for {len(rows)} Hanzi and {len(TOKEN_CHARS)} glyphs.")
    print("Tone placement self-tests passed: ni3, hao3, xue2, liu2, gui3, nv3, ma5.")


if __name__ == "__main__":
    main()
