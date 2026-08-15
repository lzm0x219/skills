#!/usr/bin/env python3
"""Render an eCommerce strategy Markdown file as a shareable report-class PDF."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path

from atomic_output import OutputExistsError, commit_staged_file
from browser_runtime import find_browser
from markdown_security import (
    UnsafeMarkdownError,
    local_resource_base_uri,
    stage_local_resources,
    validate_final_document,
    validate_markdown_for_render,
    validate_rendered_html,
)
from pdf_runtime import RenderRequest, render_pdf
from pdf_styles import CSS_TEMPLATE, FONT_STACK


def strip_frontmatter(text: str) -> str:
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)


def strip_inline_markdown(value: str) -> str:
    value = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    return html.unescape(value).strip()


def escape_css_content(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("<", "\\3C ")
        .replace(">", "\\3E ")
        .replace('"', '\\"')
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\f", " ")
    )


def extract_title_and_meta(md_text: str) -> tuple[str, list[tuple[str, str]], str]:
    """Extract the first H1 and its adjacent metadata quote for the cover."""
    lines = strip_frontmatter(md_text).splitlines()
    title = "商品销售战略报告"
    title_index = None
    for index, line in enumerate(lines):
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            title = strip_inline_markdown(match.group(1))
            title_index = index
            break

    if title_index is not None:
        del lines[title_index]

    meta: list[tuple[str, str]] = []
    scan = title_index if title_index is not None else 0
    while scan < len(lines) and not lines[scan].strip():
        scan += 1
    if scan < len(lines) and lines[scan].lstrip().startswith(">"):
        end = scan
        quote_lines: list[str] = []
        while end < len(lines) and (lines[end].lstrip().startswith(">") or not lines[end].strip()):
            if lines[end].lstrip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[end]).rstrip())
            end += 1
        for item in quote_lines:
            if "：" in item:
                label, value = item.split("：", 1)
                meta.append((label.strip(), value.strip()))
            elif ":" in item:
                label, value = item.split(":", 1)
                meta.append((label.strip(), value.strip()))
            elif item.strip():
                meta.append(("", item.strip()))
        del lines[scan:end]

    while lines and (not lines[0].strip() or lines[0].strip() == "---"):
        lines.pop(0)
    return title, meta, "\n".join(lines)


def add_table_classes(html_body: str) -> str:
    def replace_table(match: re.Match[str]) -> str:
        table_html = match.group(0)
        head = re.search(r"<thead>.*?</thead>", table_html, flags=re.S)
        columns = len(re.findall(r"<th(?:\s[^>]*)?>", head.group(0))) if head else 0
        class_name = f' class="cols-{min(max(columns, 1), 8)}"'
        return table_html.replace("<table>", f"<table{class_name}>", 1)

    return re.sub(r"<table>.*?</table>", replace_table, html_body, flags=re.S)


def wrap_sources_appendix(html_body: str) -> str:
    """Give the source appendix a quieter visual hierarchy than report chapters."""
    match = re.search(
        r'(<h1\s+id="[^"]+">\s*主要资料来源.*?</h1>)',
        html_body,
        flags=re.S,
    )
    if not match:
        return html_body
    return (
        html_body[: match.start()]
        + '<section class="sources-appendix">'
        + html_body[match.start() :]
        + "</section>"
    )


def wrap_executive_summary(html_body: str) -> str:
    """Turn the pre-chapter content into a deliberate summary page."""
    first_chapter = re.search(r"<h1\b[^>]*>.*?</h1>", html_body, flags=re.S)
    if first_chapter is None:
        return html_body
    summary = html_body[: first_chapter.start()]
    if not summary.strip():
        return html_body
    return (
        '<section class="executive-summary">'
        + summary
        + "</section>"
        + html_body[first_chapter.start() :]
    )


def wrap_final_decision(html_body: str) -> str:
    """Turn the final decision chapter into a two-part decision page."""
    headings = list(re.finditer(r"<h1\b[^>]*>.*?</h1>", html_body, flags=re.S))
    for index, match in enumerate(headings):
        label = html.unescape(re.sub(r"<[^>]+>", "", match.group(0))).strip()
        if not label.startswith("最终决策"):
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(html_body)
        display_label = re.sub(r"\s*[（(].*$", "", label).strip()
        display_heading = re.sub(
            r"(?s)(<h1\b[^>]*>).*?(</h1>)",
            lambda heading_match: (
                heading_match.group(1)
                + html.escape(display_label)
                + heading_match.group(2)
            ),
            match.group(0),
            count=1,
        )
        return (
            html_body[: match.start()]
            + '<section class="final-decision">'
            + '<div class="final-decision-header">'
            + '<div class="page-kicker">FINAL DECISION</div>'
            + display_heading
            + "</div>"
            + '<div class="final-decision-body">'
            + html_body[match.end() : end]
            + "</div></section>"
            + html_body[end:]
        )
    return html_body


def add_markdown_heading_ids(md_text: str) -> tuple[str, list[tuple[str, str]]]:
    """Add stable anchors to reader-visible top-level headings only.

    A Markdown heading inside a blockquote begins with ``>`` and is therefore
    intentionally excluded.  This prevents campaign hooks such as ``> # ...``
    from becoming report chapters or reading-guide entries.
    """
    guide: list[tuple[str, str]] = []
    first_h1_seen = False
    counter = 0
    output: list[str] = []
    for line in md_text.splitlines():
        match = re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if not match:
            output.append(line)
            continue
        level = len(match.group(1))
        include = level == 1 or (level == 2 and not first_h1_seen)
        if level == 1:
            first_h1_seen = True
        if not include:
            output.append(line)
            continue
        counter += 1
        anchor = f"section-{counter}"
        label = strip_inline_markdown(match.group(2))
        guide.append((anchor, label))
        output.append(f"{match.group(1)} {match.group(2)} {{#{anchor}}}")
    return "\n".join(output), guide


def meta_html(meta: list[tuple[str, str]]) -> str:
    rows = []
    for label, value in meta:
        label_html = html.escape(label + "：" if label else "")
        rows.append(
            '<div class="cover-meta-row">'
            f'<div class="cover-meta-label">{label_html}</div>'
            f'<div>{html.escape(value)}</div>'
            "</div>"
        )
    return "\n".join(rows)


def build_signature_html() -> str:
    """Return the fixed sell-product-in-china generation notice."""
    return """
