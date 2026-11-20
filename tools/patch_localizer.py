#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
from pathlib import Path

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact source match, found {count}")
    return source.replace(old, new, 1)

def add_language_guard(source: str, function_name: str) -> str:
    pattern = re.compile(r'(RECOMP_HOOK(?:_RETURN)?\("[^"]+"\)\s*void\s+' +
                         re.escape(function_name) + r'\s*\([^)]*\)\s*\{)', re.S)
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise RuntimeError(f"Could not uniquely locate hook {function_name}: {len(matches)}")
    match = matches[0]
    if source[match.end():].lstrip().startswith("if (!sChineseEnabled)"):
        return source
    return source[:match.end()] + "\n    if (!sChineseEnabled) return;" + source[match.end():]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod-dir", required=True, type=Path)
    mod_dir = parser.parse_args().mod_dir.resolve()
    source_path = mod_dir / "src" / "chinese_text.c"
    manifest_path = mod_dir / "mod.toml"
    build_path = mod_dir / "build.ps1"
    source = source_path.read_text(encoding="utf-8")

    if "MMCHT_LANGUAGE_TOGGLE_PATCH" in source:
        print("Chinese localization source already patched.")
        return

    anchor = '#include "generated/file_select_arrow_texture.inc"\n'
    imports = r'''
#include "recompconfig.h"
#include <string.h>

typedef struct {
    u16 codepoint;
    const char* syllable;
} CnPinyinEntry;

#include "generated/pinyin_data.inc"

RECOMP_IMPORT(".", u32 mmcht_ntilde_down(void));
RECOMP_IMPORT(".", u32 mmcht_load_language(void));
RECOMP_IMPORT(".", void mmcht_save_language(u32 enabled));

/* State used by hooks declared below. */
static bool sChineseEnabled;
static bool sNtildeWasDown;
static bool sOriginalDecodedBufferValid;
static u8 sOriginalDecodedBuffer[sizeof(((MessageContext*)0)->decodedBuffer)];
'''
    source = replace_once(source, anchor, anchor + imports, "insert imports")

    anchor = "static bool sVanillaTextHidden;\n"
    state = r'''static bool cn_pinyin_enabled(void) {
    return recomp_get_config_u32("pinyin") == 1;
}
'''
    source = replace_once(source, anchor, anchor + state, "language state")

    glyph_anchor = r'''static void cn_draw_glyph(Gfx** gfxP, const u8* texture, s16 x, s16 y, s16 drawSize,
                          Color_RGB8 color, u8 alpha, bool shadow) {
    cn_draw_glyph_subpixel(gfxP, texture, x, y, drawSize, 0, color, alpha, shadow);
}
'''
    pinyin_helpers = r'''
static const char* cn_find_pinyin(u16 codepoint) {
    s32 low = 0;
    s32 high = (s32)ARRAY_COUNT(gCnPinyinEntries) - 1;
    while (low <= high) {
        s32 mid = low + ((high - low) / 2);
        if (gCnPinyinEntries[mid].codepoint == codepoint) return gCnPinyinEntries[mid].syllable;
        if (gCnPinyinEntries[mid].codepoint < codepoint) low = mid + 1;
        else high = mid - 1;
    }
    return NULL;
}

/* Render pinyin in a separate wrapped panel above the main dialogue. */
static void cn_draw_pinyin_panel(Gfx** gfxP, MessageContext* msgCtx, const char* text) {
    const s16 panelLeft = 8, panelRight = 312, contentLeft = 13, contentRight = 307;
    const s16 glyphSize = 5, advance = 5, rowHeight = 7, wordGap = 3;
    const Color_RGB8 pinyinColor = { 225, 238, 255 };
    const char* word;
    s16 rows = 1, measureX = contentLeft, panelHeight, panelTop;
    s16 x, y, maxRows;
    Gfx* gfx;

    if (!cn_pinyin_enabled() || (text == NULL) || (*text == '\0')) return;

    word = text;
    while (*word != '\0') {
        s16 wordLength = 0;
        while ((word[wordLength] != '\0') && (word[wordLength] != ' ')) wordLength++;
        if (wordLength == 0) { word++; continue; }
        if ((measureX > contentLeft) && (measureX + wordLength * advance > contentRight)) {
            rows++;
            measureX = contentLeft;
        }
        measureX += (wordLength * advance) + wordGap;
        word += wordLength;
        if (*word == ' ') word++;
    }

    panelHeight = rows * rowHeight + 6;
    panelTop = msgCtx->textboxYTarget - panelHeight - 4;
    maxRows = rows;
    if (panelTop < 30) {
        panelTop = 30;
        maxRows = (msgCtx->textboxYTarget - panelTop - 4) / rowHeight;
        if (maxRows < 1) return;
        if (maxRows < rows) panelHeight = maxRows * rowHeight + 6;
    }

    gfx = *gfxP;
    gDPPipeSync(gfx++);
    gDPSetCycleType(gfx++, G_CYC_FILL);
    gDPSetFillColor(gfx++, ((u32)GPACK_RGBA5551(110, 88, 55, 1) << 16) |
                            GPACK_RGBA5551(110, 88, 55, 1));
    gDPFillRectangle(gfx++, panelLeft << 2, panelTop << 2, panelRight << 2,
                     (panelTop + panelHeight) << 2);
    gDPSetFillColor(gfx++, ((u32)GPACK_RGBA5551(7, 10, 17, 1) << 16) |
                            GPACK_RGBA5551(7, 10, 17, 1));
    gDPFillRectangle(gfx++, (panelLeft + 1) << 2, (panelTop + 1) << 2,
                     (panelRight - 1) << 2, (panelTop + panelHeight - 1) << 2);
    gDPPipeSync(gfx++);
    gDPSetCycleType(gfx++, G_CYC_1CYCLE);
    gDPSetRenderMode(gfx++, G_RM_XLU_SURF, G_RM_XLU_SURF2);
    gDPSetCombineLERP(gfx++, 0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0,
                      0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0);
    gDPSetTextureFilter(gfx++, G_TF_BILERP);
    *gfxP = gfx;

    x = contentLeft;
    y = panelTop + 3;
    word = text;
    while ((*word != '\0') && (y + glyphSize <= panelTop + panelHeight - 2)) {
        s16 wordLength = 0, i;
        while ((word[wordLength] != '\0') && (word[wordLength] != ' ')) wordLength++;
        if (wordLength == 0) { word++; continue; }
        if ((x > contentLeft) && (x + wordLength * advance > contentRight)) {
            x = contentLeft;
            y += rowHeight;
            if (y + glyphSize > panelTop + panelHeight - 2) break;
        }
        for (i = 0; i < wordLength; i++) {
            const u8* glyph = cn_find_glyph((u16)word[i]);
            if (glyph != NULL) {
                cn_draw_glyph_subpixel(gfxP, glyph, x, y, glyphSize, 0,
                                       pinyinColor, 255, false);
            }
            x += advance;
        }
        x += wordGap;
        word += wordLength;
        if (*word == ' ') word++;
    }
}
'''
    source = replace_once(source, glyph_anchor, glyph_anchor + pinyin_helpers, "pinyin renderer")

    start = source.index("static void cn_draw_page(PlayState* play, Gfx** gfxP) {")
    end = source.index("static bool cn_message_draws_text_this_frame", start)
    chunk = source[start:end]
    # Pinyin has its own panel; leave Chinese line spacing unchanged.
    glyph = r'''        const u8* glyph = cn_find_glyph(command);
        if (glyph != NULL) {
            bool shadow = (msgCtx->textBoxType != TEXTBOX_TYPE_CLEAR) &&
                          (msgCtx->textBoxType != TEXTBOX_TYPE_NOTEBOOK_NOTIFICATION) &&
                          !play->pauseCtx.bombersNotebookOpen;
            cn_draw_glyph(gfxP, glyph, x, y, glyphSize, color, commandAlpha, shadow);
        }
        x += glyphSize;
'''
    glyph_new = r'''        const u8* glyph = cn_find_glyph(command);
        if (glyph != NULL) {
            bool shadow = (msgCtx->textBoxType != TEXTBOX_TYPE_CLEAR) &&
                          (msgCtx->textBoxType != TEXTBOX_TYPE_NOTEBOOK_NOTIFICATION) &&
                          !play->pauseCtx.bombersNotebookOpen;
            cn_draw_glyph(gfxP, glyph, x, y, glyphSize, color, commandAlpha, shadow);
        }
        if ((command >= 0x3400) && (command <= 0x9FFF)) {
            cn_draw_pinyin(gfxP, command, x, y, glyphSize, color, commandAlpha);
        }
        x += glyphSize;
'''
    chunk = replace_once(chunk, glyph, glyph_new, "pinyin draw")
    source = source[:start] + chunk + source[end:]

    page_y_old = r'''    } else {
        offset = 26 - ((page->lineCount - 1) * 6);
        if (offset < 8) {
            offset = 8;
        }
    }
    return msgCtx->textboxYTarget + offset;
}'''
    page_y_new = page_y_old
    source = replace_once(source, page_y_old, page_y_new, "pinyin vertical alignment")

    source = replace_once(
        source,
        "    if (cn_owls_never_quit_loaded() && (play->msgCtx.currentTextId == 0x0C01) &&\n",
        "    if (sChineseEnabled && cn_owls_never_quit_loaded() && (play->msgCtx.currentTextId == 0x0C01) &&\n",
        "English owl prompt",
    )
    source = replace_once(source, "    textId = cn_desired_message_id(play);\n",
                          "    textId = sChineseEnabled ? cn_desired_message_id(play) : play->msgCtx.currentTextId;\n",
                          "active language message selection")

    decode_old = r'''RECOMP_HOOK_RETURN("Message_DecodeNES") void cn_message_decode_return(void) {
    if (sMessage != NULL) {
        if (sPlay->msgCtx.textboxEndType == TEXTBOX_ENDTYPE_INPUT_DOGGY_RACETRACK_BET) {
            cn_normalize_dog_bet_input(&sPlay->msgCtx);
        }
        if ((sPageIndex + 1) < sMessage->pageCount) {
            sPageIndex++;
        }
        cn_blank_vanilla_text(&sPlay->msgCtx);
    }
}'''
    decode_new = r'''RECOMP_HOOK_RETURN("Message_DecodeNES") void cn_message_decode_return(void) {
    if (sMessage != NULL) {
        memcpy(sOriginalDecodedBuffer, &sPlay->msgCtx.decodedBuffer,
               sizeof(sPlay->msgCtx.decodedBuffer));
        sOriginalDecodedBufferValid = true;
        if (sChineseEnabled &&
            (sPlay->msgCtx.textboxEndType == TEXTBOX_ENDTYPE_INPUT_DOGGY_RACETRACK_BET)) {
            cn_normalize_dog_bet_input(&sPlay->msgCtx);
        }
        if ((sPageIndex + 1) < sMessage->pageCount) {
            sPageIndex++;
        }
        if (sChineseEnabled) {
            cn_blank_vanilla_text(&sPlay->msgCtx);
        }
    }
}'''
    source = replace_once(source, decode_old, decode_new, "save/restore English text")

    for name in [
        "cn_draw_a_button", "cn_draw_b_button", "cn_draw_b_button_return",
        "cn_file_select_draw_keyboard_return", "cn_name_entry_draw",
        "cn_name_entry_draw_return", "cn_file_select_draw", "cn_file_select_draw_return",
        "cn_title_draw", "cn_title_hide_press_start", "cn_title_draw_return",
        "cn_interface_draw", "cn_day_telop_draw", "cn_day_telop_draw_return",
        "cn_dog_bet_input",
    ]:
        source = add_language_guard(source, name)

    source = replace_once(
        source,
        'RECOMP_HOOK("Message_DrawMain") void cn_message_draw(PlayState* play, Gfx** gfxP) {\n    sPlay = play;',
        'RECOMP_HOOK("Message_DrawMain") void cn_message_draw(PlayState* play, Gfx** gfxP) {\n'
        '    if (!sChineseEnabled) { sCreditTextHidden = false; sVanillaTextHidden = false; sDrawTextThisFrame = false; return; }\n'
        '    sPlay = play;',
        "English dialogue draw",
    )
    source = replace_once(
        source,
        'RECOMP_HOOK_RETURN("Message_DrawMain") void cn_message_draw_return(void) {\n    if (sCreditTextHidden) {',
        'RECOMP_HOOK_RETURN("Message_DrawMain") void cn_message_draw_return(void) {\n'
        '    if (!sChineseEnabled) return;\n'
        '    if (sCreditTextHidden) {',
        "English dialogue draw return",
    )

    callbacks = r'''

/* MMCHT_LANGUAGE_TOGGLE_PATCH
 * the Ñ key is polled by the companion Windows native library and edge-detected here.
 * The saved retail decoded buffer is restored before vanilla rendering resumes.
 */
static void mmcht_set_language(PlayState* play, bool chinese) {
    sChineseEnabled = chinese;
    if (sOriginalDecodedBufferValid) {
        memcpy(&play->msgCtx.decodedBuffer, sOriginalDecodedBuffer,
               sizeof(play->msgCtx.decodedBuffer));
        if (sChineseEnabled && (sMessage != NULL)) {
            cn_blank_vanilla_text(&play->msgCtx);
        }
    }
}

RECOMP_CALLBACK("*", recomp_on_init)
void mmcht_initialize_language(void) {
    sChineseEnabled = (mmcht_load_language() != 0);
    sNtildeWasDown = (mmcht_ntilde_down() != 0);
}

RECOMP_CALLBACK("*", recomp_on_play_main)
void mmcht_poll_ntilde(PlayState* play) {
    bool ntildeDown = (mmcht_ntilde_down() != 0);
    if (ntildeDown && !sNtildeWasDown) {
        mmcht_set_language(play, !sChineseEnabled);
        mmcht_save_language(sChineseEnabled ? 1 : 0);
    }
    sNtildeWasDown = ntildeDown;
}
'''
    source = source.rstrip() + callbacks + "\n"
    source_path.write_text(source, encoding="utf-8", newline="\n")

    # Add every Latin letter and tone digit to the localization's proven glyph atlas.
    generator_path = mod_dir.parent / "tools" / "generate_mod_data.py"
    generator = generator_path.read_text(encoding="utf-8")
    glyph_anchor = '    font = ImageFont.truetype(str(font_path), GLYPH_FONT_SIZE)\n'
    glyph_addition = (
        '    # MMCHT: glyphs used by generated pinyin syllables.\n'
        '    codepoints = sorted(set(codepoints) | {ord(char) for char in "abcdefghijklmnopqrstuvwxyz12345"})\n'
    )
    if "MMCHT: glyphs used by generated pinyin syllables." not in generator:
        generator = replace_once(generator, glyph_anchor, glyph_addition + glyph_anchor,
                                 "add pinyin Latin glyphs to main atlas")
        generator_path.write_text(generator, encoding="utf-8", newline="\n")

    manifest = manifest_path.read_text(encoding="utf-8")
    manifest = replace_once(manifest, 'id = "mm_chinese_localization_text"',
                            'id = "mm_chinese_english_toggle"', "manifest id")
    manifest = replace_once(manifest, 'display_name = "MM月陨中文译本_文本"',
                            'display_name = "MM Chinese-English Toggle"', "display name")
    manifest = replace_once(manifest, 'version = "1.0.0"',
                            'version = "0.1.0"', "manifest version")
    manifest = replace_once(manifest, 'short_description = "《魔吉拉的面具》高清中文语言包(文本)"',
                            'short_description = "Switch English and Simplified Chinese with Ñ."',
                            "short description")
    manifest = replace_once(manifest, 'authors = [ "SilntRavn" ]',
                            'authors = [ "alvarorrola-ui", "SilntRavn (Chinese localization)" ]',
                            "authors")
    manifest = replace_once(manifest, 'native_libraries = []',
                            'native_libraries = [ { name = "mm_cht_input", funcs = [ "mmcht_ntilde_down", "mmcht_load_language", "mmcht_save_language" ] } ]',
                            "native library declaration")
    manifest = replace_once(manifest, 'mod_filename = "mm_simplified_chinese"',
                            'mod_filename = "mm_chinese_english_toggle"', "mod filename")
    manifest += r'''

[[manifest.config_options]]
id = "pinyin"
name = "Pinyin"
description = "Show tone-number pinyin below Chinese dialogue characters. Off by default."
type = "Enum"
options = [ "Off", "On" ]
default = "Off"
'''
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")

    build_script = build_path.read_text(encoding="utf-8")
    build_script = replace_once(
        build_script,
        'Join-Path $BuildDir "mm_simplified_chinese.nrm"',
        'Join-Path $BuildDir "mm_chinese_english_toggle.nrm"',
        "upstream NRM output name",
    )
    build_path.write_text(build_script, encoding="utf-8", newline="\n")
    print("Patched upstream Chinese localization for English/Chinese switching.")


if __name__ == "__main__":
    main()
