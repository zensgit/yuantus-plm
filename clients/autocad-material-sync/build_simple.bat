@echo off
REM 简化编译脚本 - 直接使用 MSBuild

echo.
echo ============================================
echo AutoCAD Plugin 编译脚本 (简化版)
echo ============================================
echo.

if "%AUTOCAD_VERSION%"=="" set "AUTOCAD_VERSION=2018"
if "%AUTOCAD_INSTALL_DIR%"=="" set "AUTOCAD_INSTALL_DIR=C:\Program Files\Autodesk\AutoCAD %AUTOCAD_VERSION%"

REM 设置 MSBuild 路径
set MSBUILD="C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"

if not exist %MSBUILD% (
    echo [错误] 找不到 MSBuild
    echo 路径: %MSBUILD%
    pause
    exit /b 1
)

echo [信息] MSBuild 找到: %MSBUILD%
echo [信息] AutoCAD 版本: %AUTOCAD_VERSION%
echo [信息] AutoCAD 路径: %AUTOCAD_INSTALL_DIR%
echo.

REM 检查项目文件
if not exist "CADDedupPlugin\CADDedupPlugin.csproj" (
    echo [错误] 找不到项目文件
    pause
    exit /b 1
)

echo [步骤 1/2] 还原 NuGet 包...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /t:Restore /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%"

if %errorlevel% neq 0 (
    echo [错误] NuGet 还原失败
    pause
    exit /b 1
)

echo.
echo [步骤 2/2] 编译项目...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%" /v:minimal

if %errorlevel% neq 0 (
    echo.
    echo [错误] 编译失败
    echo.
    echo 可能的原因:
    echo 1. AutoCAD DLL 路径不正确
    echo 2. 缺少必要的引用
    echo 3. 代码中有错误
    echo.
    echo 建议:
    echo - 检查项目文件中的 AutoCAD DLL 路径
    echo - 使用 Visual Studio 打开项目查看详细错误
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo 编译成功！
echo ============================================
echo.
echo 输出目录: CADDedupPlugin\bin\x64\Release\AutoCAD%AUTOCAD_VERSION%\
echo.

pause