<section class="tool-signature">
  <p>本报告由 sell-product-in-china Skill 协助生成</p>
</section>
"""


def build_html(
    md_text: str,
    title_override: str = "",
    subtitle: str = "",
    author: str = "",
    report_date: str = "",
    resource_root: Path | None = None,
    resource_staging_root: Path | None = None,
) -> tuple[str, str]:
    validate_markdown_for_render(md_text, resource_root=resource_root)
    import markdown

    extracted_title, meta, body_md = extract_title_and_meta(md_text)
    title = title_override.strip() or extracted_title
    body_md, guide = add_markdown_heading_ids(body_md)
    html_body = markdown.markdown(
        body_md,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists", "attr_list"],
        output_format="html5",
    )
    resource_paths = validate_rendered_html(html_body, resource_root=resource_root)
    render_resource_root: Path | None = None
    if resource_paths:
        if resource_root is None or resource_staging_root is None:
            raise UnsafeMarkdownError(
                "local images require both a source root and a private staging root"
            )
        stage_local_resources(
            resource_paths,
            resource_root=resource_root,
            staging_root=resource_staging_root,
        )
        render_resource_root = resource_staging_root
    html_body = add_table_classes(html_body)
    html_body = wrap_executive_summary(html_body)
    html_body = wrap_final_decision(html_body)
    html_body = wrap_sources_appendix(html_body)

    if not report_date:
        report_date = date.today().isoformat()
    footer_parts = [part for part in (report_date, author) if part]
    cover_footer = " · ".join(html.escape(part) for part in footer_parts)
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    cover_subtitle = f'<div class="cover-subtitle">{safe_subtitle}</div>' if subtitle else ""
    cover_meta = f'<div class="cover-meta">{meta_html(meta)}</div>' if meta else ""
    footer = f'<div class="cover-footer">{cover_footer}</div>' if cover_footer else ""

    toc_items = "\n".join(
        f'<li><a href="#{anchor}">{html.escape(label)}</a></li>' for anchor, label in guide
    )
    guide_html = ""
    if toc_items:
        guide_html = f"""
