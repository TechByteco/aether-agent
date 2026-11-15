"""
Unit & Integration Test Suite for AETHER Instinct Concierge & Errand Engine
==========================================================================
Tests travel concierge, flight synthesis, bill negotiation, restaurant booking,
and Reflexion-guided autonomous task execution.
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.channels.instinct_concierge import instinct_concierge


class TestInstinctConcierge(unittest.TestCase):
    """Test suite for Instinct Concierge autonomous errand engine."""

    def test_flight_and_travel_concierge(self):
        """Verify flight and travel itinerary discovery."""
        res = instinct_concierge.plan_travel_and_flights(
            origin="Delhi",
            destination="Mumbai",
            date="Tomorrow Morning",
            preferences="Direct flight, morning departure under ₹6000"
        )
        self.assertEqual(res.get("category"), "travel")
        self.assertTrue(len(res.get("summary", "")) > 50)

    def test_bill_negotiation_concierge(self):
        """Verify 3-step aggressive bill negotiation script generator."""
        res = instinct_concierge.negotiate_bill(
            provider="Airtel Broadband",
            bill_amount=1499.0,
            service_type="Fiber Internet"
        )
        self.assertEqual(res.get("category"), "bill_negotiation")
        self.assertIn("Airtel", res.get("provider", ""))
        self.assertTrue(len(res.get("script", "")) > 50)

    def test_restaurant_reservation_concierge(self):
        """Verify dining and reservation recommendations."""
        res = instinct_concierge.find_restaurant_reservation(
            city_or_area="Indiranagar, Bangalore",
            cuisine="Italian & Wine Bar",
            date_time="Friday 8:30 PM",
            party_size=4
        )
        self.assertEqual(res.get("category"), "reservation")
        self.assertTrue(len(res.get("summary", "")) > 50)

    def test_execute_errand_routing(self):
        """Verify natural language errand execution."""
        # Travel errand
        html_out, keyboard = instinct_concierge.execute_errand("Find me a flight from Bangalore to Goa this weekend")
        self.assertIn("TRAVEL & FLIGHT CONCIERGE", html_out)
        self.assertIsNotNone(keyboard)
        self.assertIn("inline_keyboard", keyboard)


if __name__ == "__main__":
    unittest.main()
