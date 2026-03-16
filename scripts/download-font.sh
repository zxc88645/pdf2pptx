#!/usr/bin/env bash
# 下載思源黑體（Source Han Sans TC）供 PDF 轉 PPT 使用
# 執行前請在專案根目錄（與 docker-compose.yml 同層）
# 使用方式: ./scripts/download-font.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"  # scripts/.. = project root
if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
  PROJECT_ROOT="$(pwd)"
fi
if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
  echo "請在專案根目錄執行，或於 pdf2pptx 目錄下執行。"
  exit 1
fi

FONT_VERSION="2.005R"
FONT_ZIP_URL="https://github.com/adobe-fonts/source-han-sans/releases/download/${FONT_VERSION}/10_SourceHanSansTC.zip"
FONTS_DIR="$PROJECT_ROOT/fonts"
TARGET_FONT="SourceHanSansTC-Regular.otf"

mkdir -p "$FONTS_DIR"

if [ -f "$FONTS_DIR/$TARGET_FONT" ]; then
  echo "思源黑體已存在: $FONTS_DIR/$TARGET_FONT"
  echo "若要重新下載，請先刪除 $FONTS_DIR 目錄。"
  exit 0
fi

echo "下載思源黑體（繁體中文，約 91 MB）..."
ZIP_PATH="$FONTS_DIR/SourceHanSansTC.zip"
if command -v curl >/dev/null 2>&1; then
  curl -sL -o "$ZIP_PATH" "$FONT_ZIP_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -q -O "$ZIP_PATH" "$FONT_ZIP_URL"
else
  echo "需要 curl 或 wget，請先安裝。"
  exit 1
fi

echo "解壓縮..."
TEMP_EXTRACT="$FONTS_DIR/temp_extract"
rm -rf "$TEMP_EXTRACT"
mkdir -p "$TEMP_EXTRACT"
unzip -q "$ZIP_PATH" -d "$TEMP_EXTRACT"

FOUND="$(find "$TEMP_EXTRACT" -name "$TARGET_FONT" -type f 2>/dev/null | head -1)"
if [ -n "$FOUND" ]; then
  cp "$FOUND" "$FONTS_DIR/$TARGET_FONT"
  echo "已儲存: $FONTS_DIR/$TARGET_FONT"
else
  ANY_OTF="$(find "$TEMP_EXTRACT" -name "*.otf" -type f 2>/dev/null | head -1)"
  if [ -n "$ANY_OTF" ]; then
    cp "$ANY_OTF" "$FONTS_DIR/"
    echo "已儲存: $FONTS_DIR/$(basename "$ANY_OTF")"
  else
    echo "解壓後找不到 OTF 字體檔。"
    rm -rf "$TEMP_EXTRACT" "$ZIP_PATH"
    exit 1
  fi
fi

rm -rf "$TEMP_EXTRACT" "$ZIP_PATH"

echo ""
echo "思源黑體下載完成。"
echo "安裝方式："
echo "  Linux: mkdir -p ~/.local/share/fonts && cp $FONTS_DIR/*.otf ~/.local/share/fonts/ && fc-cache -f"
echo "  macOS: 雙擊字體檔或拖到 /Library/Fonts/"
echo "Docker 使用：可掛載 fonts 目錄或設定 PPT_FONT_PATH=$FONTS_DIR"