<section class="reading-guide">
  <div class="guide-label">READING GUIDE</div>
  <h1>阅读导航</h1>
  <p class="guide-note">从结论进入，再依次查看产品机会、购买人群、销售主张、SKU 与价格、执行路径和最终决策。</p>
  <div class="guide-axis">
    <div>DECIDE</div>
    <div>PROVE</div>
    <div>ACT</div>
  </div>
  <ol class="toc">{toc_items}</ol>
</section>
"""

    signature_html = build_signature_html()

    short_title = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", title).strip()
    header_text = f"{short_title}  |  商品销售战略报告"
    css = CSS_TEMPLATE.replace("FONT_STACK", FONT_STACK).replace(
        "HEADER_TEXT", escape_css_content(header_text)
    )
    resource_base_html = ""
    if render_resource_root is not None:
        resource_base_uri = local_resource_base_uri(render_resource_root)
        resource_base_html = f'  <base href="{html.escape(resource_base_uri, quote=True)}">\n'
    document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{resource_base_html}  <title>{safe_title}</title>
  <style>{css}</style>
</head>
<body>
  <section class="cover">
    <div class="cover-eyebrow">ECOMMERCE STRATEGY REPORT</div>
    <div class="cover-title">{safe_title}</div>
    {cover_subtitle}
    <hr class="cover-divider">
    {cover_meta}
    {footer}
  </section>
  {guide_html}
  <main class="report-body">{html_body}{signature_html}</main>
</body>
</html>
"""
    validate_final_document(document, resource_root=render_resource_root)
    return document, title


def write_text_atomic(path: Path, content: str, *, overwrite: bool) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        commit_staged_file(temporary_path, path, overwrite=overwrite)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def temporary_output_path(output_path: Path) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}-",
        suffix=output_path.suffix,
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    temporary_path.unlink()
    return temporary_path


