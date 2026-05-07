@echo off
REM ========================================
REM CADDedup插件安装脚本
REM ========================================

echo.
echo ========================================
echo CADDedup插件安装
echo ========================================
echo.

REM 目标目录
set PLUGIN_DIR=%APPDATA%\Autodesk\ApplicationPlugins\CADDedup.bundle

echo [信息] 安装到: %PLUGIN_DIR%
echo.

REM 检查是否已安装
if exist "%PLUGIN_DIR%" (
    echo [警告] 检测到已安装的版本
    echo.
    choice /C YN /M "是否覆盖安装？(Y/N)"
    if errorlevel 2 goto :eof
    if errorlevel 1 (
        echo [信息] 正在卸载旧版本...
        rmdir /s /q "%PLUGIN_DIR%"
    )
)

echo [步骤 1/3] 创建目录...
mkdir "%PLUGIN_DIR%"
mkdir "%PLUGIN_DIR%\Contents"

echo [步骤 2/3] 复制文件...
xcopy /y /i "CADDedup.bundle\Contents\*.*" "%PLUGIN_DIR%\Contents\"
copy /y "CADDedup.bundle\PackageContents.xml" "%PLUGIN_DIR%\"

echo [步骤 3/3] 配置插件...

REM 创建配置目录
set CONFIG_DIR=%APPDATA%\CADDedup
if not exist "%CONFIG_DIR%" (
    mkdir "%CONFIG_DIR%"
)

REM 如果配置文件不存在，创建默认配置
if not exist "%CONFIG_DIR%\config.json" (
    echo { > "%CONFIG_DIR%\config.json"
    echo   "ServerUrl": "http://localhost:8000", >> "%CONFIG_DIR%\config.json"
    echo   "ApiKey": "", >> "%CONFIG_DIR%\config.json"
    echo   "AutoCheckEnabled": true, >> "%CONFIG_DIR%\config.json"
    echo   "SimilarityThreshold": 0.85, >> "%CONFIG_DIR%\config.json"
    echo   "AutoIndex": true, >> "%CONFIG_DIR%\config.json"
    echo   "TimeoutSeconds": 30, >> "%CONFIG_DIR%\config.json"
    echo   "PromptOnHighSimilarity": true, >> "%CONFIG_DIR%\config.json"
    echo   "ShowNotificationOnUnique": false, >> "%CONFIG_DIR%\config.json"
    echo   "PlaySoundOnDuplicate": true, >> "%CONFIG_DIR%\config.json"
    echo   "CheckConnectionOnStartup": true, >> "%CONFIG_DIR%\config.json"
    echo   "Username": "%USERNAME%", >> "%CONFIG_DIR%\config.json"
    echo   "Department": "" >> "%CONFIG_DIR%\config.json"
    echo } >> "%CONFIG_DIR%\config.json"

    echo [完成] 已创建默认配置文件
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 插件已安装到: %PLUGIN_DIR%
echo 配置文件: %CONFIG_DIR%\config.json
echo.
echo 下一步操作：
echo 1. 关闭所有AutoCAD实例（如果正在运行）
echo 2. 启动AutoCAD
echo 3. 输入命令 DEDUPHELP 查看帮助
echo 4. 输入命令 DEDUPCONFIG 配置服务器地址
echo.
echo 注意事项：
echo • 首次使用请配置查重服务器地址
echo • 默认服务器: http://localhost:8000
echo • 如需修改，输入 DEDUPCONFIG 命令
echo.
echo ========================================

pause
