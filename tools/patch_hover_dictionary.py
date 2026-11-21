#!/usr/bin/env python3
"""Inject contextual word matching and hover glossary UI into the pinned localizer."""
from __future__ import annotations

from pathlib import Path


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact source match, found {count}")
    return source.replace(old, new, 1)


HOVER_TYPES = r'''
typedef struct {
    const CnWordEntry* entry;
    s16 x;
    s16 y;
    s16 width;
    s16 height;
} CnWordHitbox;

#define MMCHT_MAX_WORD_HITBOXES 64
#define MMCHT_TOOLTIP_WIDTH 220
#define MMCHT_TOOLTIP_HEIGHT 54

static RecompuiContext sWordHoverContext = RECOMPUI_NULL_CONTEXT;
static RecompuiResource sWordHoverRoot = RECOMPUI_NULL_RESOURCE;
static RecompuiResource sWordHoverButtons[MMCHT_MAX_WORD_HITBOXES];
static CnWordHitbox sWordHitboxes[MMCHT_MAX_WORD_HITBOXES];
static u8 sWordHitboxCount;
static s16 sHoveredWordSlot = -1;
static u16 sWordHoverTextId = 0xFFFF;
static s16 sWordHoverPage = -1;
static bool sWordHoverUiInitialized;
static bool sWordHoverUiShown;

static const CnWordEntry* cn_find_word(const u16* text, u16 remaining, u8* matchedLength) {
    s32 low = 0;
    s32 high = (s32)ARRAY_COUNT(gCnWordEntries) - 1;
    s32 first = -1;
    s32 i;
    u16 initial = text[0];
    const CnWordEntry* best = NULL;
    u8 bestLength = 0;

    *matchedLength = 0;
    while (low <= high) {
        s32 mid = low + ((high - low) / 2);
        u16 candidate = gCnWordEntries[mid].hanzi[0];
        if (candidate < initial) low = mid + 1;
        else if (candidate > initial) high = mid - 1;
        else {
            first = mid;
            high = mid - 1;
        }
    }
    if (first < 0) return NULL;

    for (i = first; i < (s32)ARRAY_COUNT(gCnWordEntries); i++) {
        const CnWordEntry* entry = &gCnWordEntries[i];
        u8 j;
        if (entry->hanzi[0] != initial) break;
        if ((entry->length == 0) || (entry->length > remaining) ||
            (entry->length <= bestLength)) continue;
        for (j = 0; j < entry->length; j++) {
            if (entry->hanzi[j] != text[j]) break;
        }
        if (j == entry->length) {
            best = entry;
            bestLength = entry->length;
        }
    }
    *matchedLength = bestLength;
    return best;
}

static void mmcht_word_hover_callback(RecompuiResource resource,
                                      const RecompuiEventData* event, void* userdata) {
    unsigned long slotValue = (unsigned long)userdata;
    s32 slot = (s32)slotValue - 1;
    (void)resource;
    if ((event == NULL) || (event->type != UI_EVENT_HOVER) ||
        (slot < 0) || (slot >= MMCHT_MAX_WORD_HITBOXES)) return;

    if (event->data.hover.active) {
        if (slot < sWordHitboxCount) sHoveredWordSlot = (s16)slot;
    } else if (sHoveredWordSlot == slot) {
        sHoveredWordSlot = -1;
    }
}

static void mmcht_setup_word_hover_ui(void) {
    RecompuiColor transparent = { 0, 0, 0, 0 };
    u32 i;
    if (sWordHoverUiInitialized) return;

    sWordHoverContext = recompui_create_context();
    if (sWordHoverContext == RECOMPUI_NULL_CONTEXT) return;
    recompui_open_context(sWordHoverContext);
    sWordHoverRoot = recompui_context_root(sWordHoverContext);
    recompui_set_position(sWordHoverRoot, POSITION_ABSOLUTE);
    recompui_set_left(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_top(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_right(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_bottom(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_width_auto(sWordHoverRoot);
    recompui_set_height_auto(sWordHoverRoot);

    for (i = 0; i < MMCHT_MAX_WORD_HITBOXES; i++) {
        RecompuiResource hitbox = recompui_create_button(
            sWordHoverContext, sWordHoverRoot, "", BUTTONSTYLE_SECONDARY);
        sWordHoverButtons[i] = hitbox;
        recompui_set_position(hitbox, POSITION_ABSOLUTE);
        recompui_set_padding(hitbox, 0.0f, UNIT_DP);
        recompui_set_border_width(hitbox, 0.0f, UNIT_DP);
        recompui_set_min_height(hitbox, 0.0f, UNIT_DP);
        recompui_set_max_height(hitbox, 200.0f, UNIT_DP);
        recompui_set_background_color(hitbox, &transparent);
        recompui_set_border_color(hitbox, &transparent);
        recompui_set_opacity(hitbox, 0.0f);
        recompui_set_cursor(hitbox, CURSOR_NONE);
        recompui_set_tab_index(hitbox, TAB_INDEX_NONE);
        recompui_set_visibility(hitbox, VISIBILITY_HIDDEN);
        recompui_register_callback(hitbox, mmcht_word_hover_callback,
                                   (void*)(unsigned long)(i + 1));
    }
    recompui_close_context(sWordHoverContext);
    recompui_set_context_captures_input(sWordHoverContext, 0);
    recompui_set_context_captures_mouse(sWordHoverContext, 1);
    sWordHoverUiInitialized = true;
}

static void mmcht_hide_word_context(void) {
    if (sWordHoverUiInitialized && sWordHoverUiShown) {
        recompui_hide_context(sWordHoverContext);
        sWordHoverUiShown = false;
    }
    sHoveredWordSlot = -1;
    sWordHitboxCount = 0;
}

static void mmcht_begin_word_frame(u16 textId, s16 pageIndex) {
    if ((textId != sWordHoverTextId) || (pageIndex != sWordHoverPage)) {
        sHoveredWordSlot = -1;
        sWordHoverTextId = textId;
        sWordHoverPage = pageIndex;
    }
    sWordHitboxCount = 0;
}

static void mmcht_add_word_hitbox(s16 x, s16 y, s16 width, s16 height,
                                  const CnWordEntry* entry) {
    CnWordHitbox* box;
    if ((entry == NULL) || (sWordHitboxCount >= MMCHT_MAX_WORD_HITBOXES)) return;
    box = &sWordHitboxes[sWordHitboxCount++];
    box->entry = entry;
    box->x = x;
    box->y = y;
    box->width = width;
    box->height = height;
}

static void mmcht_finish_word_frame(void) {
    u32 i;
    if (!sWordHoverUiInitialized) return;
    if (sHoveredWordSlot >= sWordHitboxCount) sHoveredWordSlot = -1;

    recompui_open_context(sWordHoverContext);
    for (i = 0; i < MMCHT_MAX_WORD_HITBOXES; i++) {
        RecompuiResource hitbox = sWordHoverButtons[i];
        if (i < sWordHitboxCount) {
            const CnWordHitbox* box = &sWordHitboxes[i];
            float left = ((float)box->x * 100.0f) / CN_SCREEN_WIDTH;
            float top = ((float)box->y * 100.0f) / 240.0f;
            float width = ((float)box->width * 100.0f) / CN_SCREEN_WIDTH;
            float height = ((float)box->height * 100.0f) / 240.0f;
            recompui_set_left(hitbox, left, UNIT_PERCENT);
            recompui_set_top(hitbox, top, UNIT_PERCENT);
            recompui_set_width(hitbox, width, UNIT_PERCENT);
            recompui_set_height(hitbox, height, UNIT_PERCENT);
            recompui_set_visibility(hitbox, VISIBILITY_VISIBLE);
        } else {
            recompui_set_visibility(hitbox, VISIBILITY_HIDDEN);
        }
    }
    recompui_close_context(sWordHoverContext);

    if (sWordHitboxCount > 0) {
        if (!sWordHoverUiShown) {
            recompui_show_context(sWordHoverContext);
            sWordHoverUiShown = true;
        }
    } else {
        mmcht_hide_word_context();
    }
}

static s16 cn_draw_tooltip_latin(Gfx** gfxP, const char* text, s16 x, s16 y,
                                 s16 glyphSize, s16 advance, Color_RGB8 color) {
    s16 startX = x;
    if (text == NULL) return x;
    while (*text != '\0') {
        const u8* glyph;
        if (*text == ' ') {
            x += (advance > 4) ? (advance - 2) : advance;
            text++;
            continue;
        }
        glyph = cn_find_pinyin_glyph(*text);
        if (glyph != NULL) {
            cn_draw_glyph_subpixel(gfxP, glyph, x, y, glyphSize, 0, color, 255, true);
        }
        x += advance;
        text++;
    }
    return (x > startX) ? x : startX;
}

static void cn_draw_word_tooltip(Gfx** gfxP) {
    static const Color_RGB8 hanziColor = { 255, 245, 217 };
    static const Color_RGB8 pinyinColor = { 176, 213, 255 };
    static const Color_RGB8 meaningColor = { 255, 255, 255 };
    const CnWordHitbox* box;
    const CnWordEntry* entry;
    const s16 panelWidth = MMCHT_TOOLTIP_WIDTH;
    const s16 panelHeight = MMCHT_TOOLTIP_HEIGHT;
    s16 left, top, x, y;
    s16 i;
    const char* meaning;
    u16 meaningLength = 0;

    if ((sHoveredWordSlot < 0) || (sHoveredWordSlot >= sWordHitboxCount)) return;
    box = &sWordHitboxes[sHoveredWordSlot];
    entry = box->entry;
    if (entry == NULL) return;

    left = box->x;
    if (left + panelWidth > 316) left = 316 - panelWidth;
    if (left < 4) left = 4;
    top = box->y - panelHeight - 4;
    if (top < 4) top = box->y + box->height + 4;
    if (top + panelHeight > 236) top = 236 - panelHeight;

    {
        Gfx* gfx = *gfxP;
        gDPPipeSync(gfx++);
        gDPSetCycleType(gfx++, G_CYC_1CYCLE);
        gDPSetRenderMode(gfx++, G_RM_XLU_SURF, G_RM_XLU_SURF2);
        gDPSetCombineMode(gfx++, G_CC_PRIMITIVE, G_CC_PRIMITIVE);
        gDPSetPrimColor(gfx++, 0, 0, 162, 128, 70, 245);
        gDPFillRectangle(gfx++, left, top, left + panelWidth, top + panelHeight);
        gDPSetPrimColor(gfx++, 0, 0, 9, 12, 18, 245);
        gDPFillRectangle(gfx++, left + 2, top + 2, left + panelWidth - 2, top + panelHeight - 2);
        gDPPipeSync(gfx++);
        gDPSetCombineLERP(gfx++, 0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0,
                          0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0);
        gDPSetTextureFilter(gfx++, G_TF_BILERP);
        *gfxP = gfx;
    }

    x = left + 8;
    y = top + 5;
    for (i = 0; i < entry->length; i++) {
        const u8* glyph = cn_find_glyph(entry->hanzi[i]);
        if (glyph != NULL) cn_draw_glyph(gfxP, glyph, x, y, 11, hanziColor, 255, true);
        x += 12;
    }

    x = left + 8;
    cn_draw_tooltip_latin(gfxP, entry->pinyin, x, top + 20, 7, 7, pinyinColor);

    meaning = entry->meaning;
    while (meaning[meaningLength] != '\0') meaningLength++;
    x = left + 8;
    y = top + 33;
    for (i = 0; i < meaningLength; i++) {
        if ((i == 38) || (i == 76)) {
            x = left + 8;
            y += 8;
        }
        if (y > top + panelHeight - 6) break;
        {
            char character[2] = { meaning[i], '\0' };
            cn_draw_tooltip_latin(gfxP, character, x, y, 6, 6, meaningColor);
        }
        x += 6;
    }
}
'''


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mod-dir", required=True, type=Path)
    mod_dir = parser.parse_args().mod_dir.resolve()
    source_path = mod_dir / "src" / "chinese_text.c"
    source = source_path.read_text(encoding="utf-8")

    if "MMCHT_HOVER_DICTIONARY_PATCH" in source:
        print("Hover dictionary source patch already applied.")
        return

    source = replace_once(source, '#include <string.h>\n',
                          '#include <string.h>\n#include "recompui.h"\n',
                          "include RecompUI API")
    source = replace_once(
        source,
        '#include "generated/pinyin_data.inc"\n',
        '#include "generated/pinyin_data.inc"\n'
        'typedef struct { u16 hanzi[8]; u8 length; const char* pinyin; const char* meaning; } CnWordEntry;\n'
        '#include "generated/vocabulary_data.inc"\n',
        "include generated contextual vocabulary",
    )

    insert_at = "static void cn_draw_page(PlayState* play, Gfx** gfxP) {"
    source = replace_once(source, insert_at, HOVER_TYPES + "\n" + insert_at,
                          "insert hover dictionary implementation")

    start = source.index(insert_at)
    end = source.index("static bool cn_message_draws_text_this_frame", start)
    chunk = source[start:end]

    chunk = replace_once(
        chunk,
        "    s32 pinyinLength = 0;\n",
        "    s32 pinyinLength = 0;\n    u16 wordSkipUntil = 0;\n",
        "declare word segmentation state",
    )
    chunk = replace_once(
        chunk,
        "    y = cn_page_y(msgCtx, page);\n",
        "    y = cn_page_y(msgCtx, page);\n    mmcht_begin_word_frame(msgCtx->currentTextId, pageIndex);\n",
        "begin hover frame",
    )
    chunk = replace_once(
        chunk,
        "        u16 command = gCnCommands[page->commandOffset + i];\n",
        "        u16 command = gCnCommands[page->commandOffset + i];\n"
        "        const CnWordEntry* matchedWord = NULL;\n"
        "        u8 matchedWordLength = 0;\n"
        "        if ((i >= wordSkipUntil) && (command >= 0x3400) && (command <= 0x9FFF)) {\n"
        "            matchedWord = cn_find_word(&gCnCommands[page->commandOffset + i],\n"
        "                                       page->commandCount - i, &matchedWordLength);\n"
        "            if ((matchedWord != NULL) && ((i + matchedWordLength) <= commandLimit)) {\n"
        "                mmcht_add_word_hitbox(x, y, matchedWordLength * glyphSize, glyphSize, matchedWord);\n"
        "                wordSkipUntil = i + matchedWordLength;\n"
        "            } else {\n"
        "                matchedWord = NULL;\n"
        "                matchedWordLength = 1;\n"
        "                wordSkipUntil = i + 1;\n"
        "            }\n"
        "        }\n",
        "match contextual word and register hover target",
    )

    old_pinyin = r'''        if (cn_pinyin_enabled() && (command >= 0x3400) && (command <= 0x9FFF)) {
            const char* syllable = cn_find_pinyin(command);
            if (syllable != NULL) {
                s32 length = 0;
                while (syllable[length] != '\0') length++;
                if ((pinyinLength + length + 2) < (s32)sizeof(pinyinText)) {
                    if (pinyinLength > 0) pinyinText[pinyinLength++] = ' ';
                    memcpy(&pinyinText[pinyinLength], syllable, length);
                    pinyinLength += length;
                    pinyinText[pinyinLength] = '\0';
                }
            }
        }
'''
    new_pinyin = r'''        if (cn_pinyin_enabled() && (matchedWordLength > 0) &&
            (command >= 0x3400) && (command <= 0x9FFF)) {
            const char* syllable = (matchedWord != NULL) ?
                                       matchedWord->pinyin : cn_find_pinyin(command);
            if (syllable != NULL) {
                s32 length = 0;
                while (syllable[length] != '\0') length++;
                if ((pinyinLength + length + 2) < (s32)sizeof(pinyinText)) {
                    if (pinyinLength > 0) pinyinText[pinyinLength++] = ' ';
                    memcpy(&pinyinText[pinyinLength], syllable, length);
                    pinyinLength += length;
                    pinyinText[pinyinLength] = '\0';
                }
            }
        }
'''
    chunk = replace_once(chunk, old_pinyin, new_pinyin, "use word-level pinyin")
    chunk = replace_once(
        chunk,
        "    if (pinyinLength > 0) cn_draw_pinyin_panel(gfxP, msgCtx, pinyinText);\n",
        "    mmcht_finish_word_frame();\n"
        "    if (pinyinLength > 0) cn_draw_pinyin_panel(gfxP, msgCtx, pinyinText);\n"
        "    cn_draw_word_tooltip(gfxP);\n",
        "finish hover boxes and render word tooltip",
    )
    source = source[:start] + chunk + source[end:]

    source = replace_once(
        source,
        "    sChineseEnabled = chinese;\n",
        "    sChineseEnabled = chinese;\n    if (!chinese) mmcht_hide_word_context();\n",
        "hide tooltip on English switch",
    )
    source = replace_once(
        source,
        "    sNtildeWasDown = ntildeDown;\n",
        "    sNtildeWasDown = ntildeDown;\n"
        "    if (!sChineseEnabled || (play->msgCtx.msgLength == 0)) mmcht_hide_word_context();\n",
        "hide tooltip when no Chinese dialogue is active",
    )
    source = replace_once(
        source,
        "    sChineseEnabled = (mmcht_load_language() != 0);\n",
        "    sChineseEnabled = (mmcht_load_language() != 0);\n    mmcht_setup_word_hover_ui();\n",
        "initialize hover UI",
    )

    source = source.rstrip() + "\n\n/* MMCHT_HOVER_DICTIONARY_PATCH */\n"
    source_path.write_text(source, encoding="utf-8", newline="\n")
    print("Patched word-level pinyin and mouse-hover glossary into Chinese dialogue rendering.")


if __name__ == "__main__":
    main()
