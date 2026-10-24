"""Tests for the static portfolio site.

Unit tests parse index.html and style.css directly. Integration tests serve
the folder locally and drive headless Chromium with Playwright at phone,
tablet and desktop widths.

Setup once:  pip install playwright lxml && playwright install chromium
Run:         python -m unittest discover -s tests -v
"""
import functools
import http.server
import json
import pathlib
import re
import threading
import unittest

import lxml.html

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")
DOC = lxml.html.fromstring(HTML)
SITE_URL = "https://pratikshac15.github.io/"


def meta(attr, value):
    found = DOC.xpath(f"//meta[@{attr}='{value}']/@content")
    return found[0] if found else None


def text_of(element_id):
    el = DOC.get_element_by_id(element_id, None)
    return None if el is None else " ".join(el.text_content().split())


# ---------------------------------------------------------------- unit tests

class StructureTests(unittest.TestCase):
    def test_single_h1_with_name(self):
        h1s = DOC.xpath("//h1")
        self.assertEqual(len(h1s), 1)
        self.assertIn("PRATIKSHA", h1s[0].text_content().upper())

    def test_ids_unique(self):
        ids = DOC.xpath("//@id")
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_internal_anchors_resolve(self):
        ids = set(DOC.xpath("//@id"))
        for href in DOC.xpath("//a/@href"):
            if href.startswith("#") and len(href) > 1:
                self.assertIn(href[1:], ids, f"dangling anchor {href}")

    def test_nav_covers_every_major_section(self):
        targets = set(DOC.xpath("//*[contains(@class,'navlinks')]//a/@href"))
        for sec in ("#work", "#builds", "#papers", "#presentations", "#recognition", "#contact"):
            self.assertIn(sec, targets, f"nav missing {sec}")

    def test_images_have_alt_and_dimensions(self):
        for img in DOC.xpath("//img"):
            src = img.get("src")
            self.assertTrue(img.get("alt"), f"img without alt: {src}")
            self.assertTrue(img.get("width") and img.get("height"), f"img without size: {src}")

    def test_external_links_open_safely(self):
        for a in DOC.xpath("//a[@target='_blank']"):
            self.assertIn("noopener", (a.get("rel") or "").split(), a.get("href"))


class LocalFileTests(unittest.TestCase):
    def test_every_local_reference_exists(self):
        refs = set()
        for xp in ("//a/@href", "//img/@src", "//link/@href", "//script/@src"):
            refs.update(r for r in DOC.xpath(xp) if not re.match(r"^(https?:|mailto:|#|data:)", r))
        missing = sorted(r for r in refs if not (ROOT / r).is_file())
        self.assertEqual(missing, [], f"broken local links: {missing}")


class SeoTests(unittest.TestCase):
    def test_open_graph_tags(self):
        for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
            self.assertTrue(meta("property", prop), f"missing {prop}")

    def test_og_image_is_absolute_and_exists_locally(self):
        url = meta("property", "og:image")
        self.assertTrue(url.startswith(SITE_URL))
        self.assertTrue((ROOT / url[len(SITE_URL):]).is_file())

    def test_twitter_card_and_canonical(self):
        self.assertTrue(meta("name", "twitter:card"))
        self.assertEqual(DOC.xpath("//link[@rel='canonical']/@href"), [SITE_URL])

    def test_favicon_present_and_exists(self):
        icons = DOC.xpath("//link[contains(@rel,'icon')]/@href")
        self.assertTrue(icons, "no favicon link")
        self.assertTrue((ROOT / icons[0]).is_file())

    def test_json_ld_person(self):
        blocks = DOC.xpath("//script[@type='application/ld+json']/text()")
        self.assertTrue(blocks, "no JSON-LD")
        data = json.loads(blocks[0])
        self.assertEqual(data["@type"], "Person")
        self.assertEqual(data["name"], "Pratiksha Chaudhari")
        self.assertTrue(any("linkedin.com" in s for s in data["sameAs"]))
        self.assertTrue(any("github.com" in s for s in data["sameAs"]))


