# Build and install

This repository builds a Windows package for Majora's Mask: Recompiled 1.2.2.

## Build

The automated GitHub Actions workflow builds on pushes to the main branch and can also be started manually from the Actions tab. It checks out the pinned Chinese localization and Majora's Mask decompilation, uses Clang/LLD 18.1.8, generates the character fallback pinyin atlas, downloads the current CC-CEDICT export from MDBG, filters it to words in the game's Chinese translation, generates the word-level pinyin/gloss table, patches the hover UI, builds the NRM, and builds the companion native DLL.

The output package contains:
- mm_chinese_english_toggle.nrm
- mm_cht_input.dll
- INSTALL.txt

Both binary files must be placed beside one another in the game's mods folder.

Before enabling this mod, keep the upstream `mm_chinese_localization_texture` dependency enabled and above this mod in the mod list. If the original `mm_chinese_localization_text` mod is installed, disable it: both text mods hook the same message-rendering functions and must not run together.

## Design

- Ñ is sampled by a Windows native library and edge-detected in the official recomp_on_play_main callback.
- Language choice is stored in mm_cht_language.state beside the DLL. The initial value is English.
- The original decoded English message buffer is saved before the Chinese renderer hides it. Switching back restores it, including during an open dialogue.
- Pinyin is generated from the reviewed and supplemental upstream translations, uses tone diacritics (ā á ǎ à) and is disabled by default.
- The Chinese texture companion mod remains a required dependency, matching the upstream localization package.
- ROM and save files are not modified.

## Hover glossary

The mod configuration includes `Word Dictionary` (On by default). With the Chinese language active, move the mouse over a recognized word in a dialogue to show Hanzi, contextual tone-marked pinyin, and a short English definition. The tooltip is drawn by the game's text renderer; invisible Recompiled UI buttons provide the hover hitboxes. Only words matched in the filtered CC-CEDICT subset get a tooltip. The dictionary data is CC BY-SA 4.0 and is attributed in `THIRD_PARTY_NOTICES.md`.

## Not yet verified in-game

The code must be compiled and then tested in a real 1.2.2 installation to verify the native ABI, Ñ behavior, text switching on every text path, and pinyin spacing. A successful compiler run is not proof of in-game behavior.
