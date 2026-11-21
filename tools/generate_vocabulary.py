#!/usr/bin/env python3
"""Generate a compact, game-specific CC-CEDICT word glossary.

The resulting table contains only words actually present in the Chinese MM
translation corpus. This keeps the runtime lookup small while preserving
word-level pronunciation (including polyphones) and English glosses.
"""
from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path
from typing import Iterable

MAX_WORD_LENGTH = 8
CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3007]+")
ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.*)/$")
TONE_GLYPHS = {
    ("a", 1): "ā", ("a", 2): "á", ("a", 3): "ǎ", ("a", 4): "à",
    ("e", 1): "ē", ("e", 2): "é", ("e", 3): "ě", ("e", 4): "è",
    ("i", 1): "ī", ("i", 2): "í", ("i", 3): "ǐ", ("i", 4): "ì",
    ("o", 1): "ō", ("o", 2): "ó", ("o", 3): "ǒ", ("o", 4): "ò",
    ("u", 1): "ū", ("u", 2): "ú", ("u", 3): "ǔ", ("u", 4): "ù",
    ("ü", 1): "ǖ", ("ü", 2): "ǘ", ("ü", 3): "ǚ", ("ü", 4): "ǜ",
}
GLYPH_TO_TOKEN = {glyph: chr(ord("A") + i) for i, glyph in enumerate(
    "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
)}
GLYPH_TO_TOKEN["ü"] = "Y"


def tone3_to_marked(syllable: str) -> str:
    match = re.fullmatch(r"([a-zv:ü]+)([1-5]?)", syllable.lower())
    if not match:
        raise ValueError(f"Unsupported CC-CEDICT pinyin syllable: {syllable!r}")
    base, tone_text = match.groups()
    base = base.replace("u:", "ü").replace("v", "ü")
    tone = int(tone_text) if tone_text else 5
    if tone == 5:
        return base
    if "a" in base:
        index = base.index("a")
    elif "e" in base:
        index = base.index("e")
    elif "ou" in base:
        index = base.index("o")
    else:
        candidates = [i for i, char in enumerate(base) if char in "aeiouü"]
        if not candidates:
            return base
        index = candidates[-1]
    char = base[index]
    marked = TONE_GLYPHS.get((char, tone))
    if marked is None:
        raise ValueError(f"Cannot place tone {tone} on {base!r}")
    return base[:index] + marked + base[index + 1:]


def encode_pinyin(pinyin: str) -> str:
    encoded: list[str] = []
    for syllable in pinyin.split():
        marked = tone3_to_marked(syllable)
        for char in marked:
            if char in GLYPH_TO_TOKEN:
                encoded.append(GLYPH_TO_TOKEN[char])
            elif "a" <= char <= "z":
                encoded.append(char)
            else:
                raise ValueError(f"Unsupported pinyin character {char!r} in {pinyin!r}")
        encoded.append(" ")
    return "".join(encoded).rstrip()


def clean_gloss(raw: str, limit: int = 68) -> str:
    # The dialogue atlas only guarantees a-z; keep the tooltip fully renderable.
    senses = raw.split("/")
    cleaned: list[str] = []
    for sense in senses:
        sense = re.sub(r"\[[^\]]*\]", " ", sense)
        sense = re.sub(r"\([^)]*\)", " ", sense)
        sense = re.sub(r"[^A-Za-z ]", " ", sense).lower()
        sense = " ".join(sense.split())
        if sense and sense not in cleaned:
            cleaned.append(sense)
        if len(cleaned) == 2:
            break
    result = " or ".join(cleaned) or "meaning unavailable"
    if len(result) > limit:
        result = result[:limit].rsplit(" ", 1)[0]
    return result