class ContentTests(unittest.TestCase):
    def test_open_to_roles_signal_in_hero(self):
        self.assertIn("open to", text_of("home").lower())

    def test_builds_link_public_repos(self):
        builds = DOC.get_element_by_id("builds", None)
        self.assertIsNotNone(builds, "no #builds section")
        hrefs = builds.xpath(".//a/@href")
        for repo in ("llm-fake-review-attacks", "elliptic-fraud-gnn", "IssueFlow", "enterprise-ai-platform"):
            self.assertIn(f"https://github.com/pratikshac15/{repo}", hrefs)

    def test_toolbox_section_lists_core_skills(self):
        tb = text_of("toolbox")
        self.assertIsNotNone(tb, "no #toolbox section")
        for skill in ("PyTorch", "Python", "Docker", "AWS", "Transformers"):
            self.assertIn(skill, tb)


class CssTests(unittest.TestCase):
    def test_reduced_motion_respected(self):
        self.assertIn("prefers-reduced-motion", CSS)

    def test_full_bleed_margins_match_padding(self):
        """Full-bleed stories use negative margins; they must equal the container
        padding at each breakpoint or the page scrolls sideways."""
        base = CSS.split("@media")[0]
        pad = re.search(r"\.story-projects\{padding:0 ([\d.]+)vw\}", base).group(1)
        for m in re.findall(r"margin:0 -([\d.]+)vw", base):
            self.assertEqual(m, pad)
        mobile = re.search(r"@media\(max-width:700px\)\{(.*?)\n\}", CSS, re.S).group(1)
        mpad = re.search(r"\.story-projects\{padding:0 ([\d.]+)vw\}", mobile).group(1)
        for m in re.findall(r"margin:0 -([\d.]+)vw", mobile):
            self.assertEqual(m, mpad)


# ---------------------------------------------------------- integration tests

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
        handler.log_message = lambda *a, **k: None
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.httpd.shutdown()

    def open(self, width, height=900, **ctx):
        context = self.browser.new_context(viewport={"width": width, "height": height}, **ctx)
        self.addCleanup(context.close)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: errors.append(f"{r.status} {r.url}")
                if r.status >= 400 and r.url.startswith(self.url) else None)
        page.goto(self.url)
        page.wait_for_load_state("load")
        return page, errors

    def test_no_horizontal_scroll(self):
        for width in (360, 390, 768, 1024, 1440):
            with self.subTest(width=width):
                page, _ = self.open(width)
                scroll = page.evaluate("document.documentElement.scrollWidth")
                self.assertLessEqual(scroll, width, f"{scroll}px wide at {width}px")

    def test_no_js_errors_or_local_404s(self):
        page, errors = self.open(1440)
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(300)
        self.assertEqual(errors, [])

    def test_thought_orbit_switches_topic(self):
        page, _ = self.open(1440)
        page.click("button[data-key='SCALE']")
        self.assertEqual(page.inner_text("#thoughtKey"), "SCALE")
        self.assertEqual(page.get_attribute("button[data-key='SCALE']", "aria-pressed"), "true")
        self.assertEqual(page.get_attribute("button[data-key='PERCEPTION']", "aria-pressed"), "false")

    def test_mobile_menu_opens_and_navigates(self):
        page, _ = self.open(390, 844)
        toggle = page.locator(".menu-toggle")
        self.assertTrue(toggle.is_visible(), "no visible menu button on phones")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        toggle.click()
        self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
        link = page.locator(".navlinks a[href='#builds']")
        self.assertTrue(link.is_visible())
        link.click()
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false", "menu should close")
        # wait for smooth scrolling to settle, then check the section sits just under the bar
        page.wait_for_function(
            "() => Math.abs(document.getElementById('builds').getBoundingClientRect().top) < 120",
            timeout=5000)
        top = page.evaluate("document.getElementById('builds').getBoundingClientRect().top")
        bar = page.evaluate("document.querySelector('.nav').getBoundingClientRect().bottom")
        self.assertGreaterEqual(top, bar - 1, "section heading hidden under the fixed menu bar")

    def test_escape_closes_mobile_menu(self):
        page, _ = self.open(390, 844)
        page.click(".menu-toggle")
        page.keyboard.press("Escape")
        self.assertEqual(page.get_attribute(".menu-toggle", "aria-expanded"), "false")

    def test_desktop_hides_menu_button(self):
        page, _ = self.open(1440)
        self.assertFalse(page.locator(".menu-toggle").is_visible())
        self.assertTrue(page.locator(".navlinks a[href='#builds']").is_visible())

    def test_reduced_motion_shows_content_immediately(self):
        page, _ = self.open(1440, reduced_motion="reduce")
        opacity = page.evaluate("getComputedStyle(document.querySelector('.build')).opacity")
        self.assertEqual(float(opacity), 1.0)


if __name__ == "__main__":
    unittest.main()
