@echo off
echo ============================================
echo AutoCAD Plugin Quick Build
echo ============================================
echo.

if "%AUTOCAD_VERSION%"=="" set "AUTOCAD_VERSION=2018"
if "%AUTOCAD_INSTALL_DIR%"=="" set "AUTOCAD_INSTALL_DIR=C:\Program Files\Autodesk\AutoCAD %AUTOCAD_VERSION%"

set MSBUILD="C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"

echo AutoCAD version: %AUTOCAD_VERSION%
echo AutoCAD install dir: %AUTOCAD_INSTALL_DIR%
echo.

echo [Step 1] Restore NuGet packages...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /t:Restore /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%" /v:minimal

echo.
echo [Step 2] Build project...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%" /v:detailed > build_output.txt 2>&1

echo.
echo Build output saved to: build_output.txt
echo.
type build_output.txt
echo.

if exist CADDedupPlugin\bin\x64\Release\AutoCAD%AUTOCAD_VERSION%\CADDedupPlugin.dll (
    echo ============================================
    echo SUCCESS! Plugin compiled successfully!
    echo ============================================
    echo.
    echo Output: CADDedupPlugin\bin\x64\Release\AutoCAD%AUTOCAD_VERSION%\CADDedupPlugin.dll
) else (
    echo ============================================
    echo BUILD FAILED - Check build_output.txt
    echo ============================================
)

pause
