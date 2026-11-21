# Third-party notices

This project adapts the text and glyph renderer from:

- Majora's Mask Chinese Localization, by SilntRavn
- Repository: https://github.com/SilntRavn/MajorasMask-Chinese-Localization
- Pinned revision: 6590dec4a7826d6a3cc96d2092a514a02f0c52dc
- License: GNU General Public License v3.0 (see the upstream repository's LICENSE file)

The Chinese texture companion mod remains a separate dependency and is not redistributed here. Font and texture license notices from the upstream package are retained inside the built NRM as configured by its manifest.

Build-time dependency:
- Majora's Mask decompilation: https://github.com/zeldaret/mm
- Pinned revision: 385c45ad483502a03c6f93b81e5b1ed5e08281d0

No ROM image or save data is included.

## CC-CEDICT dictionary data

The contextual word dictionary is generated from a filtered subset of CC-CEDICT:

- Source: MDBG / CC-CEDICT — https://www.mdbg.net/chinese/dictionary?page=cc-cedict
- Download source: https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- The generated subset is restricted to words occurring in the Chinese Majora's Mask translation corpus. Pinyin tone numbers are converted into tone-marked glyph tokens, and English glosses are shortened and normalized to the game's Latin glyph atlas.

The generated dictionary subset is a database adaptation of CC-CEDICT and is provided under CC BY-SA 4.0. Credit belongs to MDBG, the CC-CEDICT editors and contributors. See the source page for the complete license terms.
