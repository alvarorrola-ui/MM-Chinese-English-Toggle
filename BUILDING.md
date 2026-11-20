# Build and install

This repository builds a Windows package for Majora's Mask: Recompiled 1.2.2.

## Build

The automated GitHub Actions workflow builds on pushes to the main branch and can also be started manually from the Actions tab. It checks out the pinned Chinese localization and Majora's Mask decompilation, uses Clang/LLD 18.1.8, generates a tone-number pinyin lookup, builds the NRM, and builds the companion native DLL.

The output package contains:
- mm_chinese_english_toggle.nrm
- mm_cht_input.dll
- INSTALL.txt

Both binary files must be placed beside one another in the game's mods folder.

Before enabling this mod, keep the upstream `mm_chinese_localization_texture` dependency enabled and above this mod in the mod list. If the original `mm_chinese_localization_text` mod is installed, disable it: both text mods hook the same message-rendering functions and must not run together.

## Design

- F5 is sampled by a Windows native library and edge-detected in the official recomp_on_play_main callback.
- Language choice is stored in mm_cht_language.state beside the DLL. The initial value is English.
- The original decoded English message buffer is saved before the Chinese renderer hides it. Switching back restores it, including during an open dialogue.
- Pinyin is generated from the reviewed and supplemental upstream translations, includes tone numbers, and is disabled by default.
- The Chinese texture companion mod remains a required dependency, matching the upstream localization package.
- ROM and save files are not modified.

## Not yet verified in-game

The code must be compiled and then tested in a real 1.2.2 installation to verify the native ABI, F5 behavior, text switching on every text path, and pinyin spacing. A successful compiler run is not proof of in-game behavior.
