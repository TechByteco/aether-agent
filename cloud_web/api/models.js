// Vercel Serverless Function — Models Catalog
module.exports = (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");

  res.status(200).json({
    active_model: "Qwen/Qwen2.5-Coder-32B-Instruct",
    cloud_tier: "100% Free Serverless Edge Compute",
    local_models: [
      {
        id: "Qwen/Qwen2.5-Coder-32B-Instruct",
        name: "Qwen 2.5 Coder 32B",
        provider: "Hugging Face / Open Weights",
        size: "32B Parameters",
        specialty: "High-order autonomous coding & architecture synthesis",
        status: "ready"
      },
      {
        id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        name: "DeepSeek R1 Distill",
        provider: "Hugging Face / Open Weights",
        size: "1.5B Dense Reasoning",
        specialty: "Frontier mathematical and algorithmic tree-of-thought",
        status: "ready"
      },
      {
        id: "meta-llama/Llama-3.3-70B-Instruct",
        name: "Llama 3.3 70B",
        provider: "Hugging Face / Open Weights",
        size: "70B Parameters",
        specialty: "Executive operations, triage & autonomous agency",
        status: "ready"
      },
      {
        id: "mistralai/Mistral-Nemo-Instruct-2407",
        name: "Mistral Nemo 12B",
        provider: "Hugging Face / Open Weights",
        size: "12B / 128k Context",
        specialty: "High-speed multi-lingual long-context reasoning",
        status: "ready"
      }
    ],
    cloud_models: [
      {
        id: "gemini-2.0-flash",
        name: "Google Gemini 2.0 Flash",
        provider: "Google AI Studio",
        specialty: "Sub-second multimodal reasoning and structured outputs",
        context: "1M Context",
        status: "online",
        icon: "⚡"
      },
      {
        id: "gemini-1.5-pro",
        name: "Google Gemini 1.5 Pro",
        provider: "Google DeepMind",
        specialty: "Deep code analysis, document ingestion and strategic planning",
        context: "2M Context",
        status: "online",
        icon: "🧠"
      },
      {
        id: "deepseek",
        name: "DeepSeek V3 / R1",
        provider: "Hugging Face Cloud Router",
        specialty: "Frontier reasoning and logic synthesis",
        context: "64k Context",
        status: "online",
        icon: "🔮"
      },
      {
        id: "qwen",
        name: "Qwen 2.5 Coder",
        provider: "Hugging Face Cloud Router",
        specialty: "End-to-end full-stack software development",
        context: "32k Context",
        status: "online",
        icon: "💻"
      }
    ]
  });
};
