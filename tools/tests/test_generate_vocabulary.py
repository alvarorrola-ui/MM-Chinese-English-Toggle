from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_vocabulary as vocabulary


class VocabularyGeneratorTests(unittest.TestCase):
    def test_tone_mark_placement(self) -> None:
        cases = {
            "ni3": "nǐ",
            "hao3": "hǎo",
            "xue2": "xué",
            "liu2": "liú",
            "gui3": "guǐ",
            "nv3": "nǚ",
            "ma5": "ma",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(vocabulary.tone3_to_marked(source), expected)

    def test_pinyin_encoding_uses_single_byte_tokens(self) -> None:
        encoded = vocabulary.encode_pinyin("ni3 hao3")
        self.assertTrue(encoded.isascii())
        self.assertEqual(len(encoded.split()), 2)

    def test_cc_cedict_parser_and_simplified_form(self) -> None:
        sample = (
            "# test dictionary\\n"
            "銀行 银行 [yin2 hang2] /bank/\\n"
            "音樂 音乐 [yin1 yue4] /music/\\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cedict.txt"
            path.write_text(sample, encoding="utf-8")
            entries = vocabulary.read_cedict(path)
        self.assertEqual(entries["银行"][0], "yin2 hang2")
        self.assertEqual(entries["音乐"][0], "yin1 yue4")
        self.assertEqual(entries["银行"][1], "bank")

    def test_longest_matching_collects_phrase_not_individual_characters(self) -> None:
        entries = {
            "银": ("yin2", "silver"),
            "行": ("xing2", "to walk"),
            "银行": ("yin2 hang2", "bank"),
        }
        words = vocabulary.collect_words(["去银行"], entries)
        self.assertEqual(words, {"银行": ("yin2 hang2", "bank")})

    def test_gloss_uses_only_renderable_ascii_letters(self) -> None:
        gloss = vocabulary.clean_gloss("/to test (something)/experiment; trial/")
        self.assertRegex(gloss, r"^[a-z ]+$|^([a-z ]+ or [a-z ]+)$")


if __name__ == "__main__":
    unittest.main()
