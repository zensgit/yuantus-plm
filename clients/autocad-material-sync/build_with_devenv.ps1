# Build AutoCAD Plugin using MSBuild with proper environment
# PowerShell script to compile with VS Developer environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AutoCAD Plugin 编译脚本 (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$AutoCADVersion = if ($env:AUTOCAD_VERSION) { $env:AUTOCAD_VERSION } else { "2018" }
$AutoCADInstallDir = if ($env:AUTOCAD_INSTALL_DIR) {
    $env:AUTOCAD_INSTALL_DIR
} else {
    "C:\Program Files\Autodesk\AutoCAD $AutoCADVersion"
}

Write-Host "AutoCAD version: $AutoCADVersion" -ForegroundColor White
Write-Host "AutoCAD install dir: $AutoCADInstallDir" -ForegroundColor White
Write-Host ""

# Set up VS Developer environment
$vsPath = "C:\Program Files\Microsoft Visual Studio\2022\Community"
$vsBuildTools = "$vsPath\Common7\Tools\Launch-VsDevShell.ps1"

if (Test-Path $vsBuildTools) {
    Write-Host "✓ 找到 Visual Studio Developer 环境" -ForegroundColor Green
    Write-Host "  正在加载环境变量..." -ForegroundColor Gray

    # Import VS Developer environment
    & $vsBuildTools -SkipAutomaticLocation -Arch amd64 -HostArch amd64

    Write-Host "  环境加载完成" -ForegroundColor Green
} else {
    Write-Host "⚠️  未找到 VS Developer 环境脚本" -ForegroundColor Yellow
    Write-Host "  路径: $vsBuildTools" -ForegroundColor Gray
}

Write-Host ""

# Check MSBuild
$msbuild = "msbuild"
try {
    $msbuildVersion = & $msbuild -version 2>&1 | Select-String "Microsoft" | Select-Object -First 1
    Write-Host "✓ MSBuild 可用: $msbuildVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ MSBuild 不可用" -ForegroundColor Red
    Write-Host "  请在 Developer Command Prompt 中运行此脚本" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check project file
$projectFile = "CADDedupPlugin\CADDedupPlugin.csproj"
if (-not (Test-Path $projectFile)) {
    Write-Host "❌ 找不到项目文件: $projectFile" -ForegroundColor Red
    exit 1
}

Write-Host "✓ 项目文件: $projectFile" -ForegroundColor Green
Write-Host ""

# Clean old build
Write-Host "清理旧的编译输出..." -ForegroundColor Yellow
if (Test-Path "CADDedupPlugin\bin") {
    Remove-Item "CADDedupPlugin\bin" -Recurse -Force
    Write-Host "  已删除 bin 文件夹" -ForegroundColor Gray
}
if (Test-Path "CADDedupPlugin\obj") {
    Remove-Item "CADDedupPlugin\obj" -Recurse -Force
    Write-Host "  已删除 obj 文件夹" -ForegroundColor Gray
}

Write-Host ""

# Restore NuGet packages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "步骤 1/2: 还原 NuGet 包" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $msbuild $projectFile /t:Restore /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=$AutoCADVersion /p:AutoCADInstallDir="$AutoCADInstallDir" /v:minimal

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ NuGet 包还原失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ NuGet 包还原成功" -ForegroundColor Green
Write-Host ""

# Build project
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "步骤 2/2: 编译项目" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $msbuild $projectFile /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=$AutoCADVersion /p:AutoCADInstallDir="$AutoCADInstallDir" /v:normal

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ 编译失败" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "可能的原因:" -ForegroundColor Yellow
    Write-Host "  1. AutoCAD DLL 路径不正确" -ForegroundColor White
    Write-Host "  2. 缺少必要的引用" -ForegroundColor White
    Write-Host "  3. 代码中有错误" -ForegroundColor White
    Write-Host ""
    Write-Host "建议操作:" -ForegroundColor Yellow
    Write-Host "  • 使用 Visual Studio 2022 打开项目" -ForegroundColor White
    Write-Host "  • 检查 '引用' 中的 AutoCAD DLL" -ForegroundColor White
    Write-Host "  • 查看详细错误信息" -ForegroundColor White
    Write-Host ""
    Write-Host "参考文档: WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ 编译成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check output files
$outputDir = "CADDedupPlugin\bin\x64\Release\AutoCAD$AutoCADVersion"
if (Test-Path "$outputDir\CADDedupPlugin.dll") {
    Write-Host "输出文件:" -ForegroundColor White
    Write-Host "  ✓ CADDedupPlugin.dll" -ForegroundColor Green

    $dllInfo = Get-Item "$outputDir\CADDedupPlugin.dll"
    Write-Host "    大小: $([math]::Round($dllInfo.Length / 1KB, 2)) KB" -ForegroundColor Gray
    Write-Host "    路径: $($dllInfo.FullName)" -ForegroundColor Gray

    if (Test-Path "$outputDir\Newtonsoft.Json.dll") {
        Write-Host "  ✓ Newtonsoft.Json.dll" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  输出文件未找到: $outputDir\CADDedupPlugin.dll" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "下一步" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 运行安装脚本:" -ForegroundColor White
Write-Host "   .\install.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. 启动 AutoCAD $AutoCADVersion" -ForegroundColor White
Write-Host ""
Write-Host "3. 测试插件 (参考 WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md)" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
