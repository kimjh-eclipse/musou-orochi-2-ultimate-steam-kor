/*
 * dinput8.dll proxy for the WO3U DE (Steam) Korean patch.
 *
 * WO3U.exe keeps 27 Simplified Chinese message strings (unlimited mode notices, rebirth help, ...) in its own
 * .rdata. The exe file cannot be edited (SteamStub integrity check -> Steam error 51), so this proxy replaces
 * them in memory. All DirectInput calls are forwarded to the system dinput8.dll.
 *
 * KR_MODE (compile-time, staged validation):
 *   0  forward only: log that the game loaded this DLL and called DirectInput8Create
 *   1  read-only compare: log, per entry, whether memory holds the expected Chinese bytes
 *   2  replace entry KR_ONE only (after the full pre-check)
 *   3  replace all entries (after the full pre-check)
 * Pre-check (modes 2/3): the installed LINKIDX_CHS.BIN must be the build the table was generated for (size +
 * CRC32; the Korean bytes are only valid for that font mapping) and every entry must match its expected bytes.
 * Any mismatch -> nothing is written.
 *
 * DllMain only records the module handle. Loading the system DLL and all checks happen on the first
 * DirectInput8Create call (inside the game's own initialisation), never under the loader lock.
 * The report goes to WO3U_KR_dll.log next to this DLL.
 *
 * Built without the Windows SDK or C runtime (see build_dll.cmd).
 */
#ifndef KR_MODE
#define KR_MODE 0
#endif
#ifndef KR_ONE
#define KR_ONE 7
#endif

typedef void *HANDLE;
typedef void *HMODULE;
typedef void *LPVOID;
typedef const void *LPCVOID;
typedef int BOOL;
typedef unsigned long DWORD;
typedef long HRESULT;
typedef unsigned long long SIZE_T;
typedef void *(__stdcall *FARPROC)(void);

#define WINAPI __stdcall
#define DECL __declspec(dllimport)
#define E_FAIL ((HRESULT)0x80004005L)
#define S_FALSE ((HRESULT)1L)
#define PAGE_READWRITE 0x04
#define GENERIC_READ 0x80000000UL
#define GENERIC_WRITE 0x40000000UL
#define FILE_SHARE_READ 1
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0x80
#define INVALID_HANDLE_VALUE ((HANDLE)(long long)-1)
#define DLL_PROCESS_ATTACH 1
#define MAX_PATH 260

DECL unsigned WINAPI GetSystemDirectoryA(char *buf, unsigned size);
DECL HMODULE WINAPI LoadLibraryA(const char *name);
DECL FARPROC WINAPI GetProcAddress(HMODULE mod, const char *name);
DECL HMODULE WINAPI GetModuleHandleA(const char *name);
DECL DWORD WINAPI GetModuleFileNameA(HMODULE mod, char *buf, DWORD size);
DECL BOOL WINAPI VirtualProtect(LPVOID addr, SIZE_T size, DWORD prot, DWORD *old);
DECL SIZE_T WINAPI VirtualQuery(LPCVOID addr, void *info, SIZE_T len);
DECL BOOL WINAPI DisableThreadLibraryCalls(HMODULE mod);
DECL HANDLE WINAPI CreateFileA(const char *name, DWORD access, DWORD share, void *sa, DWORD disp, DWORD flags, HANDLE tmpl);
DECL BOOL WINAPI ReadFile(HANDLE h, LPVOID buf, DWORD n, DWORD *read, void *ov);
DECL BOOL WINAPI WriteFile(HANDLE h, LPCVOID buf, DWORD n, DWORD *written, void *ov);
DECL BOOL WINAPI CloseHandle(HANDLE h);
long _InterlockedExchange(long volatile *target, long value);
#pragma intrinsic(_InterlockedExchange)

#include "strings_table.h"

typedef HRESULT(WINAPI *PFN_DI8Create)(HMODULE, DWORD, LPCVOID, LPVOID *, LPVOID);
typedef HRESULT(WINAPI *PFN_Void)(void);
typedef HRESULT(WINAPI *PFN_GetClassObject)(LPCVOID, LPCVOID, LPVOID *);
typedef LPCVOID(WINAPI *PFN_GetdfDIJoystick)(void);