def read_cedict(path: Path) -> dict[str, tuple[str, str]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    entries: dict[str, tuple[str, str]] = {}
    with opener(path, "rt", encoding="utf-8", errors="replace") as source:
        for line in source:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = ENTRY.match(line)
            if not match:
                continue
            _traditional, simplified, pinyin, gloss = match.groups()
            if not simplified or len(simplified) > MAX_WORD_LENGTH:
                continue
            if any(ord(char) > 0xFFFF for char in simplified):
                continue
            value = (pinyin.strip(), clean_gloss(gloss))
            previous = entries.get(simplified)
            # Prefer a concrete sense over entries that merely point elsewhere.
            if previous is None or previous[1].startswith("variant of "):
                entries[simplified] = value
    return entries


def read_game_runs(root: Path) -> Iterable[str]:
    found = False
    for name in ("mm_text_cn.reviewed.txt", "mm_text_cn.supplemental.txt"):
        path = root / name
        if not path.exists():
            continue
        found = True
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            # Remove game control-code payloads before extracting natural language.
            line = re.sub(r"\{[^}]*\}|\[[0-9A-Fa-f]{2,8}\]", " ", line)
            for run in CJK_RUN.findall(line):
                if run:
                    yield run
    if not found:
        raise FileNotFoundError(f"No reviewed/supplemental translation files found in {root}")


def collect_words(runs: Iterable[str], entries: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    words: dict[str, tuple[str, str]] = {}
    for run in runs:
        pos = 0
        while pos < len(run):
            matched: str | None = None
            upper = min(MAX_WORD_LENGTH, len(run) - pos)
            for length in range(upper, 0, -1):
                candidate = run[pos:pos + length]
                if candidate in entries:
                    matched = candidate
                    break
            if matched is None:
                pos += 1
                continue
            words[matched] = entries[matched]
            pos += len(matched)
    return words


def c_string(value: str) -> str:
    # Pinyin/meaning are sanitized to safe single-byte ASCII tokens above.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_include(words: dict[str, tuple[str, str]], output: Path, source_label: str) -> None:
    if not words:
        raise RuntimeError("No in-game words matched CC-CEDICT; refusing to produce an empty glossary.")
    rows = []
    for hanzi, (raw_pinyin, meaning) in words.items():
        try:
            pinyin = encode_pinyin(raw_pinyin)
        except ValueError:
            continue
        if not pinyin:
            continue
        codepoints = ", ".join(f"0x{ord(char):04X}" for char in hanzi)
        rows.append((hanzi, len(hanzi), codepoints, pinyin, meaning))
    rows.sort(key=lambda row: (ord(row[0][0]), -row[1], row[0]))
    if not rows:
        raise RuntimeError("No CC-CEDICT entries had pinyin that the renderer can display.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as target:
        target.write("/* Generated subset of CC-CEDICT. Source: MDBG; CC BY-SA 4.0. */\n")
        target.write(f"/* Words present in the pinned MM Chinese translation corpus; source label: {source_label}. */\n")
        target.write("static const CnWordEntry gCnWordEntries[] = {\n")
        for _hanzi, length, codepoints, pinyin, meaning in rows:
            target.write(f"    {{ {{ {codepoints} }}, {length}, {c_string(pinyin)}, {c_string(meaning)} }},\n")
        target.write("};\n")
    print(f"Generated {len(rows)} in-game glossary entries from CC-CEDICT.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnmod-root", required=True, type=Path)
    parser.add_argument("--cedict", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    entries = read_cedict(args.cedict.resolve())
    runs = list(read_game_runs(args.cnmod_root.resolve()))
    words = collect_words(runs, entries)
    write_include(words, args.output.resolve(), args.cedict.name)

    # Guard the most common polyphone examples; these are word entries, not
    # isolated-character guesses.
    for source, expected in (("银行", "yin2 hang2"), ("音乐", "yin1 yue4"), ("重要", "zhong4 yao4")):
        if source in words and words[source][0].replace(" ", "") != expected.replace(" ", ""):
            print(f"Notice: CC-CEDICT variant for {source}: {words[source][0]}")


if __name__ == "__main__":
    main()
