#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>

typedef struct {
    uint64_t r0;
    uint64_t r1;
    uint64_t r2;
    uint64_t r3;
    uint64_t r4;
} recomp_context_prefix;

__declspec(dllexport) uint32_t recomp_api_version = 1;

typedef struct {
    DWORD process_id;
    HWND best_window;
    LONG64 best_area;
} mmcht_window_search;

static BOOL CALLBACK mmcht_find_window_callback(HWND window, LPARAM parameter) {
    mmcht_window_search* search = (mmcht_window_search*)parameter;
    DWORD process_id = 0;
    RECT client;
    LONG64 area;
    GetWindowThreadProcessId(window, &process_id);
    if (process_id != search->process_id || !IsWindowVisible(window) ||
        GetWindow(window, GW_OWNER) != NULL) {
        return TRUE;
    }
    if (!GetClientRect(window, &client)) return TRUE;
    area = (LONG64)(client.right - client.left) * (LONG64)(client.bottom - client.top);
    if (area > search->best_area) {
        search->best_area = area;
        search->best_window = window;
    }
    return TRUE;
}

static HWND mmcht_get_game_window(void) {
    HWND foreground = GetForegroundWindow();
    DWORD foreground_process = 0;
    mmcht_window_search search;
    if (foreground != NULL) {
        GetWindowThreadProcessId(foreground, &foreground_process);
        if (foreground_process == GetCurrentProcessId()) return foreground;
    }
    search.process_id = GetCurrentProcessId();
    search.best_window = NULL;
    search.best_area = 0;
    EnumWindows(mmcht_find_window_callback, (LPARAM)&search);
    return search.best_window;
}

static uint32_t mmcht_get_client_dimension(BOOL horizontal) {
    HWND window = mmcht_get_game_window();
    RECT client;
    if (window == NULL || !GetClientRect(window, &client)) return 0;
    return (uint32_t)(horizontal ? (client.right - client.left) :
                                   (client.bottom - client.top));
}

static int get_state_path(wchar_t* path, DWORD path_count) {
    HMODULE module = NULL;
    DWORD length;
    wchar_t* slash;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)(uintptr_t)&recomp_api_version, &module)) return 0;
    length = GetModuleFileNameW(module, path, path_count);
    if (length == 0 || length >= path_count) return 0;
    slash = wcsrchr(path, L'\\');
    if (slash == NULL) slash = wcsrchr(path, L'/');
    if (slash == NULL) return 0;
    if ((DWORD)(slash - path + 1) + 32 >= path_count) return 0;
    wcscpy_s(slash + 1, path_count - (DWORD)(slash + 1 - path), L"mm_cht_language_v2.state");
    return 1;
}

static uint32_t is_ntilde_down(void) {
    HWND foreground = GetForegroundWindow();
    DWORD foreground_process = 0;
    if (foreground == NULL) return 0;
    GetWindowThreadProcessId(foreground, &foreground_process);
    if (foreground_process != GetCurrentProcessId()) return 0;
    return (GetAsyncKeyState(VK_OEM_3) & 0x8000) ? 1u : 0u;
}

/* Native library exports use the Recompiled guest-context ABI. */
__declspec(dllexport) void mmcht_ntilde_down(uint8_t* rdram, recomp_context_prefix* ctx) {
    (void)rdram;
    if (ctx != NULL) ctx->r2 = is_ntilde_down();
}

__declspec(dllexport) void mmcht_load_language(uint8_t* rdram, recomp_context_prefix* ctx) {
    wchar_t path[MAX_PATH];
    FILE* file;
    int value = 1; /* New installs start in Simplified Chinese. */
    (void)rdram;
    if (get_state_path(path, MAX_PATH)) {
        file = _wfopen(path, L"rb");
        if (file != NULL) {
            value = fgetc(file);
            fclose(file);
        }
    }
    if (ctx != NULL) ctx->r2 = (value == 1) ? 1u : 0u;
}

__declspec(dllexport) void mmcht_save_language(uint8_t* rdram, recomp_context_prefix* ctx) {
    wchar_t path[MAX_PATH];
    FILE* file;
    uint8_t value;
    (void)rdram;
    if (ctx == NULL) return;
    value = (ctx->r4 != 0) ? 1u : 0u;
    if (!get_state_path(path, MAX_PATH)) return;
    file = _wfopen(path, L"wb");
    if (file != NULL) {
        (void)fwrite(&value, sizeof(value), 1, file);
        fclose(file);
    }
}

/* Return the active game's client dimensions in pixels. RecompUI uses the same
   swap-chain client area, so these values let the guest align hover targets after
   RT64 letterboxing. */
__declspec(dllexport) void mmcht_get_client_width(uint8_t* rdram, recomp_context_prefix* ctx) {
    (void)rdram;
    if (ctx != NULL) ctx->r2 = mmcht_get_client_dimension(TRUE);
}

__declspec(dllexport) void mmcht_get_client_height(uint8_t* rdram, recomp_context_prefix* ctx) {
    (void)rdram;
    if (ctx != NULL) ctx->r2 = mmcht_get_client_dimension(FALSE);
}
