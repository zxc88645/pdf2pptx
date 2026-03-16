# 下載思源黑體（Source Han Sans TC）供 PDF 轉 PPT 使用
# 執行前請在專案根目錄（與 docker-compose.yml 同層）
# 使用方式: .\scripts\download-font.ps1  或  pwsh -File scripts\download-font.ps1

$ErrorActionPreference = 'Stop'
$FontVersion = "2.005R"
$FontZipUrl = "https://github.com/adobe-fonts/source-han-sans/releases/download/$FontVersion/10_SourceHanSansTC.zip"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml'))) {
    $ProjectRoot = Get-Location
}
if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml'))) {
    Write-Error '請在專案根目錄執行（或於含 docker-compose.yml 的 pdf2pptx 目錄）。'
    exit 1
}

$FontsDir = Join-Path $ProjectRoot 'fonts'
$ZipPath = Join-Path $FontsDir 'SourceHanSansTC.zip'
$TargetFont = 'SourceHanSansTC-Regular.otf'

if (-not (Test-Path $FontsDir)) {
    New-Item -ItemType Directory -Path $FontsDir -Force | Out-Null
}

if (Test-Path (Join-Path $FontsDir $TargetFont)) {
    Write-Host "思源黑體已存在: $FontsDir\$TargetFont" -ForegroundColor Green
    Write-Host "若要重新下載，請先刪除 $FontsDir 目錄。" -ForegroundColor Gray
    exit 0
}

Write-Host "下載思源黑體（繁體中文，約 91 MB）..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $FontZipUrl -OutFile $ZipPath -UseBasicParsing
} catch {
    Write-Error "下載失敗: $_"
    exit 1
}

Write-Host "解壓縮..." -ForegroundColor Yellow
$TempExtract = Join-Path $FontsDir 'temp_extract'
if (Test-Path $TempExtract) { Remove-Item -Recurse -Force $TempExtract }
Expand-Archive -Path $ZipPath -DestinationPath $TempExtract -Force

# 找 SourceHanSansTC-Regular.otf（Adobe 結構可能為 OTF/TraditionalChinese/ 或子目錄）
$Found = Get-ChildItem -Path $TempExtract -Recurse -Filter $TargetFont -ErrorAction SilentlyContinue | Select-Object -First 1
if ($Found) {
    Copy-Item $Found.FullName -Destination (Join-Path $FontsDir $TargetFont)
    Write-Host "已儲存: $FontsDir\$TargetFont" -ForegroundColor Green
} else {
    # 若沒有 Regular，就複製第一個 OTF
    $AnyOtf = Get-ChildItem -Path $TempExtract -Recurse -Filter '*.otf' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($AnyOtf) {
        Copy-Item $AnyOtf.FullName -Destination (Join-Path $FontsDir $AnyOtf.Name)
        Write-Host "已儲存: $FontsDir\$($AnyOtf.Name)" -ForegroundColor Green
    } else {
        Write-Error "解壓後找不到 OTF 字體檔。"
        exit 1
    }
}

Remove-Item -Recurse -Force $TempExtract -ErrorAction SilentlyContinue
Remove-Item -Force $ZipPath -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "思源黑體下載完成。" -ForegroundColor Green
Write-Host "安裝方式：" -ForegroundColor Cyan
Write-Host "  1. 雙擊 $FontsDir\$TargetFont → 安裝" -ForegroundColor Gray
Write-Host "  2. 或將字體複製到 設定 > 個人化 > 字體" -ForegroundColor Gray
Write-Host "Docker 使用：可掛載 fonts 目錄或設定 PPT_FONT_PATH=$FontsDir" -ForegroundColor Gray
