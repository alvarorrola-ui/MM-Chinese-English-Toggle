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

static bool cn_word_hover_enabled(void) {
    return recomp_get_config_u32("word_dictionary") == 1;
}

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
static float sWordScreenWidth = 320.0f;
static float sWordScreenHeight = 240.0f;
static float sWordClientWidth = 320.0f;
static float sWordClientHeight = 240.0f;

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
    if (sWordHoverUiInitialized || !cn_word_hover_enabled()) return;

    sWordHoverContext = recompui_create_context();
    if (sWordHoverContext == RECOMPUI_NULL_CONTEXT) return;
    recompui_open_context(sWordHoverContext);
    sWordHoverRoot = recompui_context_root(sWordHoverContext);
    /* The root must be the full RecompUI canvas so percentage hitboxes resolve
       against the same window dimensions as the mouse input. */
    recompui_set_position(sWordHoverRoot, POSITION_RELATIVE);
    recompui_set_left(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_top(sWordHoverRoot, 0.0f, UNIT_DP);
    recompui_set_width(sWordHoverRoot, 100.0f, UNIT_PERCENT);
    recompui_set_height(sWordHoverRoot, 100.0f, UNIT_PERCENT);

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
        recompui_set_cursor(hitbox, CURSOR_POINTER);
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

static void mmcht_begin_word_frame(PlayState* play, u16 textId, s16 pageIndex) {
    if (!cn_word_hover_enabled()) { mmcht_hide_word_context(); return; }

    /* Dialogue text is drawn in the game's 2D screen coordinate space, not the
       3D camera viewport. Map that logical screen into RecompUI's full client
       canvas using the same centered, aspect-preserving scale as the game image. */
    (void)play;
    sWordScreenWidth = (gScreenWidth > 0) ? (float)gScreenWidth : 320.0f;
    sWordScreenHeight = (gScreenHeight > 0) ? (float)gScreenHeight : 240.0f;
    sWordClientWidth = (float)mmcht_get_client_width();
    sWordClientHeight = (float)mmcht_get_client_height();
    if (sWordClientWidth < 1.0f) sWordClientWidth = sWordScreenWidth;
    if (sWordClientHeight < 1.0f) sWordClientHeight = sWordScreenHeight;
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
    if (!cn_word_hover_enabled() || (entry == NULL) ||
        (sWordHitboxCount >= MMCHT_MAX_WORD_HITBOXES)) return;
    box = &sWordHitboxes[sWordHitboxCount++];
    box->entry = entry;
    box->x = x;
    box->y = y;
    box->width = width;
    box->height = height;
}

static void mmcht_finish_word_frame(void) {
    u32 i;
    if (!cn_word_hover_enabled() || !sWordHoverUiInitialized) { mmcht_hide_word_context(); return; }
    if (sHoveredWordSlot >= sWordHitboxCount) sHoveredWordSlot = -1;

    recompui_open_context(sWordHoverContext);
    for (i = 0; i < MMCHT_MAX_WORD_HITBOXES; i++) {
        RecompuiResource hitbox = sWordHoverButtons[i];
        if (i < sWordHitboxCount) {
            const CnWordHitbox* box = &sWordHitboxes[i];
            /* box coordinates already belong to the 2D dialogue renderer. Do
               not add the 3D camera viewport origin or scale by its dimensions. */
            float gameLeft = (float)box->x;
            float gameTop = (float)box->y;
            float gameWidth = (float)box->width;
            float gameHeight = (float)box->height;
            float scaleX = sWordClientWidth / sWordScreenWidth;
            float scaleY = sWordClientHeight / sWordScreenHeight;
            float scale = (scaleX < scaleY) ? scaleX : scaleY;
            float displayedWidth = sWordScreenWidth * scale;
            float displayedHeight = sWordScreenHeight * scale;
            float letterboxLeft = (sWordClientWidth - displayedWidth) * 0.5f;
            float letterboxTop = (sWordClientHeight - displayedHeight) * 0.5f;
            float left = ((letterboxLeft + gameLeft * scale) * 100.0f) / sWordClientWidth;
            float top = ((letterboxTop + gameTop * scale) * 100.0f) / sWordClientHeight;
            float width = (gameWidth * scale * 100.0f) / sWordClientWidth;
            float height = (gameHeight * scale * 100.0f) / sWordClientHeight;
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

/*
 * Glyphs are stored in square atlas tiles, but their visible ink is centered
 * inside each tile. Advance by the measured font width (plus a small tracking
 * allowance), not by the whole tile: this keeps letters within a word together
 * while retaining a little breathing room. Transparent tile overlap is safe.
 */
static s16 cn_pinyin_glyph_advance(char character, s16 glyphSize) {
    u32 i;
    for (i = 0; i < sizeof(gCnPinyinGlyphCharacters) - 1; i++) {
        if (gCnPinyinGlyphCharacters[i] == character) {
            s16 advance =
                (s16)((gCnPinyinGlyphWidthPercent[i] * glyphSize + 99) / 100);
            /* Font advance already includes the glyph's natural side bearing.
               Do not add artificial per-letter tracking here. */
            if (advance < 3) advance = 3;
            if (advance > glyphSize) advance = glyphSize;
            return advance;
        }
    }
    return glyphSize;
}

static s16 cn_tooltip_word_width(const char* text, s16 glyphSize) {
    s16 width = 0;
    while ((text != NULL) && (*text != '\0') && (*text != ' ')) {
        width += cn_pinyin_glyph_advance(*text, glyphSize);
        text++;
    }
    return width;
}

static s16 cn_draw_tooltip_latin(Gfx** gfxP, const char* text, s16 x, s16 y,
                                 s16 glyphSize, s16 spaceAdvance,
                                 Color_RGB8 color) {
    s16 startX = x;
    if (text == NULL) return x;
    while (*text != '\0') {
        const u8* glyph;
        if (*text == ' ') {
            x += spaceAdvance;
            text++;
            continue;
        }
        glyph = cn_find_pinyin_glyph(*text);
        if (glyph != NULL) {
            cn_draw_glyph_subpixel(gfxP, glyph, x, y, glyphSize, 0, color, 255, false);
        }
        x += cn_pinyin_glyph_advance(*text, glyphSize);
        text++;
    }
    return (x > startX) ? x : startX;
}

static s16 cn_tooltip_wrapped_metrics(const char* text, s16 maxWidth,
                                      s16 glyphSize, s16 spaceAdvance,
                                      s16* widestLine) {
    s16 lines = 1;
    s16 currentWidth = 0;
    s16 widest = 0;
    const char* cursor = text;

    while ((cursor != NULL) && (*cursor != '\0')) {
        s16 wordLength = 0;
        s16 wordWidth;
        while ((cursor[wordLength] != '\0') && (cursor[wordLength] != ' ')) wordLength++;
        if (wordLength == 0) { cursor++; continue; }
        wordWidth = cn_tooltip_word_width(cursor, glyphSize);
        if ((currentWidth > 0) &&
            (currentWidth + spaceAdvance + wordWidth > maxWidth)) {
            if (currentWidth > widest) widest = currentWidth;
            lines++;
            currentWidth = wordWidth;
        } else {
            if (currentWidth > 0) currentWidth += spaceAdvance;
            currentWidth += wordWidth;
        }
        cursor += wordLength;
        if (*cursor == ' ') cursor++;
    }
    if (currentWidth > widest) widest = currentWidth;
    if (widestLine != NULL) *widestLine = widest;
    return lines;
}

static void cn_draw_tooltip_wrapped(Gfx** gfxP, const char* text, s16 x, s16 y,
                                    s16 maxWidth, s16 spaceAdvance,
                                    s16 lineHeight, s16 glyphSize, Color_RGB8 color) {
    const char* cursor = text;
    s16 currentX = 0;
    s16 currentY = 0;

    while ((cursor != NULL) && (*cursor != '\0')) {
        s16 wordLength = 0;
        s16 i;
        s16 wordWidth;
        while ((cursor[wordLength] != '\0') && (cursor[wordLength] != ' ')) wordLength++;
        if (wordLength == 0) { cursor++; continue; }
        wordWidth = cn_tooltip_word_width(cursor, glyphSize);
        if ((currentX > 0) && (currentX + spaceAdvance + wordWidth > maxWidth)) {
            currentX = 0;
            currentY += lineHeight;
        } else if (currentX > 0) {
            currentX += spaceAdvance;
        }
        for (i = 0; i < wordLength; i++) {
            const u8* glyph = cn_find_pinyin_glyph(cursor[i]);
            if (glyph != NULL) {
                cn_draw_glyph_subpixel(gfxP, glyph, x + currentX, y + currentY,
                                       glyphSize, 0, color, 255, false);
            }
            currentX += cn_pinyin_glyph_advance(cursor[i], glyphSize);
        }
        cursor += wordLength;
        if (*cursor == ' ') cursor++;
    }
}

static void cn_draw_word_tooltip(Gfx** gfxP) {
    static const Color_RGB8 hanziColor = { 250, 243, 222 };
    static const Color_RGB8 pinyinColor = { 151, 197, 231 };
    static const Color_RGB8 meaningColor = { 226, 231, 236 };
    const CnWordHitbox* box;
    const CnWordEntry* entry;
    const s16 padding = 7;
    const s16 screenWidth = (gScreenWidth > 0) ? (s16)gScreenWidth : CN_SCREEN_WIDTH;
    const s16 screenHeight = (gScreenHeight > 0) ? (s16)gScreenHeight : 240;
    const s16 maxContentWidth = 120;
    const s16 meaningGlyphSize = 10;
    const s16 meaningSpace = 4;
    const s16 pinyinGlyphSize = 12;
    const s16 pinyinSpace = 9;
    s16 hanziWidth, pinyinWidth, meaningWidth, meaningLines;
    s16 contentWidth, panelWidth, panelHeight;
    s16 left, top, x, y;
    s16 i;

    if ((sHoveredWordSlot < 0) || (sHoveredWordSlot >= sWordHitboxCount)) return;
    box = &sWordHitboxes[sHoveredWordSlot];
    entry = box->entry;
    if (entry == NULL) return;

    hanziWidth = entry->length * 12;
    pinyinWidth = 0;
    for (i = 0; entry->pinyin[i] != '\0'; i++) {
        pinyinWidth += (entry->pinyin[i] == ' ') ?
                           pinyinSpace : cn_pinyin_glyph_advance(entry->pinyin[i], pinyinGlyphSize);
    }
    meaningLines = cn_tooltip_wrapped_metrics(entry->meaning, maxContentWidth,
                                               meaningGlyphSize, meaningSpace, &meaningWidth);
    contentWidth = hanziWidth;
    if (pinyinWidth > contentWidth) contentWidth = pinyinWidth;
    if (meaningWidth > contentWidth) contentWidth = meaningWidth;
    if (contentWidth > maxContentWidth) contentWidth = maxContentWidth;
    if (contentWidth < 62) contentWidth = 62;

    /* Re-measure using the final card width; otherwise the drawn text can wrap
       to more lines than the height calculation reserved for it. */
    meaningLines = cn_tooltip_wrapped_metrics(entry->meaning, contentWidth,
                                               meaningGlyphSize, meaningSpace, &meaningWidth);

    panelWidth = contentWidth + padding * 2;
    panelHeight = 4 + 12 + 2 + 12 + 3 + (meaningLines * 12) + 5;
    if (panelWidth > 150) panelWidth = 150;

    /* Anchor to the hovered word and clamp to the actual logical render size.
       Widescreen/expanded HUD modes can be wider than the original 320-pixel UI. */
    left = box->x + (box->width / 2) - (panelWidth / 2);
    if (left < 3) left = 3;
    if (left + panelWidth > screenWidth - 3) left = screenWidth - panelWidth - 3;

    top = box->y - panelHeight - 7;
    if (top < 4) top = box->y + box->height + 5;
    if (top + panelHeight > screenHeight - 4) top = screenHeight - panelHeight - 4;
    if (top < 3) top = 3;

    {
        Gfx* gfx = *gfxP;
        /* A restrained underline makes the actual hit target visible. */
        gDPPipeSync(gfx++);
        gDPSetCycleType(gfx++, G_CYC_1CYCLE);
        gDPSetRenderMode(gfx++, G_RM_XLU_SURF, G_RM_XLU_SURF2);
        gDPSetCombineMode(gfx++, G_CC_PRIMITIVE, G_CC_PRIMITIVE);
        gDPSetPrimColor(gfx++, 0, 0, 91, 151, 164, 175);
        gDPFillRectangle(gfx++, box->x, box->y + box->height + 1,
                         box->x + box->width, box->y + box->height + 2);
        gDPSetCycleType(gfx++, G_CYC_1CYCLE);
        gDPSetRenderMode(gfx++, G_RM_XLU_SURF, G_RM_XLU_SURF2);
        gDPSetCombineMode(gfx++, G_CC_PRIMITIVE, G_CC_PRIMITIVE);

        /* Soft shadow, fine warm outline, charcoal fill, and a muted teal accent. */
        gDPSetPrimColor(gfx++, 0, 0, 0, 0, 0, 105);
        gDPFillRectangle(gfx++, left + 2, top + 2,
                         left + panelWidth + 2, top + panelHeight + 2);
        gDPSetPrimColor(gfx++, 0, 0, 125, 102, 66, 235);
        gDPFillRectangle(gfx++, left, top, left + panelWidth, top + panelHeight);
        gDPSetPrimColor(gfx++, 0, 0, 15, 19, 25, 238);
        gDPFillRectangle(gfx++, left + 1, top + 1,
                         left + panelWidth - 1, top + panelHeight - 1);
        gDPSetPrimColor(gfx++, 0, 0, 91, 151, 164, 245);
        gDPFillRectangle(gfx++, left + 1, top + 1, left + 3, top + panelHeight - 1);

        gDPPipeSync(gfx++);
        gDPSetCombineLERP(gfx++, 0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0,
                          0, 0, 0, PRIMITIVE, TEXEL0, 0, PRIMITIVE, 0);
        gDPSetTextureFilter(gfx++, G_TF_BILERP);
        *gfxP = gfx;
    }

    x = left + padding + 1;
    y = top + 4;
    for (i = 0; i < entry->length; i++) {
        const u8* glyph = cn_find_glyph(entry->hanzi[i]);
        if (glyph != NULL) cn_draw_glyph(gfxP, glyph, x, y, 12, hanziColor, 255, false);
        x += 12;
    }

    cn_draw_tooltip_latin(gfxP, entry->pinyin, left + padding + 1,
                          top + 18, pinyinGlyphSize, pinyinSpace, pinyinColor);

    cn_draw_tooltip_wrapped(gfxP, entry->meaning, left + padding + 1,
                            top + 33, contentWidth, meaningSpace,
                            12, meaningGlyphSize, meaningColor);
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
                          '#include <string.h>\n#include "recompui.h"\n'
                          'RECOMP_IMPORT(".", u32 mmcht_get_client_width(void));\n'
                          'RECOMP_IMPORT(".", u32 mmcht_get_client_height(void));\n',
                          "include RecompUI and client size APIs")
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
        "    y = cn_page_y(msgCtx, page);\n    mmcht_begin_word_frame(play, msgCtx->currentTextId, pageIndex);\n",
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

    manifest_path = mod_dir / "mod.toml"
    manifest = manifest_path.read_text(encoding="utf-8")
    if 'id = "word_dictionary"' not in manifest:
        manifest += r'''

[[manifest.config_options]]
id = "word_dictionary"
name = "Word Dictionary"
description = "Show Hanzi, contextual pinyin and an English gloss when hovering Chinese dialogue. Enabled by default."
type = "Enum"
options = [ "Off", "On" ]
default = "On"
'''
        manifest_path.write_text(manifest, encoding="utf-8", newline="\n")

    print("Patched word-level pinyin and mouse-hover glossary into Chinese dialogue rendering.")


if __name__ == "__main__":
    main()
