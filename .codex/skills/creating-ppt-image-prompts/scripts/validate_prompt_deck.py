#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

REQUIRED_BLOCKS = ["【生成提示词】", "【本页文字】", "【页面类型】", "【版式分组】"]
FORBIDDEN_GEOMETRY = ["向下平移", "向上平移", "整体平移", "裁切图片", "缩放图片", "扩展画布", "顶部补白"]
TITLELESS_REQUIRED = ["不生成", "标题", "正文"]
NO_FRAME_TERMS = ["无框", "不得绘制", "不是一个可见", "连续"]


def bundled_styles() -> set[str]:
    styles_dir = Path(__file__).resolve().parent.parent / "references" / "styles"
    return {path.stem for path in styles_dir.glob("*.md")}


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    errors: list[str] = []
    pages = list(re.finditer(r"(?m)^## 第\s*(\d+)\s*页\s*·\s*(.+)$", text))
    if not pages:
        return ["未找到任何页标题：需要使用 `## 第 N 页 · 页面名称`。"]
    nums = [int(m.group(1)) for m in pages]
    if nums != list(range(1, len(nums) + 1)):
        errors.append(f"页码不连续：{nums}")

    for i, match in enumerate(pages):
        start = match.start()
        end = pages[i + 1].start() if i + 1 < len(pages) else len(text)
        block = text[start:end]
        page = int(match.group(1))
        for required in REQUIRED_BLOCKS:
            if required not in block:
                errors.append(f"第{page}页缺少 {required}")

    expected_match = re.search(r"预计页数[：:]\s*(\d+)", text)
    if expected_match and int(expected_match.group(1)) != len(pages):
        errors.append(f"预计页数为{expected_match.group(1)}，实际定义{len(pages)}页")

    style_match = re.search(r"视觉风格[：:]\s*([^\s]+)", text)
    source_match = re.search(r"风格来源[：:]\s*([^\r\n]+)", text)
    if not style_match:
        errors.append("缺少视觉风格")
    elif style_match.group(1) not in bundled_styles():
        source = source_match.group(1).strip().lower() if source_match else ""
        if source not in {"user-reference", "hybrid"}:
            errors.append(f"未知视觉风格：{style_match.group(1)}")

    profile_match = re.search(r"风格档案[：:]\s*([^\r\n]+)", text)
    if style_match and style_match.group(1) in bundled_styles():
        expected_profile = f"references/styles/{style_match.group(1)}.md"
        if not profile_match:
            errors.append("缺少风格档案")
        elif profile_match.group(1).strip().replace("\\", "/") != expected_profile:
            errors.append(f"风格档案与视觉风格不匹配：应为 {expected_profile}")

    mode_titleless = bool(re.search(r"文字模式[：:]\s*titleless-body", text, re.I))
    if mode_titleless:
        joined = " ".join(text.split())
        if not all(term in joined for term in TITLELESS_REQUIRED):
            errors.append("titleless-body 缺少“不生成标题但保留正文”的明确要求")
        if not any(term in joined for term in NO_FRAME_TERMS):
            errors.append("titleless-body 缺少标题留白区无框约束")
        if re.search(r"标题框区域|顶部标题框|绘制标题框", text):
            errors.append("发现可能诱导模型绘制可见框体的“标题框”表述")

    if "章节页审计" not in text:
        errors.append("缺少章节页审计")

    for forbidden in FORBIDDEN_GEOMETRY:
        if forbidden in text:
            errors.append(f"发现禁止的生成后几何处理：{forbidden}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PPT image prompt deck Markdown")
    parser.add_argument("markdown", type=Path)
    args = parser.parse_args()
    if not args.markdown.is_file():
        print(f"ERROR: file not found: {args.markdown}", file=sys.stderr)
        return 2
    errors = validate(args.markdown)
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK: prompt deck structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