typedef struct {
    LPVOID BaseAddress, AllocationBase;
    DWORD AllocationProtect;
    unsigned short PartitionId;
    SIZE_T RegionSize;
    DWORD State, Protect, Type;
} MEMINFO;

static HMODULE g_real;
static HMODULE g_self;
static long volatile g_done;

/* ---- tiny helpers (no CRT) ---- */
static char g_log[8192];
static int g_len;
static void lput(const char *s) { while (*s && g_len < (int)sizeof g_log - 1) g_log[g_len++] = *s++; }
static void lnum(unsigned long long v, int base)
{
    char t[24]; int n = 0;
    if (v == 0) t[n++] = '0';
    while (v) { int dgt = (int)(v % base); t[n++] = (char)(dgt < 10 ? '0' + dgt : 'a' + dgt - 10); v /= base; }
    if (base == 16) lput("0x");
    while (n) { char c[2] = {t[--n], 0}; lput(c); }
}
static int mcmp(const unsigned char *a, const unsigned char *b, unsigned n)
{
    unsigned i;
    for (i = 0; i < n; i++) if (a[i] != b[i]) return 1;
    return 0;
}
static void mcpy(unsigned char *d, const unsigned char *s, unsigned n) { unsigned i; for (i = 0; i < n; i++) d[i] = s[i]; }
static int dir_of(HMODULE mod, char *path)
{
    DWORD n = GetModuleFileNameA(mod, path, MAX_PATH);
    int i;
    if (n == 0 || n >= MAX_PATH - 24) return -1;
    for (i = (int)n; i > 0 && path[i - 1] != '\\'; i--) {}
    return i;
}
static void cat(char *d, const char *s) { while (*d) d++; while ((*d++ = *s++)) {} }

static void write_log(void)
{
    char path[MAX_PATH];
    int i = dir_of(g_self, path);
    HANDLE h;
    DWORD w;
    if (i < 0) return;
    path[i] = 0;
    cat(path, "WO3U_KR_dll.log");
    h = CreateFileA(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    if (h == INVALID_HANDLE_VALUE) return;
    WriteFile(h, g_log, (DWORD)g_len, &w, 0);
    CloseHandle(h);
}

static HMODULE real_dll(void)
{
    if (!g_real) {
        char path[MAX_PATH];
        unsigned n = GetSystemDirectoryA(path, MAX_PATH);
        if (n == 0 || n > MAX_PATH - 16) return 0;
        path[n] = 0;
        cat(path, "\\dinput8.dll");
        g_real = LoadLibraryA(path);
    }
    return g_real;
}

static int readable(const unsigned char *p, unsigned n)
{
    MEMINFO mi;
    if (!VirtualQuery(p, &mi, sizeof mi) || mi.State != 0x1000 /* MEM_COMMIT */) return 0;
    return (const unsigned char *)mi.BaseAddress + mi.RegionSize >= p + n && !(mi.Protect & 0x101);
}

/* CRC32 (IEEE) of the installed LINKIDX_CHS.BIN next to the game exe */
static int idx_matches(void)
{
    static unsigned char buf[65536];
    char path[MAX_PATH];
    int i = dir_of(0, path);
    HANDLE h;
    DWORD got, total = 0;
    unsigned crc = 0xFFFFFFFFu;
    if (i < 0) return 0;
    path[i] = 0;
    cat(path, "LINKIDX_CHS.BIN");
    h = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0);
    if (h == INVALID_HANDLE_VALUE) { lput("LINKIDX_CHS.BIN: cannot open\r\n"); return 0; }
    while (ReadFile(h, buf, sizeof buf, &got, 0) && got) {
        DWORD k;
        for (k = 0; k < got; k++) {
            int b;
            crc ^= buf[k];
            for (b = 0; b < 8; b++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1)));
        }
        total += got;
    }
    CloseHandle(h);
    crc ^= 0xFFFFFFFFu;
    lput("LINKIDX_CHS.BIN size "); lnum(total, 10); lput(" crc32 "); lnum(crc, 16);
    lput(total == KR_IDX_SIZE && crc == KR_IDX_CRC32 ? " = table build\r\n" : " != table build (font mapping differs)\r\n");
    return total == KR_IDX_SIZE && crc == KR_IDX_CRC32;
}

