// Vercel Serverless Function — Agency Specialists Roster
module.exports = (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  if (req.method === "OPTIONS") return res.status(200).end();

  res.status(200).json({
    status: "ok",
    agents: [
      { id: "agent_architect", name: "System Architect", role: "High-order distributed systems & edge topology", status: "ready", model: "Qwen 2.5 Coder 32B" },
      { id: "agent_coder", name: "Autonomous Coder", role: "Full-stack code generation, refactoring, and test suite creation", status: "active", model: "Qwen 2.5 Coder 32B" },
      { id: "agent_reasoner", name: "Deep Reasoner", role: "Mathematical proofs, algorithmic logic & verification", status: "ready", model: "DeepSeek R1 Distill" },
      { id: "agent_executive", name: "Executive Triage", role: "Deal negotiation, financial forecasting & operational dispatch", status: "ready", model: "Llama 3.3 70B" },
      { id: "agent_sre", name: "Site Reliability Engineer", role: "Zero-localhost serverless health, memory bounds & Vercel edge telemetry", status: "monitoring", model: "Mistral Nemo 12B" },
      { id: "agent_hf_curator", name: "Hugging Face Model Curator", role: "Dynamic open-weights model discovery, benchmark tracking & adaptation", status: "active", model: "Hugging Face API" }
    ]
  });
};
