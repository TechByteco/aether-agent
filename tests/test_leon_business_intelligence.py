"""Unit tests for LEON Business Intelligence (ideation, brand studio, lead discovery)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aether.brain.leon_business_intelligence import (
    BrandStudio,
    IdeationEngine,
    LeadDiscovery,
    LEONBusinessIntelligence,
    _hue_distance,
)

PORTFOLIO = [
    ("Aether Sovereign OS", "productivity_saas"),
    ("CogniGuard Cyber", "cybersecurity"),
    ("CloudFlow AI", "developer_tools"),
    ("LeadPulse Pro", "agency_services"),
    ("ApexStudio AI", "agency_services"),
]

SAMPLE_HTML = """<html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap" rel="stylesheet">
<script>
    tailwind.config = { theme: { extend: { fontFamily: { heading: [Inter] } } } }
</script>
</head><body class="antialiased"><div class="bg-indigo-600 text-cyan-400 border-indigo-500/50"></div></body></html>"""


class TestIdeation(unittest.TestCase):
    def test_ideas_ranked_and_complete(self):
        ideas = IdeationEngine().generate_ideas("cybersecurity", "SMBs get hacked", count=5)
        self.assertEqual(len(ideas), 5)
        scores = [i.total_score for i in ideas]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for i in ideas:
            self.assertEqual(len(i.core_tools), 3)
            self.assertTrue(i.free_lead_magnet_tool)
            self.assertGreaterEqual(len(i.validation_steps), 3)

    def test_tool_guidelines(self):
        g = IdeationEngine().tool_guidelines("developer_tools")
        self.assertIn("free_lead_magnet_tools", g)
        self.assertTrue(g["build_order"][0].startswith("1. Free tool"))


class TestBrandStudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = BrandStudio(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_portfolio_brands_are_distinct(self):
        brands = [self.studio.get_or_create(n, niche) for n, niche in PORTFOLIO]
        hues = [b.primary_hue for b in brands]
        for i in range(len(hues)):
            for j in range(i + 1, len(hues)):
                self.assertGreaterEqual(_hue_distance(hues[i], hues[j]), 28)
        # Same-niche businesses still get different fonts
        self.assertNotEqual(brands[3].font_heading, brands[4].font_heading)

    def test_brand_persistence_is_stable(self):
        b1 = self.studio.get_or_create("CloudFlow AI", "developer_tools")
        b2 = BrandStudio(Path(self.tmp.name)).get_or_create("CloudFlow AI", "developer_tools")
        self.assertEqual(b1.primary_scale, b2.primary_scale)

    def test_customize(self):
        self.studio.get_or_create("CloudFlow AI", "developer_tools")
        b = self.studio.customize("cloudflow-ai", primary_hex="#FF5500", font_heading="Sora")
        self.assertEqual(b.primary, "#FF5500")
        self.assertEqual(b.font_heading, "Sora")
        self.assertTrue(b.customized)
        with self.assertRaises(ValueError):
            self.studio.customize("cloudflow-ai", primary_hex="red")

    def test_apply_to_html(self):
        b = self.studio.get_or_create("CloudFlow AI", "developer_tools")
        html = self.studio.apply_to_html(SAMPLE_HTML, b)
        self.assertNotIn("indigo-", html)
        self.assertNotIn("cyan-", html)
        self.assertIn("bg-brand-600", html)
        self.assertIn("text-accent-400", html)
        self.assertIn(b.primary_scale["600"], html)
        self.assertIn(b.font_heading.replace(" ", "+"), html)
        self.assertNotIn("[Inter]", html)  # broken unquoted JS font config is replaced
        self.assertIn('data-brand="cloudflow-ai"', html)


class TestLeadDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ld = LeadDiscovery(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_intent_scoring(self):
        hi, hits = self.ld.score_intent("Can anyone recommend an alternative to Snyk? Willing to pay.")
        lo, _ = self.ld.score_intent("Here is my weekend photo")
        self.assertGreaterEqual(hi, 60)
        self.assertTrue(hits)
        self.assertEqual(lo, 0)

    def test_playbook(self):
        pb = self.ld.build_playbook("CogniGuard Cyber", "cybersecurity", "security for SMBs")
        for key in ("ideal_customer_profile", "search_queries", "outreach_sequence", "compliance"):
            self.assertIn(key, pb)

    def test_discover_signals_with_mocked_sources(self):
        fake = [{"source": "reddit/r/smallbusiness", "title": "Looking for a security tool for my store",
                 "url": "https://reddit.com/x1", "author": "u1", "text": "Any recommend? budget is small"},
                {"source": "hackernews", "title": "Show HN: my cat", "url": "https://hn/x2",
                 "author": "u2", "text": "cute"}]
        with mock.patch.object(LeadDiscovery, "_search_reddit", return_value=fake), \
             mock.patch.object(LeadDiscovery, "_search_hn", return_value=[]):
            sigs = self.ld.discover_signals("CogniGuard Cyber", "cybersecurity")
        self.assertEqual(len(sigs), 1)
        self.assertEqual(sigs[0].url, "https://reddit.com/x1")
        self.assertEqual(len(self.ld.list_signals("cogniguard-cyber")), 1)


class TestBlueprint(unittest.TestCase):
    def test_blueprint_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            bi = LEONBusinessIntelligence(Path(tmp))
            bp = bi.build_blueprint("LeadPulse Pro", "agency_services", "B2B leads", live_leads=False)
            self.assertTrue((bi.out_dir / "leadpulse-pro.md").exists())
            self.assertEqual(len(bp["top_ideas"]), 5)
            self.assertIn("primary_scale", bp["brand"])


if __name__ == "__main__":
    unittest.main()