static void run_once(void)
{
    char path[MAX_PATH];
    unsigned char *base = (unsigned char *)GetModuleHandleA(0);
    int i, match = 0, written = 0;
    if (_InterlockedExchange(&g_done, 1)) return;

    lput("WO3U_KR dinput8 proxy, mode "); lnum(KR_MODE, 10); lput("\r\n");
    if (GetModuleFileNameA(g_self, path, MAX_PATH)) { lput("proxy: "); lput(path); lput("\r\n"); }
    if (GetModuleFileNameA(0, path, MAX_PATH)) { lput("host:  "); lput(path); lput("\r\n"); }
    lput("exe base "); lnum((unsigned long long)base, 16); lput("\r\n");
    lput(real_dll() ? "system dinput8 loaded\r\n" : "system dinput8 NOT loaded\r\n");
    if (KR_MODE == 0) { write_log(); return; }

    for (i = 0; i < KR_PATCH_COUNT; i++) {
        const KrPatch *p = &KR_PATCHES[i];
        const unsigned char *dst = base + p->rva;
        int ok = readable(dst, p->rlen) && !mcmp(dst, p->expect, p->elen);
        match += ok;
        if (KR_MODE == 1) {
            lput("  #"); lnum(i, 10); lput(" rva "); lnum(p->rva, 16); lput(ok ? " expected bytes\r\n" : " DIFFERENT\r\n");
        }
    }
    lput("pre-check: "); lnum(match, 10); lput("/"); lnum(KR_PATCH_COUNT, 10); lput(" entries hold the expected Chinese bytes\r\n");
    if (KR_MODE == 1) { write_log(); return; }

    if (!idx_matches() || match != KR_PATCH_COUNT) {
        lput("NOT patched: pre-check failed, nothing written\r\n");
        write_log();
        return;
    }
    for (i = 0; i < KR_PATCH_COUNT; i++) {
        const KrPatch *p = &KR_PATCHES[i];
        unsigned char *dst = base + p->rva;
        DWORD old;
        if (KR_MODE == 2 && i != KR_ONE) continue;
        if (!VirtualProtect(dst, p->rlen, PAGE_READWRITE, &old)) { lput("VirtualProtect failed at #"); lnum(i, 10); lput("\r\n"); continue; }
        mcpy(dst, p->repl, p->rlen);
        VirtualProtect(dst, p->rlen, old, &old);
        written++;
    }
    lput("patched "); lnum(written, 10); lput(" entries\r\n");
    write_log();
}

HRESULT WINAPI DirectInput8Create(HMODULE inst, DWORD ver, LPCVOID riid, LPVOID *out, LPVOID outer)
{
    PFN_DI8Create fn;
    run_once();
    fn = (PFN_DI8Create)GetProcAddress(real_dll(), "DirectInput8Create");
    return fn ? fn(inst, ver, riid, out, outer) : E_FAIL;
}

HRESULT WINAPI DllCanUnloadNow(void)
{
    PFN_Void fn = (PFN_Void)GetProcAddress(real_dll(), "DllCanUnloadNow");
    return fn ? fn() : S_FALSE;
}

HRESULT WINAPI DllGetClassObject(LPCVOID clsid, LPCVOID riid, LPVOID *out)
{
    PFN_GetClassObject fn = (PFN_GetClassObject)GetProcAddress(real_dll(), "DllGetClassObject");
    return fn ? fn(clsid, riid, out) : E_FAIL;
}

HRESULT WINAPI DllRegisterServer(void)
{
    PFN_Void fn = (PFN_Void)GetProcAddress(real_dll(), "DllRegisterServer");
    return fn ? fn() : E_FAIL;
}

HRESULT WINAPI DllUnregisterServer(void)
{
    PFN_Void fn = (PFN_Void)GetProcAddress(real_dll(), "DllUnregisterServer");
    return fn ? fn() : E_FAIL;
}

LPCVOID WINAPI GetdfDIJoystick(void)
{
    PFN_GetdfDIJoystick fn = (PFN_GetdfDIJoystick)GetProcAddress(real_dll(), "GetdfDIJoystick");
    return fn ? fn() : 0;
}

BOOL WINAPI DllMain(HMODULE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = inst;
        DisableThreadLibraryCalls(inst);
    }
    return 1;
}
