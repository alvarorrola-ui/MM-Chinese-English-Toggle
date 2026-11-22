# Project specification

## User-visible behavior

| Item | Requirement |
|---|---|
| Startup language | Simplified Chinese |
| Hotkey | Ñ, optional and disabled by default in mod configuration |
| Alternate language | Simplified Chinese |
| Switch while dialogue is open | Immediate; preserve message position/progress |
| Pinyin | Optional second line; tone marks; OFF by default; word-level readings when dictionary match exists |
| Persistence | Remember language and pinyin preferences |
| ROM | Must not be modified |
| Save files | Must not be modified |
| Target | Majora's Mask: Recompiled 1.2.2 |

## Learning and hover dictionary

- The user can hover a recognized Chinese word in an open dialogue.
- The tooltip shows the matched Hanzi, contextual tone-marked pinyin, and a concise English meaning.
- Word segmentation uses longest dictionary match so polyphonic characters can use the reading of the full word.
- The hover feature can be disabled in mod configuration without disabling language switching.
- The tooltip disappears when the pointer leaves the word, the dialogue closes, or English is selected.
- No OCR is used; hitboxes are aligned from the Chinese renderer's character positions.

## Acceptance tests

- [ ] Mod loads on Recompiled 1.2.2.
- [ ] New installations start in Simplified Chinese.
- [ ] The Ñ language-toggle option is Off by default.
- [ ] With the option Off, Ñ does not change the language.
- [ ] With the option On, Ñ switches between Chinese and English.
- [ ] Ñ works while a dialogue is open when the option is enabled.
- [ ] Switching does not close the dialogue or reset its character/page position.
- [ ] Switching does not require a restart.
- [ ] Pinyin is hidden by default.\n- [ ] Hovering a recognized Chinese word shows Hanzi, contextual pinyin and an English gloss.\n- [ ] The tooltip does not obstruct dialogue progression or controller input.\n- [ ] The hover dictionary can be disabled independently in mod configuration.\n- [ ] Hover hitboxes remain aligned at supported window sizes and aspect ratios.
- [ ] Enabling pinyin shows correctly toned pinyin below Chinese text.
- [ ] Language and pinyin settings persist across game restarts.
- [ ] Existing save files remain unchanged.
- [ ] ROM remains unchanged.

## Blocker to resolve before implementation

Find and verify a supported way for a game mod to receive F5 key-down events in Majora's Mask: Recompiled 1.2.2. Do not assume that the runtime's internal SDL keyboard state is exposed to mods. If a native-library bridge is needed, establish the exact supported ABI/callback route before writing it.
