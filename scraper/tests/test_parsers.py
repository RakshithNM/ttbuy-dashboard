"""Run every plugin's parse() on a saved copy of its page.

The fixtures are frozen, so these tests catch a code change that breaks a
parser, not a bank that changes its live page (check_stale.py catches that).
When a bank does change its page, fix the parser, then refresh the fixture
with save_fixtures.py.

    .venv/bin/python3 -m unittest discover -s scraper/tests -t .
"""
import gzip
import json
import os
import unittest
from unittest import mock

from ..banks import REGISTRY, remitly
from .save_fixtures import EXPECTED_PATH, REMITLY_EXTRA_CURRENCIES, expected_rows, fixture_path


def read_fixture(plugin, suffix=""):
    path = fixture_path(plugin, suffix)
    if path.endswith(".pdf.gz"):
        with gzip.open(path, "rb") as f:
            return f.read()
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read()


class ParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(EXPECTED_PATH) as f:
            cls.expected = json.load(f)

    def test_every_plugin_has_a_fixture(self):
        self.assertEqual(sorted(REGISTRY), sorted(self.expected))
        for plugin in REGISTRY.values():
            self.assertTrue(os.path.exists(fixture_path(plugin)), plugin.slug)

    def test_parse_reads_the_saved_rates(self):
        for slug, plugin in REGISTRY.items():
            with self.subTest(bank=slug):
                parsed = self.parse(plugin)
                self.assertTrue(parsed, "parse() found no rates")
                self.assertEqual(expected_rows(plugin, parsed), self.expected[slug])

    def parse(self, plugin):
        content = read_fixture(plugin)
        if plugin.slug != "remitly":
            return plugin.parse(content, plugin.live_url)

        pages = {
            remitly._CURRENCY_URLS[currency]: read_fixture(plugin, f"_{currency}")
            for currency in REMITLY_EXTRA_CURRENCIES
        }
        with mock.patch.object(
            remitly.requests, "get", side_effect=lambda url, **_: mock.Mock(ok=True, text=pages[url])
        ):
            return plugin.parse(content, plugin.live_url)


if __name__ == "__main__":
    unittest.main()
