# MM Chinese-English Toggle

A Majora's Mask: Recompiled mod project targeting **version 1.2.2**.

## Goal

Switch the in-game text language between:
- **English** (default)
- **Simplified Chinese** (based on the community Chinese localization)

The intended hotkey is **F5**. The language must change immediately, including while a message is open, without closing the dialogue, restarting the game, resetting progress, editing the ROM, or modifying save files.

Optional pinyin is intended to appear on a second line below Chinese characters. It is **OFF by default**. User preferences must persist.

## Current status

This repository currently contains the project specification and technical investigation. It is **not yet a working or installable mod**. No `.nrm` has been built or tested.

The main unresolved engineering requirement is reliable F5 input detection from a Majora's Mask: Recompiled mod. The official mod template exposes configuration and UI APIs, but the public mod API inspected so far does not establish a supported arbitrary-key polling interface. We must not substitute an unverified SDL/native-DLL polling trick and claim it works.

## Target compatibility

- Game: Majora's Mask: Recompiled
- Minimum version: `1.2.2`
- Mod display name: `MM Chinese-English Toggle`
- Initial language: English
- Toggle: F5 (required)
- Pinyin: optional, default OFF
- Persistence: language and pinyin preferences
- Save/ROM safety: no save-file or ROM modifications

## Planned architecture

1. Reuse the Chinese localization's translated message data and glyph-rendering approach, subject to its license and attribution requirements.
2. Separate language selection from message rendering so English text is restored correctly when Chinese mode is inactive.
3. Implement a safe language switch at message decode/draw boundaries so an already-open dialogue updates without resetting its current progress.
4. Add persistent mod settings for language and pinyin.
5. Add F5 only through a verified, supported input path for this exact Recompiled runtime version.
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
