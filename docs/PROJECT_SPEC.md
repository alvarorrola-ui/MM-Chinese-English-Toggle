# Project specification

## User-visible behavior

| Item | Requirement |
|---|---|
| Startup language | English |
| Hotkey | F5, mandatory |
| Alternate language | Simplified Chinese |
| Switch while dialogue is open | Immediate; preserve message position/progress |
| Pinyin | Optional second line under Hanzi; tones included; OFF by default |
| Persistence | Remember language and pinyin preferences |
| ROM | Must not be modified |
| Save files | Must not be modified |
| Target | Majora's Mask: Recompiled 1.2.2 |

## Acceptance tests

- [ ] Mod loads on Recompiled 1.2.2.
- [ ] Game starts in English.
- [ ] F5 switches English to Simplified Chinese.
- [ ] F5 switches Simplified Chinese to English.
- [ ] F5 works while a dialogue is open.
- [ ] Switching does not close the dialogue or reset its character/page position.
- [ ] F5 does not require a menu or restart.
- [ ] Pinyin is hidden by default.
- [ ] Enabling pinyin shows correctly toned pinyin below Chinese text.
- [ ] Language and pinyin settings persist across game restarts.
- [ ] Existing save files remain unchanged.
- [ ] ROM remains unchanged.

## Blocker to resolve before implementation

Find and verify a supported way for a game mod to receive F5 key-down events in Majora's Mask: Recompiled 1.2.2. Do not assume that the runtime's internal SDL keyboard state is exposed to mods. If a native-library bridge is needed, establish the exact supported ABI/callback route before writing it.
