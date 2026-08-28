#!/usr/bin/env python3

from __future__ import annotations

import base64
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname
from unittest import mock
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "commerce" / "china-commerce-asset-pack"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
PDF_STUB = b"%PDF-1.7\n" + b"0" * 96 + b"\n%%EOF\n"


def _load_module(
    path: Path,
    module_name: str,
    *,
    add_parent_to_sys_path: bool = False,
) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    if add_parent_to_sys_path:
        sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        if add_parent_to_sys_path:
            sys.path.pop(0)
    return module


def load_script(name: str) -> types.ModuleType:
    path = SKILL / "scripts" / f"{name}.py"
    return _load_module(
        path,
        f"china_commerce_asset_pack_{name}",
        add_parent_to_sys_path=True,
    )


def load_repository_script(name: str) -> types.ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    return _load_module(path, f"repository_{name}")


class ChinaCommerceAssetPackTest(unittest.TestCase):
    def test_pdf_style_tokens_keep_body_text_accessible(self) -> None:
        styles = load_script("pdf_styles")
        tokens = dict(
            re.findall(
                r"--(color-[\w-]+):\s*(#[0-9A-F]{6});",
                styles.CSS_TEMPLATE,
            )
        )

        def relative_luminance(color: str) -> float:
            channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        page_luminance = relative_luminance(tokens["color-page"])
        for token in (
            "color-ink",
            "color-text-body",
            "color-text-secondary",
            "color-text-muted",
        ):
            with self.subTest(token=token):
                text_luminance = relative_luminance(tokens[token])
                contrast = (page_luminance + 0.05) / (text_luminance + 0.05)
                self.assertGreaterEqual(contrast, 4.5)

        self.assertIn("--type-caption: 8.6pt;", styles.CSS_TEMPLATE)
        self.assertNotRegex(
            styles.CSS_TEMPLATE,
            r"font-size:\s*(?:7(?:\.\d+)?|8(?:\.[0-4])?)pt",
        )
        self.assertNotIn("Avenir Next", styles.CSS_TEMPLATE)
        for obsolete_color in ("#8D4638", "#9E4A3D", "#B65B45"):
            with self.subTest(obsolete_color=obsolete_color):
                self.assertNotIn(obsolete_color, styles.CSS_TEMPLATE)

    def test_pdf_renderer_builds_distinct_editorial_pages(self) -> None:
        renderer = load_script("md_to_pdf")
        source = (
            "<h2>结论摘要</h2><p>先给结论。</p>"
            '<h1 id="chapter">一、商品机会</h1><p>机会正文。</p>'
            '<h1 id="decision">最终决策</h1><blockquote><p>先上主推装。</p></blockquote>'
            '<h1 id="sources">主要资料来源</h1><p>官方资料。</p>'
        )

        structured = renderer.wrap_executive_summary(source)
        structured = renderer.wrap_final_decision(structured)
        structured = renderer.wrap_sources_appendix(structured)

        self.assertIn('<section class="executive-summary">', structured)
        self.assertIn('<section class="final-decision">', structured)
        self.assertIn('<div class="final-decision-header">', structured)
        self.assertIn('<div class="final-decision-body">', structured)
        self.assertIn('<section class="sources-appendix">', structured)
        self.assertLess(
            structured.index('class="final-decision"'),
            structured.index('class="sources-appendix"'),
        )

    def test_pdf_renderer_builds_decision_first_reading_guide(self) -> None:
        renderer = load_script("md_to_pdf")
        markdown_module = mock.Mock()
        markdown_module.markdown.return_value = (
            "<h2>结论摘要</h2><p>先给结论。</p>"
            '<h1 id="opportunity">商品机会</h1><p>证据。</p>'
            '<h1 id="decision">最终决策</h1><p>行动。</p>'
            '<h1 id="sources">主要资料来源</h1><p>来源。</p>'
        )
        source = "# 报告\n## 结论摘要\n# 商品机会\n# 最终决策\n# 主要资料来源\n"

        with mock.patch.dict(sys.modules, {"markdown": markdown_module}):
            document, _title = renderer.build_html(source)

        self.assertIn('<div class="guide-axis">', document)
        self.assertIn("<div>DECIDE</div>", document)
        self.assertIn("<div>PROVE</div>", document)
        self.assertIn("<div>ACT</div>", document)

    def test_pdf_design_contract_uses_one_visual_language(self) -> None:
        style = (SKILL / "references" / "pdf-style.md").read_text(encoding="utf-8")
        delivery = (SKILL / "references" / "deliverable-pack.md").read_text(
            encoding="utf-8"
        )
        combined = style + delivery

        self.assertNotIn("砖红", combined)
        self.assertNotIn("暖白底", combined)
        self.assertIn("决策轨道", style)
        self.assertIn("Apple 的信息纪律", style)
        self.assertIn("OpenAI 的编辑气质", style)

    def test_pdf_renderer_recognizes_template_decision_heading(self) -> None:
        renderer = load_script("md_to_pdf")
        source = (
            '<h1 id="decision">最终决策卡（Final Decision Card）</h1>'
            "<p>建议先验证主推装。</p>"
            '<h1 id="sources">主要资料来源（Sources）</h1>'
        )

        structured = renderer.wrap_final_decision(source)

        self.assertIn('<section class="final-decision">', structured)
        self.assertIn('<div class="final-decision-body">', structured)
        self.assertIn('<h1 id="decision">最终决策卡</h1>', structured)

    def test_pdf_style_constrains_dense_navigation_and_tables(self) -> None:
        styles = load_script("pdf_styles")

        self.assertRegex(
            styles.CSS_TEMPLATE,
            r"(?s)\.toc li \{.*?min-height:\s*10mm;",
        )
        self.assertRegex(
            styles.CSS_TEMPLATE,
            r"(?s)table\.cols-6,.*?table\.cols-8 \{[^}]*table-layout:\s*fixed;",
        )
        self.assertRegex(
            styles.CSS_TEMPLATE,
            r"(?s)table\.cols-5 \{[^}]*table-layout:\s*fixed;",
        )

    def test_atomic_batch_rolls_back_without_removing_a_racing_file(self) -> None:
        atomic = load_script("atomic_output")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged_a = root / "staged-a.png"
            staged_b = root / "staged-b.png"
            destination_a = root / "a.png"
            destination_b = root / "b.png"
            staged_a.write_bytes(b"a")
            staged_b.write_bytes(b"b")
            real_link = atomic.os.link
            calls = 0

            def race_on_second_link(source: Path, destination: Path, **kwargs: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    real_link(source, destination, **kwargs)
                    return
                destination_b.write_bytes(b"racer")
                raise FileExistsError(destination)

            with (
                mock.patch.object(atomic.os, "link", side_effect=race_on_second_link),
                self.assertRaises(atomic.OutputExistsError),
            ):
                atomic.commit_staged_files(
                    [(staged_a, destination_a), (staged_b, destination_b)],
                    overwrite=False,
                )

            self.assertFalse(destination_a.exists())
            self.assertEqual(b"racer", destination_b.read_bytes())

    def test_workspace_eval_fixture_matches_the_behavior_case(self) -> None:
        runner = load_repository_script("run_workspace_evals")

        entry = runner.load_behavior_case(
            "china-commerce-asset-pack",
            "strategy-deliverable-write",
        )
        input_directory, changes = runner.load_workspace_expectation(
            "china-commerce-asset-pack",
            "strategy-deliverable-write",
        )

        self.assertEqual("explicit", entry["invocation"])
        self.assertTrue((input_directory / "商品资料.md").is_file())
        self.assertEqual(
            {
                "created": ["deliverables", "deliverables/商品销售战略.md"],
                "modified": [],
                "deleted": [],
            },
            changes,
        )

    def test_pdf_renderer_rejects_active_html_and_remote_images(self) -> None:
        renderer = load_script("md_to_pdf")
        unsafe_inputs = (
            "# Report\n<script>fetch('https://example.com/pixel')</script>\n",
            "# Report\n![tracking](https://example.com/pixel.png)\n",
            "# Report\n<a href=\"file:///etc/passwd\">local file</a>\n",
        )

        for source in unsafe_inputs:
            with self.subTest(source=source), self.assertRaises(
                renderer.UnsafeMarkdownError
            ):
                renderer.build_html(source)

    def test_pdf_renderer_allows_safe_markdown_links_and_fenced_html(self) -> None:
        renderer = load_script("md_to_pdf")
        source = (
            "# Report\n[官方资料](https://example.com/docs)\n\n"
            "```html\n<script>alert('shown as code')</script>\n```\n"
        )

        renderer.validate_markdown_for_render(source)
        renderer.validate_rendered_html(
            '<p><a href="https://example.com/docs">官方资料</a></p>'
            "<pre><code>&lt;script&gt;alert('shown as code')&lt;/script&gt;</code></pre>"
            '<table><tbody><tr><td style="text-align: right;">¥39</td></tr></tbody></table>'
        )

        with self.assertRaises(renderer.UnsafeMarkdownError):
            renderer.validate_rendered_html(
                '<p style="background: url(https://example.com/pixel.png)">unsafe</p>'
            )
        with self.assertRaises(renderer.UnsafeMarkdownError):
            renderer.validate_rendered_html("<p><strong>mismatched</p></strong>")

    def test_pdf_renderer_rejects_malformed_and_relative_urls(self) -> None:
        renderer = load_script("md_to_pdf")

        with self.assertRaises(renderer.UnsafeMarkdownError):
            renderer.validate_markdown_for_render("# Report\n![bad](//[)\n")
        with self.assertRaises(renderer.UnsafeMarkdownError):
            renderer.validate_rendered_html('<p><a href="notes.txt">local note</a></p>')

        unsafe_links = (
            '<a href>missing</a>',
            '<a href="">empty</a>',
            '<a href="?q=1">query only</a>',
            '<a href="http://example.com">insecure web</a>',
            '<a href="mailto:buyer@example.com">email</a>',
            '<a href="tel:10086">phone</a>',
        )
        for link in unsafe_links:
            with self.subTest(link=link), self.assertRaises(
                renderer.UnsafeMarkdownError
            ):
                renderer.validate_rendered_html(link)

        renderer.validate_rendered_html('<p><a href="#section-1">chapter</a></p>')
        renderer.validate_rendered_html(
            '<p><a href="https://example.com/docs">official source</a></p>'
        )

    def test_pdf_renderer_confines_images_to_the_markdown_directory(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resource_root = root / "report"
            assets = resource_root / "assets"
            assets.mkdir(parents=True)
            (assets / "safe.png").write_bytes(b"safe")
            outside = root / "outside.png"
            outside.write_bytes(b"outside")
            (assets / "linked.png").symlink_to(outside)
            (assets / "linked-inside.png").symlink_to(assets / "safe.png")

            renderer.validate_markdown_for_render(
                "# Report\n![safe](assets/safe.png)\n",
                resource_root=resource_root,
            )

            unsafe_sources = (
                "# Report\n![encoded](%2e%2e/outside.png)\n",
                "# Report\n![backslash](..\\outside.png)\n",
                "# Report\n![symlink](assets/linked.png)\n",
                "# Report\n![internal-symlink](assets/linked-inside.png)\n",
            )
            for source in unsafe_sources:
                with self.subTest(source=source), self.assertRaises(
                    renderer.UnsafeMarkdownError
                ):
                    renderer.validate_markdown_for_render(
                        source,
                        resource_root=resource_root,
                    )

    def test_pdf_renderer_rejects_missing_and_unsupported_images(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            resource_root = Path(directory)
            (resource_root / "unsafe.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
                encoding="utf-8",
            )

            unsafe_sources = (
                "# Report\n![missing](missing.png)\n",
                "# Report\n![vector](unsafe.svg)\n",
            )
            for source in unsafe_sources:
                with self.subTest(source=source), self.assertRaises(
                    renderer.UnsafeMarkdownError
                ):
                    renderer.validate_markdown_for_render(
                        source,
                        resource_root=resource_root,
                    )

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_pdf_renderer_bases_relative_images_on_the_markdown_directory(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            resource_root = Path(directory).resolve()
            staging_root = resource_root / "staging"
            staging_root.mkdir()
            assets = resource_root / "assets"
            assets.mkdir()
            (assets / "safe.png").write_bytes(PNG_1X1)
            markdown_module = mock.Mock()
            markdown_module.markdown.return_value = (
                '<p><img alt="safe" src="assets/safe.png"></p>'
            )

            with mock.patch.dict(sys.modules, {"markdown": markdown_module}):
                document, _title = renderer.build_html(
                    "# Report\n![safe](assets/safe.png)\n",
                    resource_root=resource_root,
                    resource_staging_root=staging_root,
                )

            self.assertIn(f'<base href="{staging_root.as_uri()}/">', document)

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_pdf_renderer_renders_from_a_private_resource_snapshot(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            source_image = assets / "safe.png"
            source_image.write_bytes(PNG_1X1)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n![safe](assets/safe.png)\n", encoding="utf-8")
            observed_staging_root: Path | None = None
            runtime = load_script("pdf_runtime")

            def render(request: object) -> object:
                nonlocal observed_staging_root
                document = request.html_path.read_text(encoding="utf-8")
                match = re.search(r'<base href="([^"]+)">', document)
                self.assertIsNotNone(match)
                parsed = urlsplit(match.group(1))
                observed_staging_root = Path(url2pathname(unquote(parsed.path)))
                self.assertNotEqual(root.resolve(), observed_staging_root.resolve())
                staged_image = observed_staging_root / "assets" / "safe.png"
                self.assertEqual(PNG_1X1, staged_image.read_bytes())
                source_image.write_bytes(b"changed after validation")
                self.assertEqual(PNG_1X1, staged_image.read_bytes())
                request.output_path.write_bytes(PDF_STUB)
                return runtime.RenderResult(True, "chrome")

            arguments = [
                "md_to_pdf.py",
                str(source),
                str(output),
                "--engine",
                "chrome",
            ]
            markdown_module = mock.Mock()
            markdown_module.markdown.return_value = (
                '<p><img alt="safe" src="assets/safe.png"></p>'
            )
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.dict(sys.modules, {"markdown": markdown_module}),
                mock.patch.object(renderer, "find_browser", return_value=Path("/fake/chrome")),
                mock.patch.object(renderer, "render_pdf", side_effect=render),
                mock.patch("sys.stdout", io.StringIO()),
            ):
                self.assertEqual(0, renderer.main())

            self.assertIsNotNone(observed_staging_root)
            self.assertFalse(observed_staging_root.exists())

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_pdf_renderer_keeps_the_snapshot_for_persistent_html(self) -> None:
        renderer = load_script("md_to_pdf")
        runtime = load_script("pdf_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            (assets / "safe.png").write_bytes(PNG_1X1)
            source = root / "report.md"
            output = root / "report.pdf"
            html_output = root / "report.html"
            source.write_text("# Report\n![safe](assets/safe.png)\n", encoding="utf-8")
            markdown_module = mock.Mock()
            markdown_module.markdown.return_value = (
                '<p><img alt="safe" src="assets/safe.png"></p>'
            )

            def render(request: object) -> object:
                request.output_path.write_bytes(PDF_STUB)
                return runtime.RenderResult(True, "chrome")

            arguments = [
                "md_to_pdf.py",
                str(source),
                str(output),
                "--html-output",
                str(html_output),
                "--engine",
                "chrome",
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.dict(sys.modules, {"markdown": markdown_module}),
                mock.patch.object(renderer, "find_browser", return_value=Path("/fake/chrome")),
                mock.patch.object(renderer, "render_pdf", side_effect=render),
                mock.patch("sys.stdout", io.StringIO()),
            ):
                self.assertEqual(0, renderer.main())

            document = html_output.read_text(encoding="utf-8")
            match = re.search(r'<base href="([^"]+)">', document)
            self.assertIsNotNone(match)
            parsed = urlsplit(match.group(1))
            snapshot_root = Path(url2pathname(unquote(parsed.path)))
            self.assertEqual(PNG_1X1, (snapshot_root / "assets" / "safe.png").read_bytes())

    def test_pdf_renderer_rejects_invalid_raster_content(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            staging.mkdir()
            (root / "fake.png").write_bytes(b"not a PNG")
            markdown_module = mock.Mock()
            markdown_module.markdown.return_value = (
                '<p><img alt="fake" src="fake.png"></p>'
            )

            with (
                mock.patch.dict(sys.modules, {"markdown": markdown_module}),
                self.assertRaises(renderer.UnsafeMarkdownError),
            ):
                renderer.build_html(
                    "# Report\n![fake](fake.png)\n",
                    resource_root=root,
                    resource_staging_root=staging,
                )

    def test_pdf_renderer_keeps_entity_encoded_title_inside_css_text(self) -> None:
        renderer = load_script("md_to_pdf")
        markdown_module = mock.Mock()
        markdown_module.markdown.return_value = "<p>body</p>"
        source = (
            "# &lt;/style&gt;&lt;script&gt;globalThis.pwned=1"
            "&lt;/script&gt;&lt;style&gt;\n"
        )

        with mock.patch.dict(sys.modules, {"markdown": markdown_module}):
            document, title = renderer.build_html(source)

        self.assertEqual("</style><script>globalThis.pwned=1</script><style>", title)
        self.assertNotIn("</style><script>", document)
        renderer.validate_final_document(document)

    def test_pdf_renderer_refuses_existing_output_without_overwrite(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")
            output.write_bytes(b"existing")

            with mock.patch.object(sys, "argv", ["md_to_pdf.py", str(source), str(output)]):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        renderer.main()

            self.assertEqual(2, raised.exception.code)
            self.assertEqual(b"existing", output.read_bytes())

    def test_pdf_renderer_reports_a_missing_markdown_dependency_cleanly(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")
            missing = ModuleNotFoundError("No module named 'markdown'", name="markdown")
            stderr = io.StringIO()

            with (
                mock.patch.object(sys, "argv", ["md_to_pdf.py", str(source), str(output)]),
                mock.patch.object(renderer, "build_html", side_effect=missing),
                redirect_stderr(stderr),
                self.assertRaises(SystemExit) as raised,
            ):
                renderer.main()

            self.assertEqual(2, raised.exception.code)
            self.assertIn("Markdown 渲染准备失败", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_pdf_renderer_refuses_input_output_and_html_path_aliases(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")

            cases = (
                ["md_to_pdf.py", str(source), str(source), "--overwrite"],
                [
                    "md_to_pdf.py",
                    str(source),
                    str(output),
                    "--html-output",
                    str(source),
                    "--overwrite",
                ],
                [
                    "md_to_pdf.py",
                    str(source),
                    str(output),
                    "--html-output",
                    str(output),
                    "--overwrite",
                ],
            )
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    with (
                        mock.patch.object(sys, "argv", arguments),
                        redirect_stderr(io.StringIO()),
                        self.assertRaises(SystemExit) as raised,
                    ):
                        renderer.main()
                    self.assertEqual(2, raised.exception.code)

            self.assertEqual("# Report\n", source.read_text(encoding="utf-8"))
            self.assertFalse(output.exists())

    def test_pdf_renderer_refuses_existing_html_without_overwrite(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            html_output = root / "report.html"
            source.write_text("# Report\n", encoding="utf-8")
            html_output.write_text("existing", encoding="utf-8")
            arguments = [
                "md_to_pdf.py",
                str(source),
                str(output),
                "--html-output",
                str(html_output),
            ]

            with (
                mock.patch.object(sys, "argv", arguments),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                renderer.main()

            self.assertEqual(2, raised.exception.code)
            self.assertEqual("existing", html_output.read_text(encoding="utf-8"))

    def test_failed_pdf_render_preserves_existing_output(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")
            output.write_bytes(b"existing")
            arguments = [
                "md_to_pdf.py",
                str(source),
                str(output),
                "--overwrite",
                "--engine",
                "chrome",
            ]

            runtime = load_script("pdf_runtime")

            def fail_render(request: object) -> object:
                request.output_path.write_bytes(b"partial")
                return runtime.RenderResult(False, "chrome", "render_failed", "failure")

            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(renderer, "build_html", return_value=("<html></html>", "Report")),
                mock.patch.object(renderer, "find_browser", return_value=Path("/fake/chrome")),
                mock.patch.object(renderer, "render_pdf", side_effect=fail_render),
                mock.patch("sys.stdout", io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(1, renderer.main())

            self.assertEqual(b"existing", output.read_bytes())

    def test_pdf_renderer_does_not_clobber_a_racing_output(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")

            runtime = load_script("pdf_runtime")

            def race_render(request: object) -> object:
                output.write_bytes(b"created by another process")
                request.output_path.write_bytes(PDF_STUB)
                return runtime.RenderResult(True, "chrome")

            arguments = [
                "md_to_pdf.py",
                str(source),
                str(output),
                "--engine",
                "chrome",
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(renderer, "build_html", return_value=("<html></html>", "Report")),
                mock.patch.object(renderer, "find_browser", return_value=Path("/fake/chrome")),
                mock.patch.object(renderer, "render_pdf", side_effect=race_render),
                mock.patch("sys.stdout", io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(1, renderer.main())

            self.assertEqual(b"created by another process", output.read_bytes())

    def test_pdf_renderer_auto_does_not_fallback_without_chrome(self) -> None:
        renderer = load_script("md_to_pdf")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "report.md"
            output = root / "report.pdf"
            source.write_text("# Report\n", encoding="utf-8")
            arguments = ["md_to_pdf.py", str(source), str(output), "--engine", "auto"]

            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(renderer, "build_html", return_value=("<html></html>", "Report")),
                mock.patch.object(renderer, "find_browser", return_value=None),
                mock.patch("sys.stdout", io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(1, renderer.main())

            self.assertFalse(output.exists())

    def test_chrome_render_uses_an_isolated_network_quiet_profile(self) -> None:
        browser_runtime = load_script("browser_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "report.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            observed: list[str] = []
            observed_environment: dict[str, str] = {}

            def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                observed.extend(command)
                observed_environment.update(kwargs["env"])
                output.write_bytes(PDF_STUB)
                return subprocess.CompletedProcess(command, 0, "", "")

            with mock.patch.object(browser_runtime.subprocess, "run", side_effect=run):
                self.assertTrue(
                    browser_runtime.render_pdf_with_browser(
                        Path("/fake/chrome"),
                        html_path,
                        output,
                    )[0]
                )

            self.assertIn("--disable-background-networking", observed)
            self.assertIn("--disable-extensions", observed)
            self.assertIn("--incognito", observed)
            self.assertNotIn("--user-data-dir", " ".join(observed))
            self.assertEqual(
                observed_environment["HOME"],
                observed_environment["USERPROFILE"],
            )
            self.assertFalse(Path(observed_environment["HOME"]).exists())

    def test_macos_chrome_render_uses_a_mock_keychain(self) -> None:
        browser_runtime = load_script("browser_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "report.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            observed: list[str] = []

            def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                observed.extend(command)
                output.write_bytes(PDF_STUB)
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                mock.patch.object(browser_runtime.sys, "platform", "darwin"),
                mock.patch.object(browser_runtime.subprocess, "run", side_effect=run),
            ):
                self.assertTrue(
                    browser_runtime.render_pdf_with_browser(
                        Path("/fake/chrome"),
                        html_path,
                        output,
                    )[0]
                )

            self.assertIn("--use-mock-keychain", observed)

    def test_browser_rejects_a_non_pdf_output(self) -> None:
        browser_runtime = load_script("browser_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "report.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")

            def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                output.write_bytes(b"not a PDF")
                return subprocess.CompletedProcess(command, 0, "", "")

            with mock.patch.object(browser_runtime.subprocess, "run", side_effect=run):
                success, error = browser_runtime.render_pdf_with_browser(
                    Path("/fake/chrome"),
                    html_path,
                    output,
                )

            self.assertFalse(success)
            self.assertIn("valid PDF", error)

    def test_browser_rejects_a_truncated_pdf_signature(self) -> None:
        browser_runtime = load_script("browser_runtime")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.pdf"
            output.write_bytes(b"%PDF-1.7\n")

            self.assertFalse(browser_runtime.is_pdf_file(output))

    def test_weasyprint_render_uses_an_isolated_subprocess(self) -> None:
        runtime = load_script("pdf_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "temporary.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            observed: dict[str, object] = {}

            def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                observed["command"] = command
                observed["environment"] = kwargs["env"]
                Path(command[3]).write_bytes(PDF_STUB)
                return subprocess.CompletedProcess(command, 0, "", "")

            request = runtime.RenderRequest(
                engine="weasyprint",
                html_path=html_path,
                output_path=output,
                resource_root=root,
            )
            with (
                mock.patch.object(runtime.subprocess, "run", side_effect=run),
                mock.patch.dict(
                    runtime.os.environ,
                    {"PYTHONHOME": "/unsafe", "PYTHONPATH": "/unsafe"},
                    clear=True,
                ),
            ):
                result = runtime.render_pdf(request)

            self.assertTrue(result.success)
            command = observed["command"]
            self.assertEqual(str(runtime.WEASYPRINT_RUNNER), command[1])
            self.assertEqual(str(html_path), command[2])
            self.assertEqual(str(output), command[3])
            self.assertEqual(str(root), command[4])
            environment = observed["environment"]
            self.assertNotIn("PYTHONHOME", environment)
            self.assertNotIn("PYTHONPATH", environment)
            self.assertFalse(Path(environment["HOME"]).exists())

    def test_weasyprint_rejects_a_non_pdf_subprocess_output(self) -> None:
        runtime = load_script("pdf_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "temporary.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            request = runtime.RenderRequest(
                engine="weasyprint",
                html_path=html_path,
                output_path=output,
                resource_root=root,
            )

            with mock.patch.object(
                runtime.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(["python"], 0, "", ""),
            ):
                result = runtime.render_pdf(request)

            self.assertFalse(result.success)
            self.assertEqual("invalid_output", result.error_kind)
            self.assertFalse(output.exists())

    def test_weasyprint_fetcher_uses_the_current_response_contract(self) -> None:
        security = load_script("markdown_security")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            staging.mkdir()
            safe_asset = staging / "safe.png"
            safe_asset.write_bytes(b"safe")
            outside_asset = root / "outside.png"
            outside_asset.write_bytes(b"outside")

            class FakeURLFetcher:
                def __init__(self, **kwargs: object) -> None:
                    self.settings = kwargs

                def __call__(self, url: str) -> object:
                    return self.fetch(url)

            class FakeURLFetcherResponse:
                def __init__(
                    self,
                    url: str,
                    body: bytes,
                    headers: dict[str, str],
                    status: int,
                ) -> None:
                    self.url = url
                    self.body = body
                    self.headers = headers
                    self.status = status

            fake_weasyprint = types.ModuleType("weasyprint")
            fake_weasyprint.URLFetcher = FakeURLFetcher
            fake_urls = types.ModuleType("weasyprint.urls")
            fake_urls.URLFetcherResponse = FakeURLFetcherResponse
            with mock.patch.dict(
                sys.modules,
                {"weasyprint": fake_weasyprint, "weasyprint.urls": fake_urls},
            ):
                fetcher = security.build_local_resource_fetcher(staging)

            response = fetcher(safe_asset.as_uri())
            self.assertIsInstance(response, FakeURLFetcherResponse)
            self.assertEqual(b"safe", response.body)
            self.assertEqual({"file"}, fetcher.settings["allowed_protocols"])
            self.assertTrue(fetcher.settings["fail_on_errors"])
            with self.assertRaises(ValueError):
                fetcher("https://example.com/tracker.png")
            with self.assertRaises(ValueError):
                fetcher(outside_asset.as_uri())

    def test_weasyprint_timeout_returns_a_structured_render_error(self) -> None:
        runtime = load_script("pdf_runtime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "report.html"
            output = root / "report.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            request = runtime.RenderRequest(
                engine="weasyprint",
                html_path=html_path,
                output_path=output,
                resource_root=root,
            )

            with mock.patch.object(
                runtime.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["python"], 0.01),
            ):
                result = runtime.render_pdf(request, timeout=0.01)

            self.assertFalse(result.success)
            self.assertEqual("weasyprint", result.engine)
            self.assertEqual("timeout", result.error_kind)
            self.assertFalse(output.exists())

    def test_pdf_generation_notice_has_no_upstream_branding(self) -> None:
        renderer = load_script("md_to_pdf")

        notice = renderer.build_signature_html()

        self.assertIn("china-commerce-asset-pack Skill", notice)
        self.assertNotIn("Jiaran", notice)
        self.assertNotIn("evadebot", notice)
        self.assertNotIn("c.aoao.ai", notice)

    def test_image_normalizer_refuses_existing_output_without_overwrite(self) -> None:
        normalizer = load_script("normalize_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "page.png").write_bytes(b"source")
            destination = output_dir / "page.png"
            destination.write_bytes(b"existing")

            arguments = [
                "normalize_images.py",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                self.assertRaises(SystemExit),
            ):
                normalizer.main()

            self.assertEqual(b"existing", destination.read_bytes())

    def test_image_normalizer_rejects_duplicate_destinations_before_writing(self) -> None:
        normalizer = load_script("normalize_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            (input_dir / "page.jpg").write_bytes(b"jpg")
            (input_dir / "page.webp").write_bytes(b"webp")
            arguments = [
                "normalize_images.py",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ]

            with (
                mock.patch.object(sys, "argv", arguments),
                self.assertRaises(SystemExit),
            ):
                normalizer.main()

            self.assertFalse(output_dir.exists())

    def test_image_normalizer_stages_the_whole_batch_before_overwrite(self) -> None:
        normalizer = load_script("normalize_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "a.png").write_bytes(PNG_1X1)
            (input_dir / "b.png").write_bytes(b"invalid image")
            destination = output_dir / "a.png"
            destination.write_bytes(b"existing")
            arguments = [
                "normalize_images.py",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--overwrite",
            ]

            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch("sys.stdout", io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(1, normalizer.main())

            self.assertEqual(b"existing", destination.read_bytes())
            self.assertFalse((output_dir / "b.png").exists())

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_image_normalizer_outputs_an_exact_transparent_png(self) -> None:
        from PIL import Image

        normalizer = load_script("normalize_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            source = input_dir / "page.webp"
            Image.new("RGBA", (4, 6), (255, 0, 0, 128)).save(source, format="WEBP")
            arguments = [
                "normalize_images.py",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--width",
                "3",
                "--height",
                "2",
            ]

            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch("sys.stdout", io.StringIO()),
            ):
                self.assertEqual(0, normalizer.main())

            with Image.open(output_dir / "page.png") as output:
                self.assertEqual("PNG", output.format)
                self.assertEqual((3, 2), output.size)
                self.assertEqual("RGBA", output.mode)

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
    def test_image_normalizer_applies_exif_orientation(self) -> None:
        from PIL import Image

        normalizer = load_script("normalize_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            source = input_dir / "oriented.jpg"
            image = Image.new("RGB", (2, 3))
            image.putdata(
                [
                    (255, 0, 0),
                    (255, 0, 0),
                    (0, 255, 0),
                    (0, 255, 0),
                    (0, 0, 255),
                    (0, 0, 255),
                ]
            )
            exif = Image.Exif()
            exif[274] = 6
            image.save(source, format="JPEG", quality=100, exif=exif)
            arguments = [
                "normalize_images.py",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--width",
                "3",
                "--height",
                "2",
            ]

            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch("sys.stdout", io.StringIO()),
            ):
                self.assertEqual(0, normalizer.main())

            with Image.open(output_dir / "oriented.png") as output:
                left = output.getpixel((0, 0))
                right = output.getpixel((2, 0))
                self.assertGreater(left[2], left[0])
                self.assertGreater(right[0], right[2])

    def test_environment_requires_a_usable_pdf_renderer(self) -> None:
        environment = load_script("check_environment")
        with (
            mock.patch.object(sys, "argv", ["check_environment.py", "--strict"]),
            mock.patch.object(environment.importlib.util, "find_spec", return_value=object()),
            mock.patch.object(environment, "find_browser", return_value=Path("/fake/chrome")),
            mock.patch.object(environment, "browser_usable", return_value=False),
            mock.patch.object(environment, "weasyprint_usable", return_value=False),
            mock.patch.object(environment.shutil, "which", return_value="/usr/bin/tool"),
            redirect_stderr(io.StringIO()),
            mock.patch("sys.stdout", io.StringIO()),
        ):
            self.assertEqual(1, environment.main())

    def test_environment_rejects_out_of_range_runtime_versions(self) -> None:
        environment = load_script("check_environment")
        stdout = io.StringIO()

        def version(name: str) -> str:
            return {"Markdown": "3.9.0", "Pillow": "11.3.0"}[name]

        with (
            mock.patch.object(sys, "argv", ["check_environment.py", "--json", "--strict"]),
            mock.patch.object(environment.importlib.util, "find_spec", return_value=object()),
            mock.patch.object(environment, "distribution_version", side_effect=version),
            mock.patch.object(environment, "find_browser", return_value=Path("/fake/chrome")),
            mock.patch.object(environment, "browser_usable", return_value=True),
            mock.patch.object(environment, "weasyprint_usable", return_value=False),
            mock.patch("sys.stdout", stdout),
        ):
            self.assertEqual(1, environment.main())

        result = json.loads(stdout.getvalue())
        self.assertFalse(result["pdf"]["markdown_module"])
        self.assertFalse(result["image_normalization"]["pillow_module"])

    def test_browser_probe_requires_a_nonempty_pdf(self) -> None:
        browser_runtime = load_script("browser_runtime")
        no_op_executable = Path("/usr/bin/true")
        if not no_op_executable.is_file():
            self.skipTest("/usr/bin/true is unavailable")

        self.assertFalse(browser_runtime.browser_usable(no_op_executable))

    def test_environment_does_not_treat_weasyprint_as_an_automatic_fallback(self) -> None:
        environment = load_script("check_environment")
        stdout = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["check_environment.py", "--json", "--strict"]),
            mock.patch.object(environment.importlib.util, "find_spec", return_value=object()),
            mock.patch.object(environment, "find_browser", return_value=Path("/fake/chrome")),
            mock.patch.object(environment, "browser_usable", return_value=False),
            mock.patch.object(environment, "weasyprint_usable", return_value=True),
            mock.patch.object(environment.shutil, "which", return_value="/usr/bin/tool"),
            redirect_stderr(io.StringIO()),
            mock.patch("sys.stdout", stdout),
        ):
            self.assertEqual(1, environment.main())

        result = json.loads(stdout.getvalue())
        self.assertFalse(result["pdf"]["chrome_usable"])
        self.assertFalse(result["pdf"]["ready"])
        self.assertTrue(result["pdf"]["weasyprint_optional"])

    def test_weasyprint_probe_renders_a_nonempty_pdf(self) -> None:
        environment = load_script("check_environment")
        observed: dict[str, object] = {}

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            observed["command"] = command
            observed["timeout"] = kwargs.get("timeout")
            observed["cwd"] = kwargs.get("cwd")
            observed["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(command, 0, "", "")

        with (
            mock.patch.object(environment.importlib.util, "find_spec", return_value=object()),
            mock.patch.object(environment.subprocess, "run", side_effect=run),
            mock.patch.dict(
                environment.os.environ,
                {
                    "PYTHONHOME": "/unsafe/home",
                    "PYTHONPATH": "/unsafe/path",
                    "PYTHONUSERBASE": "/safe/user-base",
                },
                clear=True,
            ),
        ):
            self.assertTrue(environment.weasyprint_usable())

        command = observed["command"]
        self.assertIsInstance(command, list)
        probe_code = command[-1]
        self.assertNotIn("-I", command)
        self.assertNotIn("-P", command)
        self.assertNotIn("-s", command)
        self.assertIn("write_pdf()", probe_code)
        self.assertIn("%PDF", probe_code)
        self.assertIn("%%EOF", probe_code)
        self.assertEqual(30, observed["timeout"])
        self.assertNotEqual(Path.cwd(), Path(observed["cwd"]))
        probe_environment = observed["env"]
        self.assertEqual("/safe/user-base", probe_environment["PYTHONUSERBASE"])
        self.assertNotIn("PYTHONHOME", probe_environment)
        self.assertNotIn("PYTHONPATH", probe_environment)


if __name__ == "__main__":
    unittest.main()
