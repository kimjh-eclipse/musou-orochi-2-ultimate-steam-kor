/* Test stand-in for another program's dinput8.dll (e.g. a frame-rate fix). Worst case for chaining: it forwards by
 * loading "dinput8.dll" by bare name, which returns the Korean proxy (already loaded) instead of the system DLL.
 * Leaves marker files so the host test can see that DllMain ran and that the call went through this DLL. */
typedef void *HANDLE;
typedef void *HMODULE;
typedef void *LPVOID;
typedef const void *LPCVOID;
typedef int BOOL;
typedef unsigned long DWORD;
typedef long HRESULT;
typedef void *(__stdcall *FARPROC)(void);
#define WINAPI __stdcall
#define DECL __declspec(dllimport)
#define E_FAIL ((HRESULT)0x80004005L)
#define GENERIC_WRITE 0x40000000UL
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0x80
#define INVALID_HANDLE_VALUE ((HANDLE)(long long)-1)
DECL HMODULE WINAPI LoadLibraryA(const char *name);
DECL FARPROC WINAPI GetProcAddress(HMODULE mod, const char *name);
DECL HANDLE WINAPI CreateFileA(const char *name, DWORD access, DWORD share, void *sa, DWORD disp, DWORD flags, HANDLE tmpl);
DECL BOOL WINAPI WriteFile(HANDLE h, LPCVOID buf, DWORD n, DWORD *written, void *ov);
DECL BOOL WINAPI CloseHandle(HANDLE h);
typedef HRESULT(WINAPI *PFN_DI8Create)(HMODULE, DWORD, LPCVOID, LPVOID *, LPVOID);

static void mark(const char *name)
{
    DWORD w;
    HANDLE h = CreateFileA(name, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    if (h != INVALID_HANDLE_VALUE) { WriteFile(h, "1", 1, &w, 0); CloseHandle(h); }
}

HRESULT WINAPI DirectInput8Create(HMODULE inst, DWORD ver, LPCVOID riid, LPVOID *out, LPVOID outer)
{
    PFN_DI8Create fn;
    mark("fake_mod_called.txt");
    fn = (PFN_DI8Create)GetProcAddress(LoadLibraryA("dinput8.dll"), "DirectInput8Create");
    return fn ? fn(inst, ver, riid, out, outer) : E_FAIL;
}

BOOL WINAPI DllMain(HMODULE inst, DWORD reason, LPVOID reserved)
{
    (void)inst; (void)reserved;
    if (reason == 1) mark("fake_mod_loaded.txt");
    return 1;
}
