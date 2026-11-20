$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ChineseRoot = Join-Path $RepoRoot "third_party\chinese-localization"
$ModDir = Join-Path $ChineseRoot "CNmod\mod"
$CnmodRoot = Join-Path $ChineseRoot "CNmod"
$DecompRoot = Join-Path $RepoRoot "third_party\mm-decomp"
$RecompModTool = Join-Path $env:RUNNER_TEMP "RecompModTool.exe"
$Clang = "C:\Program Files\LLVM\bin\clang.exe"
$Ld = "C:\Program Files\LLVM\bin\ld.lld.exe"

if (-not (Test-Path (Join-Path $ModDir "src\chinese_text.c"))) {
    throw "Chinese localization submodule missing. Run git submodule update --init --recursive."
}
if (-not (Test-Path (Join-Path $DecompRoot "include\global.h"))) {
    throw "Majora's Mask decompilation submodule is missing."
}
if (-not (Test-Path $RecompModTool)) { throw "RecompModTool.exe is missing." }
foreach ($Tool in @($Clang, $Ld)) {
    if (-not (Test-Path $Tool)) { throw "LLVM tool not found: $Tool" }
}

Write-Host "Patching pinned Chinese localization source..."
python (Join-Path $PSScriptRoot "patch_localizer.py") --mod-dir $ModDir
if ($LASTEXITCODE -ne 0) { throw "Localizer patch step failed." }

Write-Host "Generating tone-marked pinyin lookup..."
python (Join-Path $PSScriptRoot "generate_pinyin.py") --cnmod-root $CnmodRoot --output (Join-Path $ModDir "src\generated\pinyin_data.inc")
if ($LASTEXITCODE -ne 0) { throw "Pinyin generation failed." }

Write-Host "Building MIPS mod and NRM..."
$UpstreamBuild = Join-Path $ModDir "build.ps1"
& $UpstreamBuild -DecompRoot $DecompRoot -Clang $Clang -Ld $Ld -RecompModTool $RecompModTool
if ($LASTEXITCODE -ne 0) { throw "RecompModTool build failed." }

$BuildDir = Join-Path $ModDir "build"
$Nrm = Join-Path $BuildDir "mm_chinese_english_toggle.nrm"
if (-not (Test-Path $Nrm)) { throw "Expected NRM was not produced: $Nrm" }

Write-Host "Building Windows Ñ-key bridge..."
$NativeOutput = Join-Path $BuildDir "mm_cht_input.dll"
cl.exe /nologo /LD /O2 /W4 (Join-Path $RepoRoot "native\mm_cht_input.c") /link user32.lib "/OUT:$NativeOutput"
if ($LASTEXITCODE -ne 0) { throw "Native input bridge build failed." }

$Dist = Join-Path $RepoRoot "dist"
New-Item -ItemType Directory -Force $Dist | Out-Null
Copy-Item $Nrm $Dist -Force
Copy-Item $NativeOutput $Dist -Force
$InstallText = @'
MM Chinese-English Toggle — installation

1. Install the companion Chinese localization texture mod required by this package:
   mm_chinese_localization_texture (version 1.0.0 or newer).
2. Copy BOTH files from this folder into the game's mods folder:
   - mm_chinese_english_toggle.nrm
   - mm_cht_input.dll
3. Enable "MM Chinese-English Toggle" in the in-game mod manager.
4. Start in English. Press Ñ to switch between English and Simplified Chinese.
5. Optional: set Pinyin to On in this mod's configuration. It is Off by default.

The chosen language is stored in mm_cht_language.state beside the DLL. This separate
preference file does not modify the ROM or any game save file.

Windows build only. Target: Majora's Mask: Recompiled 1.2.2.
'@
Set-Content -Path (Join-Path $Dist "INSTALL.txt") -Value $InstallText -Encoding UTF8
$Archive = Join-Path $Dist "MM-Chinese-English-Toggle-Windows.zip"
if (Test-Path $Archive) { Remove-Item $Archive -Force }
Compress-Archive -Path (Join-Path $Dist "*") -DestinationPath $Archive -Force
Write-Host "Build finished: $Archive"
Get-ChildItem $Dist | Select-Object Name, Length
