"""
Unit Tests for LEON Growth, UI Assignment, Lead Prospecting, Cold Outreach & SEO Engine
========================================================================================
"""

import unittest
from aether.brain.leon_growth_engine import (
    leon_growth_engine,
    UIArchetype,
    TargetAudienceType,
    LeadProfile,
    tool_leon_assign_ui_archetype,
    tool_leon_search_and_qualify_leads,
    tool_leon_draft_personalized_outreach,
    tool_leon_generate_seo_and_web_spec,
)


class TestLEONGrowthEngine(unittest.TestCase):
    def setUp(self):
        self.venture_name = "DevPulse Cloud"
        self.niche = "developer_tools"
        self.value_prop = "Automated real-time CI/CD performance and latency bottleneck profiling for microservices."

    def test_ui_archetype_assignment(self):
        """Test assigning UI archetype for developer tools venture."""
        theme = leon_growth_engine.assign_ui_archetype_for_venture(
            venture_name=self.venture_name,
            niche=self.niche,
            target_audience="DevOps & Backend Engineers",
        )
        self.assertEqual(theme.archetype, UIArchetype.LINEAR_DARK)
        self.assertIn("bg", theme.tailwind_classes)
        self.assertIn("card", theme.tailwind_classes)
        self.assertIn("btn_primary", theme.tailwind_classes)

        # Test agency niche maps to editorial luxury
        agency_theme = leon_growth_engine.assign_ui_archetype_for_venture(
            venture_name="Apex Studio",
            niche="agency_services",
            target_audience="Enterprise Executives",
        )
        self.assertEqual(agency_theme.archetype, UIArchetype.EDITORIAL_LUXURY)

    def test_lead_prospecting_and_qualification(self):
        """Test lead discovery and qualification."""
        leads = leon_growth_engine.search_and_qualify_leads(
            venture_name=self.venture_name,
            niche=self.niche,
            value_prop=self.value_prop,
            target_audience_type=TargetAudienceType.B2B_SMB,
            count=2,
        )
        self.assertTrue(len(leads) >= 1)
        lead = leads[0]
        self.assertIsInstance(lead, LeadProfile)
        self.assertTrue(lead.qualification_score >= 70)
        self.assertTrue(len(lead.pain_point) > 5)

    def test_cold_outreach_drafting(self):
        """Test personalized outreach generation for B2B and consumer leads."""
        lead = LeadProfile(
            id="test_lead_01",
            name="Alex Mercer",
            organization="CloudScale Inc",
            role_or_title="Lead DevOps Architect",
            channel="email",
            contact_handle="alex@cloudscale.io",
            audience_type=TargetAudienceType.B2B_SMB,
            pain_point="CI/CD pipelines taking 45+ minutes per build",
            qualification_score=95,
            custom_notes="High urgency lead"
        )
        msg = leon_growth_engine.draft_personalized_outreach(
            lead=lead,
            venture_name=self.venture_name,
            value_prop=self.value_prop,
        )
        self.assertIn("Alex", msg.recipient_name)
        self.assertIsNotNone(msg.message_body)
        self.assertTrue(len(msg.call_to_action) > 5)
        self.assertIn("UNSUBSCRIBE", msg.compliance_disclaimer)

    def test_seo_and_web_spec_generation(self):
        """Test SEO metadata, Schema.org JSON-LD, and keyword clusters."""
        seo = leon_growth_engine.generate_seo_and_web_spec(
            venture_name=self.venture_name,
            niche=self.niche,
            value_prop=self.value_prop,
        )
        self.assertTrue(len(seo.meta_title) > 0)
        self.assertTrue(len(seo.meta_description) > 0)
        self.assertTrue(len(seo.focus_keywords) >= 3)
        self.assertEqual(seo.json_ld_schema.get("@type"), "SoftwareApplication")
        self.assertIn("og:title", seo.opengraph_tags)
        self.assertIn("twitter:card", seo.twitter_card_tags)
        self.assertTrue(len(seo.content_cluster_topics) >= 2)

    def test_native_tool_wrappers(self):
        """Test native tool functions dispatched via ReWOO and agent loops."""
        ui_res = tool_leon_assign_ui_archetype("FinEdge", "fintech")
        self.assertIn("VIBRANT_FINTECH", ui_res)

        lead_res = tool_leon_search_and_qualify_leads(self.venture_name, self.niche, self.value_prop, count=2)
        self.assertIn("LEON Lead Prospector", lead_res)

        outreach_res = tool_leon_draft_personalized_outreach(
            lead_name="Marcus Vance",
            venture_name=self.venture_name,
            value_prop=self.value_prop,
            channel="linkedin"
        )
        self.assertIn("LEON Cold Outreach Generator", outreach_res)

        seo_res = tool_leon_generate_seo_and_web_spec(self.venture_name, self.niche, self.value_prop)
        self.assertIn("LEON Programmatic SEO Matrix", seo_res)


if __name__ == "__main__":
    unittest.main()
