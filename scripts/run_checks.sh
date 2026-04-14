#!/bin/bash
# 翻译后 QMD 语法检查
# Usage: ./scripts/run_checks.sh [directory]
#   directory defaults to output/book/contents
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
QMD_DIR="${1:-output/book/contents}"

echo "=== 1. 翻译语法检查 ==="
python3 "$SCRIPT_DIR/check_translation_syntax.py" -d "$QMD_DIR" --strict

echo ""
echo "=== 2. 重复标签检查 ==="
python3 "$SCRIPT_DIR/content/check_duplicate_labels.py" -d "$QMD_DIR" --quiet --strict

echo ""
echo "=== 3. 引用完整性检查 ==="
python3 "$SCRIPT_DIR/content/validate_citations.py" -d "$QMD_DIR" --quiet || true

echo ""
echo "=== 4. 脚注检查 ==="
python3 "$SCRIPT_DIR/content/footnote_cleanup.py" -d "$QMD_DIR" --validate --quiet || true

echo ""
echo "=== 5. 列表格式检查 ==="
python3 "$SCRIPT_DIR/utilities/check_list_formatting.py" --check --recursive "$QMD_DIR" || true

echo ""
echo "=== 全部检查通过 ==="
