@echo off
rem Build the dinput8.dll proxy (x64) in four validation stages with the MSVC compiler only
rem (no Windows SDK, no C runtime):  out\mode0 forward only, mode1 read-only compare,
rem mode2 replace one entry (KR_ONE), mode3 replace all.
setlocal
set VCBIN=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64
cd /d "%~dp0"
if not exist out mkdir out
"%VCBIN%\lib.exe" /nologo /def:kernel32.def /machine:x64 /out:out\kernel32.lib || exit /b 1
for %%M in (0 1 2 3) do (
  if not exist out\mode%%M mkdir out\mode%%M
  "%VCBIN%\cl.exe" /nologo /O2 /W4 /GS- /Zl /DKR_MODE=%%M /c wo3u_kr_dinput8.c /Fo:out\mode%%M\wo3u_kr_dinput8.obj || exit /b 1
  "%VCBIN%\link.exe" /nologo /DLL /NODEFAULTLIB /ENTRY:DllMain /DEF:dinput8.def /MACHINE:X64 /OUT:out\mode%%M\dinput8.dll out\mode%%M\wo3u_kr_dinput8.obj out\kernel32.lib || exit /b 1
)
echo built out\mode0..3\dinput8.dll
