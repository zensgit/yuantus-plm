param(
    [string]$AutoCADVersion = "2018",
    [string]$AutoCADInstallDir = "",
    [switch]$RunBuild
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AutoCADInstallDir)) {
    $AutoCADInstallDir = "C:\Program Files\Autodesk\AutoCAD $AutoCADVersion"
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Join-Path $Root "CADDedupPlugin\CADDedupPlugin.csproj"
$PackageDefault = Join-Path $Root "CADDedupPlugin\PackageContents.xml"
$PackageVersioned = Join-Path $Root "CADDedupPlugin\PackageContents.$AutoCADVersion.xml"
$Failures = New-Object System.Collections.Generic.List[string]

function Add-Failure {
    param([string]$Message)
    $Failures.Add($Message) | Out-Null
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-Pass {
    param([string]$Message)
    Write-Host "[ OK ] $Message" -ForegroundColor Green
}

function Test-RequiredFile {
    param([string]$Path, [string]$Label)
    if (Test-Path $Path) {
        Add-Pass "$Label found: $Path"
    } else {
        Add-Failure "$Label missing: $Path"
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AutoCAD 2018 Material Sync Preflight" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "AutoCADVersion: $AutoCADVersion"
Write-Host "AutoCADInstallDir: $AutoCADInstallDir"
Write-Host ""

Test-RequiredFile $Project "Project"
Test-RequiredFile $PackageDefault "Default PackageContents"
Test-RequiredFile $PackageVersioned "Versioned PackageContents"
Test-RequiredFile (Join-Path $AutoCADInstallDir "acad.exe") "AutoCAD executable"

foreach ($assembly in @("accoremgd.dll", "acdbmgd.dll", "acmgd.dll", "AcWindows.dll", "AdWindows.dll")) {
    Test-RequiredFile (Join-Path $AutoCADInstallDir $assembly) "AutoCAD managed assembly $assembly"
}

$TargetingPack = "C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.6"
Test-RequiredFile $TargetingPack ".NET Framework 4.6 targeting pack"

if (Test-Path $Project) {
    $ProjectText = Get-Content $Project -Raw
    if ($ProjectText.Contains("<AutoCADVersion") -and $ProjectText.Contains(">2018</AutoCADVersion>")) {
        Add-Pass "Project defaults AutoCADVersion to 2018"
    } else {
        Add-Failure "Project does not default AutoCADVersion to 2018"
    }
    if ($ProjectText.Contains("TargetFrameworkVersion") -and $ProjectText.Contains("v4.6")) {
        Add-Pass "Project contains AutoCAD 2018 .NET Framework v4.6 target"
    } else {
        Add-Failure "Project is missing AutoCAD 2018 .NET Framework v4.6 target"
    }
    if ($ProjectText.Contains("`$(AutoCADInstallDir)\accoremgd.dll")) {
        Add-Pass "Project references AutoCAD assemblies through AutoCADInstallDir"
    } else {
        Add-Failure "Project still appears to use fixed AutoCAD assembly paths"
    }
}

if (Test-Path $PackageVersioned) {
    $PackageText = Get-Content $PackageVersioned -Raw
    if ($AutoCADVersion -eq "2018") {
        if ($PackageText.Contains('SeriesMin="R22.0"') -and $PackageText.Contains('SeriesMax="R22.0"')) {
            Add-Pass "AutoCAD 2018 package targets R22.0"
        } else {
            Add-Failure "AutoCAD 2018 package does not target R22.0"
        }
    }
}

$MsBuild = $null
try {
    $MsBuild = (Get-Command msbuild.exe -ErrorAction Stop).Source
} catch {
    $Candidates = @(
        "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
        "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe",
        "C:\Program Files\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
        "C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\MSBuild.exe"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $MsBuild = $Candidate
            break
        }
    }
}

if ($MsBuild) {
    Add-Pass "MSBuild found: $MsBuild"
} else {
    Add-Failure "MSBuild not found. Install Visual Studio or Build Tools with .NET desktop build tools."
}

if ($RunBuild -and $MsBuild -and $Failures.Count -eq 0) {
    Write-Host ""
    Write-Host "Running build..." -ForegroundColor Cyan
    & $MsBuild $Project /t:Restore /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=$AutoCADVersion /p:AutoCADInstallDir="$AutoCADInstallDir" /v:minimal
    if ($LASTEXITCODE -ne 0) {
        Add-Failure "MSBuild restore failed"
    }
    & $MsBuild $Project /p:Configuration=Release /p:Platform=x64 /p:AutoCADVersion=$AutoCADVersion /p:AutoCADInstallDir="$AutoCADInstallDir" /v:minimal
    if ($LASTEXITCODE -ne 0) {
        Add-Failure "MSBuild compile failed"
    } else {
        $OutputDll = Join-Path $Root "CADDedupPlugin\bin\x64\Release\AutoCAD$AutoCADVersion\CADDedupPlugin.dll"
        Test-RequiredFile $OutputDll "Compiled plugin DLL"
    }
}

Write-Host ""
if ($Failures.Count -gt 0) {
    Write-Host "Preflight failed with $($Failures.Count) issue(s)." -ForegroundColor Red
    foreach ($Failure in $Failures) {
        Write-Host "- $Failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Preflight passed. The Windows machine is ready for AutoCAD $AutoCADVersion plugin build/smoke." -ForegroundColor Green
exit 0
