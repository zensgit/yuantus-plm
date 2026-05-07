@echo off
REM ========================================
REM CADDedup插件编译脚本
REM ========================================

echo.
echo ========================================
echo CADDedup插件编译
echo ========================================
echo.

if "%AUTOCAD_VERSION%"=="" set "AUTOCAD_VERSION=2018"
if "%AUTOCAD_INSTALL_DIR%"=="" set "AUTOCAD_INSTALL_DIR=C:\Program Files\Autodesk\AutoCAD %AUTOCAD_VERSION%"

REM 检查MSBuild
set MSBUILD="C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"

if not exist %MSBUILD% (
    echo [错误] 找不到MSBuild
    echo 请安装Visual Studio 2022或更高版本
    pause
    exit /b 1
)

REM 检查AutoCAD SDK
set ACAD_SDK="%AUTOCAD_INSTALL_DIR%"
if not exist %ACAD_SDK% (
    echo [警告] 找不到 AutoCAD %AUTOCAD_VERSION% SDK
    echo 请确保已安装 AutoCAD %AUTOCAD_VERSION% 或设置 AUTOCAD_INSTALL_DIR
    pause
)

echo [信息] 正在编译插件...
echo.

REM 清理旧的构建
if exist "CADDedupPlugin\bin" rmdir /s /q "CADDedupPlugin\bin"
if exist "CADDedupPlugin\obj" rmdir /s /q "CADDedupPlugin\obj"

REM 还原NuGet包
echo [步骤 1/3] 还原NuGet包...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /t:Restore /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%" /v:minimal

if %errorlevel% neq 0 (
    echo [错误] NuGet包还原失败
    pause
    exit /b 1
)

echo.
echo [步骤 2/3] 编译项目...
%MSBUILD% CADDedupPlugin\CADDedupPlugin.csproj /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=%AUTOCAD_VERSION% /p:AutoCADInstallDir="%AUTOCAD_INSTALL_DIR%" /v:minimal

if %errorlevel% neq 0 (
    echo [错误] 编译失败
    pause
    exit /b 1
)

echo.
echo [步骤 3/3] 创建发布包...

REM 创建发布目录
set PUBLISH_DIR=publish
if exist %PUBLISH_DIR% rmdir /s /q %PUBLISH_DIR%
mkdir %PUBLISH_DIR%\CADDedup.bundle\Contents

REM 复制文件
copy CADDedupPlugin\bin\x64\Release\AutoCAD%AUTOCAD_VERSION%\CADDedupPlugin.dll %PUBLISH_DIR%\CADDedup.bundle\Contents\
copy CADDedupPlugin\bin\x64\Release\AutoCAD%AUTOCAD_VERSION%\Newtonsoft.Json.dll %PUBLISH_DIR%\CADDedup.bundle\Contents\
if exist CADDedupPlugin\PackageContents.%AUTOCAD_VERSION%.xml (
    copy CADDedupPlugin\PackageContents.%AUTOCAD_VERSION%.xml %PUBLISH_DIR%\CADDedup.bundle\PackageContents.xml
) else (
    copy CADDedupPlugin\PackageContents.xml %PUBLISH_DIR%\CADDedup.bundle\
)

REM 复制安装脚本
copy install.bat %PUBLISH_DIR%\
copy uninstall.bat %PUBLISH_DIR%\
copy README.md %PUBLISH_DIR%\

echo.
echo ========================================
echo 编译成功！
echo ========================================
echo.
echo 输出目录: %CD%\%PUBLISH_DIR%
echo.
echo 下一步：
echo 1. 查看 %PUBLISH_DIR% 文件夹
echo 2. 运行 install.bat 安装插件
echo 3. 启动AutoCAD测试
echo.
echo ========================================

pause
