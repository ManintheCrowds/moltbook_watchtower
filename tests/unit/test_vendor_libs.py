# PURPOSE: Vendored chart libraries and OFL fonts exist with pinned sha256, are permissively
#   licensed, and the generated dashboard references no external http(s) script/link/asset URLs.
import base64
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.dashboard_fixture import REPO_ROOT, generate_dashboard, seed_sample_db

VENDOR_DIR = REPO_ROOT / "vendor"
_MANIFEST = json.loads((VENDOR_DIR / "manifest.json").read_text(encoding="utf-8"))
LIBRARIES = _MANIFEST["libraries"]
FONTS = _MANIFEST["fonts"]
PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Apache-2.0 OR MIT"}
FONT_LICENSES = {"OFL-1.1"}
EXPECTED = {"chart.js": "4.6.1", "vis-network": "10.1.5", "wordcloud2.js": "1.0.2"}
EXPECTED_FONTS = {"JetBrains Mono": "2.304", "Source Sans 3": "3.052"}
EXPECTED_FACES = {
    "JetBrains Mono": {(500, "normal"), (600, "normal"), (700, "normal")},
    "Source Sans 3": {(400, "normal"), (600, "normal"), (400, "italic")},
}

_URL_ATTRS = {"src", "href", "srcset", "data", "action", "poster"}
_LICENSE_NAMES = {"LICENSE", "LICENSE.MD", "LICENSE.TXT", "OFL.TXT"}


class _UrlCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in _URL_ATTRS and value:
                self.refs.append((tag, name, value))


def _is_external(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith(("http://", "https://", "//"))


def test_manifest_lists_expected_pinned_libraries() -> None:
    assert {lib["name"]: lib["version"] for lib in LIBRARIES} == EXPECTED


def test_manifest_lists_expected_pinned_fonts() -> None:
    assert {font["name"]: font["version"] for font in FONTS} == EXPECTED_FONTS
    for font in FONTS:
        assert font["family"] == font["name"]
        faces = {(int(face["weight"]), face["style"]) for face in font["faces"]}
        assert faces == EXPECTED_FACES[font["name"]]
        for face in font["faces"]:
            assert face["file"] in font["files"]


@pytest.mark.parametrize("lib", LIBRARIES, ids=lambda lib: lib["name"])
def test_vendored_files_exist_with_matching_sha256(lib: dict) -> None:
    assert lib["script"] in lib["files"]
    for rel, expected in lib["files"].items():
        path = VENDOR_DIR / rel
        assert path.is_file(), f"missing vendored file {path}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"sha256 mismatch for {rel}"


@pytest.mark.parametrize("font", FONTS, ids=lambda font: font["name"])
def test_vendored_font_files_exist_with_matching_sha256(font: dict) -> None:
    for rel, expected in font["files"].items():
        path = VENDOR_DIR / rel
        assert path.is_file(), f"missing vendored file {path}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"sha256 mismatch for {rel}"


@pytest.mark.parametrize("lib", LIBRARIES, ids=lambda lib: lib["name"])
def test_vendored_libraries_are_permissive_and_ship_license(lib: dict) -> None:
    assert lib["license"] in PERMISSIVE
    assert any(Path(rel).name.upper().startswith("LICENSE") for rel in lib["files"]), "LICENSE file required"
    assert lib["version"] in lib["script"], "vendor dir must be version-pinned"


@pytest.mark.parametrize("font", FONTS, ids=lambda font: font["name"])
def test_vendored_fonts_are_ofl_and_ship_license(font: dict) -> None:
    assert font["license"] in FONT_LICENSES
    assert any(Path(rel).name.upper() in _LICENSE_NAMES for rel in font["files"]), "OFL/LICENSE file required"
    assert font["version"] in next(iter(font["files"])), "vendor dir must be version-pinned"


def test_third_party_notices_list_every_file_hash() -> None:
    notices = (VENDOR_DIR / "README.md").read_text(encoding="utf-8")
    for entry in (*LIBRARIES, *FONTS):
        assert entry["version"] in notices
        for rel, digest in entry["files"].items():
            assert rel in notices and digest in notices


def test_generated_dashboard_has_no_external_urls_and_inlines_vendor_libs(tmp_path) -> None:
    seed_sample_db(tmp_path / "watchtower.db")
    html = generate_dashboard(tmp_path).read_text(encoding="utf-8")

    parser = _UrlCollector()
    parser.feed(html)
    external = [r for r in parser.refs if _is_external(r[2])]
    assert external == [], f"external URLs in dashboard: {external}"
    for host in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com", "fonts.googleapis.com", "fonts.gstatic.com"):
        assert host not in html
    assert "@import" not in html
    assert not re.search(r"url\(\s*['\"]?(?:https?:)?//", html), "external url() in CSS"

    for lib in LIBRARIES:
        js = (VENDOR_DIR / lib["script"]).read_text(encoding="utf-8")
        assert f"<script>{js}</script>" in html, f"{lib['name']} not inlined verbatim"


def test_generated_dashboard_embeds_font_faces(tmp_path) -> None:
    seed_sample_db(tmp_path / "watchtower.db")
    html = generate_dashboard(tmp_path).read_text(encoding="utf-8")
    assert html.count("@font-face") == sum(len(font["faces"]) for font in FONTS)
    for font in FONTS:
        assert f'font-family: "{font["family"]}";' in html
        for face in font["faces"]:
            data = (VENDOR_DIR / face["file"]).read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            assert f"url(data:font/woff2;base64,{b64}) format(\"woff2\")" in html
            assert f"font-weight: {int(face['weight'])};" in html
            assert f"font-style: {face['style']};" in html


def test_generator_fails_closed_on_vendor_hash_mismatch(monkeypatch, tmp_path) -> None:
    import scripts.generate_dashboard_html as gen

    bad = json.loads(json.dumps(LIBRARIES))
    bad[0]["files"][bad[0]["script"]] = "0" * 64
    monkeypatch.setattr(gen, "load_vendor_manifest", lambda: bad)
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        gen._vendor_script_tags()


def test_generator_fails_closed_on_font_hash_mismatch(monkeypatch) -> None:
    import scripts.generate_dashboard_html as gen

    bad = json.loads(json.dumps(FONTS))
    first_file = next(iter(bad[0]["files"]))
    bad[0]["files"][first_file] = "0" * 64
    monkeypatch.setattr(gen, "load_vendor_fonts", lambda: bad)
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        gen._vendor_font_face_css()
