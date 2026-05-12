param(
    [string]$SolidWorksInstallDir = "",
    [string]$ProjectPath = ".\SolidWorksMaterialSync\SolidWorksMaterialSync.csproj",
    [string]$OutputDll = "",
    [switch]$RunBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($SolidWorksInstallDir)) {
    $CandidateDirs = @(
        "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS",
        "C:\Program Files\Dassault Systemes\SOLIDWORKS"
    )
    foreach ($Candidate in $CandidateDirs) {
        if (Test-Path (Join-Path $Candidate "SLDWORKS.exe")) {
            $SolidWorksInstallDir = $Candidate
            break
        }
    }
}

$ProjectFullPath = if ([System.IO.Path]::IsPathRooted($ProjectPath)) {
    $ProjectPath
} else {
    Join-Path $Root $ProjectPath
}

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
Write-Host "SolidWorks Material Sync Preflight" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "SolidWorksInstallDir: $SolidWorksInstallDir"
Write-Host "ProjectPath: $ProjectFullPath"
Write-Host ""

if ([string]::IsNullOrWhiteSpace($SolidWorksInstallDir)) {
    Add-Failure "SolidWorks install directory was not provided and no default install was found."
} else {
    Test-RequiredFile (Join-Path $SolidWorksInstallDir "SLDWORKS.exe") "SolidWorks executable"
}

Test-RequiredFile $ProjectFullPath "SolidWorks material sync project"
Test-RequiredFile (Join-Path $Root "WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md") "Windows validation guide"
Test-RequiredFile (Join-Path $Root "MANIFEST.md") "Manifest"

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

if (Test-Path $ProjectFullPath) {
    $ProjectText = Get-Content $ProjectFullPath -Raw
    if ($ProjectText.Contains("SolidWorksMaterialSync")) {
        Add-Pass "Project identifies SolidWorksMaterialSync"
    } else {
        Add-Failure "Project does not identify SolidWorksMaterialSync"
    }
}

if ($RunBuild -and $MsBuild -and $Failures.Count -eq 0) {
    Write-Host ""
    Write-Host "Running build..." -ForegroundColor Cyan
    & $MsBuild $ProjectFullPath /t:Restore /p:Configuration=Release /v:minimal
    if ($LASTEXITCODE -ne 0) {
        Add-Failure "MSBuild restore failed"
    }
    & $MsBuild $ProjectFullPath /p:Configuration=Release /v:minimal
    if ($LASTEXITCODE -ne 0) {
        Add-Failure "MSBuild compile failed"
    } elseif (-not [string]::IsNullOrWhiteSpace($OutputDll)) {
        Test-RequiredFile $OutputDll "Compiled SolidWorks client DLL"
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

Write-Host "Preflight passed. The Windows machine is ready for SolidWorks material sync build/smoke." -ForegroundColor Green
exit 0

