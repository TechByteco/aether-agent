// Vercel Serverless Function — Hugging Face Model Hub Explorer
// Fetches models directly from Hugging Face Hub API using free cloud compute

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  const query = req.query.search || req.query.q || "coder";
  const limit = Math.min(parseInt(req.query.limit || "12", 10), 30);

  const curatedModels = [
    {
      id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
      name: "DeepSeek-R1 Distill Qwen 1.5B",
      author: "deepseek-ai",
      pipeline_tag: "text-generation",
      description: "State-of-the-art open reasoning model distilled from DeepSeek-R1.",
      tags: ["reasoning", "math", "code", "open-weights"],
      hf_url: "https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
      tier: "free_cloud_inference",
      recommended: true
    },
    {
      id: "Qwen/Qwen2.5-Coder-32B-Instruct",
      name: "Qwen 2.5 Coder 32B Instruct",
      author: "Qwen",
      pipeline_tag: "text-generation",
      description: "Premier open-source code generation and architectural synthesis model.",
      tags: ["coding", "architecture", "multi-language"],
      hf_url: "https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct",
      tier: "free_cloud_inference",
      recommended: true
    },
    {
      id: "meta-llama/Llama-3.3-70B-Instruct",
      name: "Llama 3.3 70B Instruct",
      author: "meta-llama",
      pipeline_tag: "text-generation",
      description: "Meta flagship 70B open weights model for complex reasoning and enterprise autonomy.",
      tags: ["general", "executive", "reasoning"],
      hf_url: "https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct",
      tier: "free_cloud_inference",
      recommended: true
    },
    {
      id: "mistralai/Mistral-Nemo-Instruct-2407",
      name: "Mistral Nemo 12B Instruct",
      author: "mistralai",
      pipeline_tag: "text-generation",
      description: "12B state-of-the-art multilingual model built by Mistral AI and NVIDIA with 128k context.",
      tags: ["fast", "128k-context", "multilingual"],
      hf_url: "https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407",
      tier: "free_cloud_inference",
      recommended: false
    },
    {
      id: "google/gemma-2-9b-it",
      name: "Gemma 2 9B Instruct",
      author: "google",
      pipeline_tag: "text-generation",
      description: "Google DeepMind open research weights built from Gemini technology.",
      tags: ["google", "deepmind", "compact"],
      hf_url: "https://huggingface.co/google/gemma-2-9b-it",
      tier: "free_cloud_inference",
      recommended: false
    },
    {
      id: "microsoft/Phi-3.5-mini-instruct",
      name: "Phi-3.5 Mini 3.8B Instruct",
      author: "microsoft",
      pipeline_tag: "text-generation",
      description: "High-density lightweight 3.8B model with 128k context window by Microsoft Research.",
      tags: ["lightweight", "mobile", "efficient"],
      hf_url: "https://huggingface.co/microsoft/Phi-3.5-mini-instruct",
      tier: "free_cloud_inference",
      recommended: false
    }
  ];

  try {
    // Also try live query to Hugging Face Hub REST API
    const hfApiUrl = `https://huggingface.co/api/models?search=${encodeURIComponent(query)}&sort=downloads&direction=-1&limit=${limit}`;
    const hfRes = await fetch(hfApiUrl, {
      headers: { "User-Agent": "AETHER-Sovereign-Cloud/1.0" },
      signal: AbortSignal.timeout(4000)
    });

    if (hfRes.ok) {
      const liveData = await hfRes.json();
      const liveModels = liveData.map(m => ({
        id: m.id || m.modelId,
        name: (m.id || "").split("/")[1] || m.id,
        author: (m.id || "").split("/")[0] || "community",
        downloads: m.downloads || 0,
        likes: m.likes || 0,
        pipeline_tag: m.pipeline_tag || "text-generation",
        hf_url: `https://huggingface.co/${m.id}`,
        tags: m.tags ? m.tags.slice(0, 5) : []
      }));

      return res.status(200).json({
        source: "huggingface_hub_live",
        query: query,
        curated_models: curatedModels,
        hub_results: liveModels,
        count: liveModels.length
      });
    }
  } catch (err) {
    // Fallback to curated catalog
  }

  res.status(200).json({
    source: "huggingface_curated",
    query: query,
    curated_models: curatedModels,
    hub_results: curatedModels,
    count: curatedModels.length
  });
};
