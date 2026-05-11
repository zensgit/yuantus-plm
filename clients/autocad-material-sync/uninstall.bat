@echo off
REM ========================================
REM CADDedup插件卸载脚本
REM ========================================

echo.
echo ========================================
echo CADDedup插件卸载
echo ========================================
echo.

set PLUGIN_DIR=%APPDATA%\Autodesk\ApplicationPlugins\CADDedup.bundle
set CONFIG_DIR=%APPDATA%\CADDedup

REM 检查是否安装
if not exist "%PLUGIN_DIR%" (
    echo [信息] 未检测到已安装的插件
    pause
    goto :eof
)

echo 即将卸载CADDedup插件
echo.
echo 插件目录: %PLUGIN_DIR%
echo 配置目录: %CONFIG_DIR%
echo.
choice /C YN /M "确定要卸载吗？(Y/N)"
if errorlevel 2 goto :eof

echo.
echo [步骤 1/2] 删除插件文件...
rmdir /s /q "%PLUGIN_DIR%"

if exist "%PLUGIN_DIR%" (
    echo [错误] 无法删除插件目录
    echo 请确保AutoCAD已关闭
    pause
    goto :eof
)

echo [完成] 插件文件已删除

echo.
choice /C YN /M "是否同时删除配置文件和统计数据？(Y/N)"
if errorlevel 2 goto :skip_config
if errorlevel 1 (
    echo [步骤 2/2] 删除配置和数据...
    if exist "%CONFIG_DIR%" (
        rmdir /s /q "%CONFIG_DIR%"
        echo [完成] 配置和数据已删除
    )
)
goto :done

:skip_config
echo [跳过] 保留配置文件和统计数据

:done
echo.
echo ========================================
echo 卸载完成！
echo ========================================
echo.
echo 插件已从AutoCAD中移除
echo 请重启AutoCAD以使更改生效
echo.
echo ========================================

pause
