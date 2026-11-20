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
    if ((DWORD)(slash - path + 1) + 24 >= path_count) return 0;
    wcscpy_s(slash + 1, path_count - (DWORD)(slash + 1 - path), L"mm_cht_language.state");
    return 1;
}

static uint32_t is_f5_down(void) {
    HWND foreground = GetForegroundWindow();
    DWORD foreground_process = 0;
    if (foreground == NULL) return 0;
    GetWindowThreadProcessId(foreground, &foreground_process);
    if (foreground_process != GetCurrentProcessId()) return 0;
    return (GetAsyncKeyState(VK_F5) & 0x8000) ? 1u : 0u;
}

/* Native library exports use the Recompiled guest-context ABI. */
__declspec(dllexport) void mmcht_f5_down(uint8_t* rdram, recomp_context_prefix* ctx) {
    (void)rdram;
    if (ctx != NULL) ctx->r2 = is_f5_down();
}

__declspec(dllexport) void mmcht_load_language(uint8_t* rdram, recomp_context_prefix* ctx) {
    wchar_t path[MAX_PATH];
    FILE* file;
    int value = 0;
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
