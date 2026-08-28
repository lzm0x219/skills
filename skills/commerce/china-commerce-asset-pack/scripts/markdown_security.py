"""Security boundaries for Markdown-to-PDF rendering."""

from __future__ import annotations

import html
from html.parser import HTMLParser
from io import BytesIO
import mimetypes
import os
from pathlib import Path
import re
import stat
import warnings
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname


SAFE_HTML_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
SAFE_HTML_ATTRIBUTES = {
    "alt",
    "class",
    "colspan",
    "href",
    "id",
    "rowspan",
    "src",
    "title",
}
UNSAFE_URL_SCHEMES = {"data", "file", "javascript", "vbscript"}
SAFE_LINK_SCHEMES = {"https"}
SAFE_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}
SAFE_IMAGE_FORMAT_SUFFIXES = {
    "JPEG": {".jpeg", ".jpg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}
MAX_IMAGE_PIXELS = 50_000_000
VOID_HTML_TAGS = {"base", "br", "hr", "img", "meta"}


class UnsafeMarkdownError(ValueError):
    """Raised when Markdown would make browser rendering unsafe."""


def local_resource_base_uri(resource_root: Path) -> str:
    """Return one canonical directory URI for local report resources."""
    resource_uri = resource_root.resolve().as_uri()
    return resource_uri if resource_uri.endswith("/") else f"{resource_uri}/"


def _without_code_literals(md_text: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in md_text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            output.append("")
            continue
        output.append("" if fence else re.sub(r"`+[^`]*`+", "", line))
    return "\n".join(output)


def validate_markdown_for_render(md_text: str, *, resource_root: Path | None = None) -> None:
    """Reject active HTML and resource URLs before starting a renderer."""
    active_text = _without_code_literals(md_text)
    if re.search(r"(?is)<!--|<\s*/?\s*[A-Za-z][^>]*>|<\s*[!?]", active_text):
        raise UnsafeMarkdownError("Markdown contains raw HTML; remove it before rendering")
    if re.search(r"(?i)\bfile\s*:", active_text):
        raise UnsafeMarkdownError("Markdown contains a local file URL")

    image_targets = re.findall(
        r"!\[[^\]]*\]\(\s*<?([^\s)>]+)",
        active_text,
    )
    for target in image_targets:
        _validate_url(target, resource=True, resource_root=resource_root)


def _decode_url_path(path: str) -> str:
    decoded = path
    for _ in range(5):
        previous = decoded
        decoded = unquote(decoded)
        if decoded == previous:
            break
    else:
        raise UnsafeMarkdownError("resource path has excessive URL encoding")
    if any(ord(character) < 32 for character in decoded):
        raise UnsafeMarkdownError("resource path contains control characters")
    return decoded.replace("\\", "/")


def _validate_url(
    value: str,
    *,
    resource: bool,
    resource_root: Path | None = None,
) -> Path | None:
    candidate = html.unescape(value).strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError as error:
        raise UnsafeMarkdownError(f"invalid URL: {candidate}") from error
    if parsed.scheme.lower() in UNSAFE_URL_SCHEMES:
        raise UnsafeMarkdownError(f"unsafe URL scheme: {parsed.scheme}")
    if resource and (parsed.scheme or parsed.netloc or candidate.startswith(("/", "\\"))):
        raise UnsafeMarkdownError("remote or absolute resources are not allowed")
    if not resource:
        if parsed.scheme.lower() in SAFE_LINK_SCHEMES and parsed.netloc:
            return None
        if (
            not parsed.scheme
            and not parsed.netloc
            and not parsed.path
            and not parsed.query
            and parsed.fragment
        ):
            return None
        raise UnsafeMarkdownError("only HTTPS and nonempty page-fragment links are allowed")
    if resource:
        if parsed.query or parsed.fragment:
            raise UnsafeMarkdownError("resource URLs cannot contain a query or fragment")
        decoded_path = _decode_url_path(parsed.path)
        try:
            decoded_url = urlsplit(decoded_path)
        except ValueError as error:
            raise UnsafeMarkdownError(f"invalid resource URL: {candidate}") from error
        if decoded_url.scheme or decoded_url.netloc or decoded_path.startswith("/"):
            raise UnsafeMarkdownError("remote or absolute resources are not allowed")
        if ".." in Path(decoded_path).parts:
            raise UnsafeMarkdownError("resource paths cannot leave the report directory")
        relative_path = Path(decoded_path)
        if resource_root is not None:
            try:
                resolved_root = resource_root.resolve()
                _reject_symlink_components(resolved_root, relative_path)
                resolved_resource = (resolved_root / relative_path).resolve()
            except (OSError, RuntimeError) as error:
                raise UnsafeMarkdownError("resource path cannot be resolved") from error
            if not resolved_resource.is_relative_to(resolved_root):
                raise UnsafeMarkdownError("resource paths cannot leave the report directory")
            if not resolved_resource.is_file():
                raise UnsafeMarkdownError("resource must be an existing image file")
            if resolved_resource.suffix.lower() not in SAFE_IMAGE_SUFFIXES:
                raise UnsafeMarkdownError("resource must be a PNG, JPEG, or WebP image")
        return relative_path
    return None


def _reject_symlink_components(resource_root: Path, relative_path: Path) -> None:
    current = resource_root
    try:
        for part in relative_path.parts:
            current /= part
            if current.is_symlink():
                raise UnsafeMarkdownError("resource paths cannot contain symlinks")
    except OSError as error:
        raise UnsafeMarkdownError("resource path cannot be inspected") from error


def _read_stable_resource(resource_root: Path, relative_path: Path) -> bytes:
    resolved_root = resource_root.resolve()
    source_path = resolved_root / relative_path
    _reject_symlink_components(resolved_root, relative_path)
    try:
        with source_path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            content = stream.read()
            after = os.fstat(stream.fileno())
        path_state = source_path.stat(follow_symlinks=False)
    except OSError as error:
        raise UnsafeMarkdownError("resource changed while it was being staged") from error
    _reject_symlink_components(resolved_root, relative_path)
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if (
        not stat.S_ISREG(before.st_mode)
        or identity(before) != identity(after)
        or identity(after) != identity(path_state)
    ):
        raise UnsafeMarkdownError("resource changed while it was being staged")
    return content


def _validate_image_content(content: bytes, relative_path: Path) -> None:
    try:
        from PIL import Image, UnidentifiedImageError
    except ModuleNotFoundError as error:
        raise UnsafeMarkdownError("Pillow is required to validate local images") from error

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                image_format = image.format or ""
                width, height = image.size
                if relative_path.suffix.lower() not in SAFE_IMAGE_FORMAT_SUFFIXES.get(
                    image_format,
                    set(),
                ):
                    raise UnsafeMarkdownError(
                        "resource extension does not match its image content"
                    )
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise UnsafeMarkdownError("resource image dimensions are unsafe")
                image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError) as error:
        raise UnsafeMarkdownError("resource is not a safe raster image") from error
    except (OSError, SyntaxError) as error:
        raise UnsafeMarkdownError("resource image is corrupt") from error


def stage_local_resources(
    resource_paths: tuple[Path, ...],
    *,
    resource_root: Path,
    staging_root: Path,
) -> None:
    """Copy validated report images into one private, immutable render root."""
    resolved_staging_root = staging_root.resolve()
    for relative_path in sorted(set(resource_paths), key=lambda path: path.as_posix()):
        content = _read_stable_resource(resource_root, relative_path)
        _validate_image_content(content, relative_path)
        destination = resolved_staging_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def build_local_resource_fetcher(resource_root: Path) -> object:
    """Return a current WeasyPrint fetcher confined to one staged root."""
    from weasyprint import URLFetcher
    from weasyprint.urls import URLFetcherResponse

    resolved_root = resource_root.resolve()

    class LocalResourceFetcher(URLFetcher):
        def __init__(self) -> None:
            super().__init__(
                allowed_protocols={"file"},
                allow_redirects=False,
                fail_on_errors=True,
            )

        def fetch(self, url: str, headers: dict[str, str] | None = None) -> object:
            del headers
            try:
                parsed = urlsplit(url)
                if (
                    parsed.scheme != "file"
                    or parsed.netloc
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValueError("only local staged resources are allowed")
                path = Path(url2pathname(unquote(parsed.path))).resolve()
                if not path.is_relative_to(resolved_root) or not path.is_file():
                    raise ValueError("resource is outside the staging directory")
                mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                return URLFetcherResponse(
                    path.as_uri(),
                    path.read_bytes(),
                    {"Content-Type": mime_type},
                    200,
                )
            except (OSError, RuntimeError, ValueError) as error:
                raise ValueError("resource request was rejected") from error

    return LocalResourceFetcher()


class _RenderedHtmlValidator(HTMLParser):
    def __init__(self, *, resource_root: Path | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.resource_root = resource_root
        self.resource_paths: list[Path] = []
        self.open_tags: list[str] = []

    def _record_start_tag(self, tag: str) -> None:
        if tag not in VOID_HTML_TAGS:
            self.open_tags.append(tag)

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag not in SAFE_HTML_TAGS:
            raise UnsafeMarkdownError(f"unsupported HTML tag: {tag}")
        for name, value in attrs:
            if name == "style":
                if tag not in {"td", "th"} or value is None or not re.fullmatch(
                    r"\s*text-align\s*:\s*(?:left|center|right)\s*;?\s*",
                    value,
                    flags=re.I,
                ):
                    raise UnsafeMarkdownError("unsupported HTML style")
                continue
            if name not in SAFE_HTML_ATTRIBUTES or name.startswith("on"):
                raise UnsafeMarkdownError(f"unsupported HTML attribute: {name}")
            if value is not None and name == "src":
                relative_path = _validate_url(
                    value,
                    resource=True,
                    resource_root=self.resource_root,
                )
                if relative_path is not None:
                    self.resource_paths.append(relative_path)
            elif name == "href":
                if value is None:
                    raise UnsafeMarkdownError("link destination is required")
                _validate_url(value, resource=False)
        self._record_start_tag(tag)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_HTML_TAGS:
            self.open_tags.pop()

    def handle_endtag(self, tag: str) -> None:
        if not self.open_tags or self.open_tags[-1] != tag:
            raise UnsafeMarkdownError(f"mismatched HTML end tag: {tag}")
        self.open_tags.pop()

    def handle_decl(self, _decl: str) -> None:
        raise UnsafeMarkdownError("HTML declarations are not allowed")

    def handle_comment(self, _data: str) -> None:
        raise UnsafeMarkdownError("HTML comments are not allowed")

    def assert_balanced(self) -> None:
        if self.open_tags:
            raise UnsafeMarkdownError(f"unclosed HTML tag: {self.open_tags[-1]}")


def validate_rendered_html(
    html_body: str,
    *,
    resource_root: Path | None = None,
) -> tuple[Path, ...]:
    validator = _RenderedHtmlValidator(resource_root=resource_root)
    validator.feed(html_body)
    validator.close()
    validator.assert_balanced()
    return tuple(validator.resource_paths)


class _FinalDocumentValidator(_RenderedHtmlValidator):
    """Validate the trusted report wrapper as well as rendered Markdown."""

    WRAPPER_TAGS = {
        "html",
        "head",
        "meta",
        "base",
        "title",
        "style",
        "body",
        "section",
        "main",
        "div",
    }
    WRAPPER_ATTRIBUTES = {"lang", "charset", "name", "content"}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag not in self.WRAPPER_TAGS:
            super().handle_starttag(tag, attrs)
            return

        for name, value in attrs:
            if name.startswith("on"):
                raise UnsafeMarkdownError(f"unsupported HTML attribute: {name}")
            if tag == "base" and name == "href" and value is not None:
                if self.resource_root is None:
                    raise UnsafeMarkdownError("unexpected resource base URL")
                expected = local_resource_base_uri(self.resource_root)
                if value != expected:
                    raise UnsafeMarkdownError("unexpected resource base URL")
                continue
            if name == "class" and tag in {"section", "main", "div"}:
                continue
            if name not in self.WRAPPER_ATTRIBUTES:
                raise UnsafeMarkdownError(f"unsupported HTML attribute: {name}")
        self._record_start_tag(tag)

    def handle_decl(self, decl: str) -> None:
        if decl.lower().strip() != "doctype html":
            raise UnsafeMarkdownError("unsupported HTML declaration")


def validate_final_document(document: str, *, resource_root: Path | None = None) -> None:
    validator = _FinalDocumentValidator(resource_root=resource_root)
    validator.feed(document)
    validator.close()
    validator.assert_balanced()
