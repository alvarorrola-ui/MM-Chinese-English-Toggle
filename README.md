# MM Chinese-English Toggle

A Majora's Mask: Recompiled mod project targeting **version 1.2.2**.

## Goal

Switch the in-game text language between:
- **English** (default)
- **Simplified Chinese** (based on the community Chinese localization)

The intended hotkey is **Ñ**. The language must change immediately, including while a message is open, without closing the dialogue, restarting the game, resetting progress, editing the ROM, or modifying save files.

Optional pinyin is intended to appear on a second line below Chinese characters. It is **OFF by default**. User preferences must persist.

## Current status

A Windows build now completes successfully in GitHub Actions. The generated package contains:
- `mm_chinese_english_toggle.nrm`
- `mm_cht_input.dll`
- `INSTALL.txt`

The build uses a companion native Windows library to detect the Ñ key and an official per-frame Recompiled callback to switch languages. Pinyin tone-mark data and a dedicated Latin/accented-vowel glyph atlas are generated at build time. See the latest successful [GitHub Actions run](https://github.com/alvarorrola-ui/MM-Chinese-English-Toggle/actions/runs/44723522418).

**Important:** compilation and packaging have passed, but the mod has not yet been validated inside a live Majora's Mask: Recompiled 1.2.2 game session. In particular, the live dialogue-switch behavior, all message paths, and pinyin layout still need in-game testing.

## Language-learning features

The current implementation adds a contextual word glossary to Chinese dialogue:

- Hover over a recognized Chinese word with the mouse to show a small in-game tooltip.
- The tooltip shows the Hanzi, word-level tone-marked pinyin, and a concise English gloss.
- The dictionary is filtered to vocabulary that occurs in the game's Chinese translation files, rather than bundling the entire CC-CEDICT database.
- A separate `Word Dictionary` mod setting controls the hover feature and is enabled by default.
- Pinyin display remains independently configurable.

The word glossary is generated from CC-CEDICT (MDBG, CC BY-SA 4.0). Its source and data license are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**Limitations of this first iteration:** meanings are in English; words absent from the dictionary do not get a tooltip; at most 64 word hitboxes are active per message page. Contextual phrase matching improves polyphonic readings, while the existing character-level pinyin lookup remains the fallback for unmatched text.

The hover UI uses Recompiled's mouse-hover event API. Compilation alone does not prove that its pointer coordinates align correctly with the game's 320×240 dialogue renderer on every window size or aspect ratio; this still requires live testing.

## Target compatibility

- Game: Majora's Mask: Recompiled
- Minimum version: `1.2.2`
- Mod display name: `MM Chinese-English Toggle`
- Initial language: English
- Toggle: Ñ (required)
- Pinyin: optional, tone diacritics (ā á ǎ à), default OFF
- Persistence: language and pinyin preferences
- Save/ROM safety: no save-file or ROM modifications

## Planned architecture

1. Reuse the Chinese localization's translated message data and glyph-rendering approach, subject to its license and attribution requirements.
2. Separate language selection from message rendering so English text is restored correctly when Chinese mode is inactive.
3. Implement a safe language switch at message decode/draw boundaries so an already-open dialogue updates without resetting its current progress.
4. Add persistent mod settings for language and pinyin.
5. Add Ñ only through a verified, supported input path for this exact Recompiled runtime version.
6. Build with the official Majora's Mask: Recompiled mod toolchain and test in-game.

## Important technical constraint

The Chinese localization is not merely a table of translated strings: it includes custom glyph handling and hooks into message decoding/rendering. A correct toggle must account for those hooks, including message windows and non-dialogue text. Simply swapping a language variable or showing a config enum at startup is insufficient for the requested live switch.

## References

- Official mod template: https://github.com/Zelda64Recomp/MMRecompModTemplate
- Chinese localization: https://github.com/SilntRavn/MajorasMask-Chinese-Localization
- Majora's Mask: Recompiled: https://github.com/Zelda64Recomp/Zelda64Recomp

## Development rules

- Do not claim a feature is implemented until the code builds and the behavior has been tested.
- Do not distribute ROM data or copyrighted game assets.
- Preserve the original Chinese localization's licensing and attribution conditions when incorporating or adapting its code/data.