def _render_report(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    input_path: Path,
    output_path: Path,
    html_output: Path | None,
    resource_staging_root: Path,
) -> int:
    md_text = input_path.read_text(encoding="utf-8")
    try:
        document, title = build_html(
            md_text,
            title_override=args.title,
            subtitle=args.subtitle,
            author=args.author,
            report_date=args.date,
            resource_root=input_path.parent,
            resource_staging_root=resource_staging_root,
        )
    except (ModuleNotFoundError, UnsafeMarkdownError) as error:
        if isinstance(error, ModuleNotFoundError) and error.name != "markdown":
            raise
        parser.error(f"Markdown 渲染准备失败：{error}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if html_output:
        html_path = html_output
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_is_temporary = False
    else:
        html_path = temporary_output_path(
            Path(tempfile.gettempdir()) / f"{output_path.stem}.html"
        )
        html_is_temporary = True
    try:
        write_text_atomic(
            html_path,
            document,
            overwrite=args.overwrite if html_output else False,
        )
    except OutputExistsError as error:
        print(f"[ERROR] {error}", file=os.sys.stderr)
        return 1

    engine = "chrome" if args.engine == "auto" else args.engine
    browser = find_browser(args.chrome) if engine == "chrome" else None
    render_output = temporary_output_path(output_path)
    try:
        result = render_pdf(
            RenderRequest(
                engine=engine,
                html_path=html_path,
                output_path=render_output,
                resource_root=resource_staging_root,
                browser=browser,
            )
        )
        success = result.success
        if not success:
            print(
                f"[WARN] {result.engine} {result.error_kind}: {result.message}",
                file=os.sys.stderr,
            )
        else:
            try:
                commit_staged_file(
                    render_output,
                    output_path,
                    overwrite=args.overwrite,
                )
            except OutputExistsError as error:
                print(f"[ERROR] {error}", file=os.sys.stderr)
                success = False
    finally:
        render_output.unlink(missing_ok=True)
        if html_is_temporary and not args.keep_html:
            html_path.unlink(missing_ok=True)
        elif args.keep_html or html_output:
            print(f"[OK] HTML：{html_path}")

    if not success:
        print(
            "[ERROR] PDF 渲染失败。请安装 Chrome；WeasyPrint 仅在显式指定时使用。",
            file=os.sys.stderr,
        )
        return 1

    print(f"[OK] PDF：{output_path}")
    print(f"[OK] 标题：{title}")
    print(f"[OK] 渲染引擎：{result.engine}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="将商品销售战略 Markdown 导出为报告级 PDF")
    parser.add_argument("input", type=Path, help="输入 Markdown 文件")
    parser.add_argument("output", type=Path, help="输出 PDF 文件")
    parser.add_argument("--title", default="", help="覆盖封面标题")
    parser.add_argument("--subtitle", default="中国市场新品销售策略", help="封面副标题")
    parser.add_argument("--author", default="", help="可选署名")
    parser.add_argument("--date", default="", help="封面日期，默认当天")
    parser.add_argument("--overwrite", action="store_true", help="允许替换已存在的输出 PDF")
    parser.add_argument("--engine", choices=("auto", "chrome", "weasyprint"), default="auto")
    parser.add_argument("--chrome", type=Path, help="Chrome／Chromium 可执行文件")
    parser.add_argument("--html-output", type=Path, help="指定中间 HTML 路径")
    parser.add_argument("--keep-html", action="store_true", help="保留中间 HTML")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    html_output = args.html_output.resolve() if args.html_output else None

    if not input_path.is_file():
        parser.error(f"输入文件不存在：{input_path}")
    if input_path == output_path:
        parser.error("输入 Markdown 与输出 PDF 必须使用不同路径")
    if html_output and html_output in {input_path, output_path}:
        parser.error("输入 Markdown、输出 PDF 与中间 HTML 必须使用不同路径")
    if output_path.exists() and not args.overwrite:
        parser.error(f"输出文件已存在：{output_path}；如已确认替换，请传 --overwrite")
    if html_output and html_output.exists() and not args.overwrite:
        parser.error(f"HTML 文件已存在：{html_output}；如已确认替换，请传 --overwrite")

    if html_output or args.keep_html:
        snapshot_parent = html_output.parent if html_output else output_path.parent
        snapshot_parent.mkdir(parents=True, exist_ok=True)
        resources_directory = Path(
            tempfile.mkdtemp(
                prefix=".sell-product-in-china-resources-",
                dir=snapshot_parent,
            )
        )
        keep_resources = False
        try:
            result = _render_report(
                args,
                parser,
                input_path,
                output_path,
                html_output,
                resources_directory,
            )
            keep_resources = any(path.is_file() for path in resources_directory.rglob("*"))
            return result
        finally:
            if not keep_resources:
                shutil.rmtree(resources_directory, ignore_errors=True)
    with tempfile.TemporaryDirectory(
        prefix="sell-product-in-china-resources-"
    ) as resources_directory:
        return _render_report(
            args,
            parser,
            input_path,
            output_path,
            html_output,
            Path(resources_directory),
        )


if __name__ == "__main__":
    raise SystemExit(main())
