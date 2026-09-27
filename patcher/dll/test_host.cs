using System;
using System.IO;
using System.Runtime.InteropServices;

// Loads the proxy dinput8.dll from a test folder and calls DirectInput8Create: the call must reach the system
// DirectInput (returns S_OK and an interface), and the patch must skip all entries because this host process
// is not WO3U.exe (log: 0 patched, 27 skipped).
internal static class TestHost
{
    [DllImport("kernel32", SetLastError = true, CharSet = CharSet.Unicode)] static extern IntPtr LoadLibraryW(string path);
    [DllImport("kernel32", CharSet = CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr mod, string name);
    [DllImport("kernel32")] static extern IntPtr GetModuleHandleW(IntPtr name);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int DI8Create(IntPtr inst, uint ver, ref Guid riid, out IntPtr obj, IntPtr outer);

    static int Main(string[] args)
    {
        IntPtr mod = LoadLibraryW(args[0]);
        if (mod == IntPtr.Zero) { Console.WriteLine("load failed " + Marshal.GetLastWin32Error()); return 1; }
        var fn = (DI8Create)Marshal.GetDelegateForFunctionPointer(GetProcAddress(mod, "DirectInput8Create"), typeof(DI8Create));
        Guid iid = new Guid("BF798031-483A-4DA2-AA99-5D64ED369700"); // IID_IDirectInput8A
        IntPtr obj;
        int hr = fn(GetModuleHandleW(IntPtr.Zero), 0x0800, ref iid, out obj, IntPtr.Zero);
        Console.WriteLine("DirectInput8Create hr=0x" + hr.ToString("X8") + " obj=" + (obj != IntPtr.Zero));
        string log = Path.Combine(Path.GetDirectoryName(args[0]), "WO3U_KR_dll.log");
        Console.WriteLine(File.Exists(log) ? File.ReadAllText(log).Trim() : "no log");
        return hr == 0 && obj != IntPtr.Zero ? 0 : 2;
    }
}
