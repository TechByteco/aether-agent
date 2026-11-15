// Vercel Serverless Function — CRM Deals & Portfolio Ventures
module.exports = (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");

  res.status(200).json({
    status: "ok",
    pipeline: {
      total_pipeline_value: 300000,
      total_deals: 2,
      currency: "INR",
      deals: [
        {
          deal_id: "deal_apexfintech_101",
          company_name: "ApexFintech Ltd",
          contact_person: "Siddharth Mehta",
          contact_email: "siddharth@apexfintech.io",
          deal_value: 180000,
          currency: "INR",
          stage: "demo_scheduled",
          meeting_link: "meet.google.com/aet-ape-567",
          created_at: "2026-10-18T10:00:00Z"
        },
        {
          deal_id: "deal_1792234567_testcorp",
          company_name: "TestCorp Global",
          contact_person: "Vikram Singh",
          contact_email: "vikram@testcorp.com",
          deal_value: 120000,
          currency: "INR",
          stage: "proposal_sent",
          created_at: "2026-10-18T14:30:00Z"
        }
      ]
    },
    ventures: [
      { name: "CloudFlow AI", status: "active", revenue: "₹24,000", url: "https://cloudflow-3efl38x0f-saali.vercel.app" },
      { name: "LeadPulse Pro", status: "active", revenue: "₹38,000", url: "https://leadpulse-r8hemyai6-saali.vercel.app" },
      { name: "ApexStudio AI", status: "active", revenue: "₹45,000", url: "https://apexstudio-egwq9v3v9-saali.vercel.app" },
      { name: "CogniGuard Cyber", status: "active", revenue: "₹18,500", url: "https://cogniguard-cyber-iuuuxzino-saali.vercel.app" },
      { name: "Aether Sovereign OS", status: "sovereign", revenue: "₹45,000", url: "https://aether-sovereign-os.vercel.app" }
    ],
    verified_settlements: [
      { utr: "RZP9823410294", amount: 45000, status: "settled", date: "2026-10-17" }
    ]
  });
};
