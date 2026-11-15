// Vercel Serverless Function — Workspace & Goals Router
let defaultGoals = [
  "1. Maintain 100% online cloud sovereignty 24/7 on Vercel Serverless Edge.",
  "2. Execute all AI reasoning and continuous evolution using free cloud RAM and CPU.",
  "3. Dynamically discover and leverage open weights models from Hugging Face Hub (Qwen 2.5 Coder, DeepSeek R1).",
  "4. Monitor and advance enterprise CRM deals (₹3,00,000 active pipeline).",
  "5. Provide instant pair programming and cloud execution in the web terminal."
].join("\n");

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();

  const url = req.url || "";

  if (url.includes("goals")) {
    if (req.method === "POST") {
      let body = {};
      try {
        body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
      } catch {}
      if (body.goals) defaultGoals = body.goals;
      return res.status(200).json({ status: "saved", goals: defaultGoals });
    }
    return res.status(200).json({ status: "ok", goals: defaultGoals });
  }

  // Default: Workspace Files
  res.status(200).json({
    status: "ok",
    repository: "https://github.com/TechByteco/aether-agent",
    branch: "main",
    hosting: "Vercel Global Edge (100% Online)",
    files: [
      { name: "cloud_web/api/chat.js", path: "cloud_web/api/chat.js", size: "3.7 KB", type: "file" },
      { name: "cloud_web/api/status.js", path: "cloud_web/api/status.js", size: "2.6 KB", type: "file" },
      { name: "cloud_web/api/huggingface.js", path: "cloud_web/api/huggingface.js", size: "4.6 KB", type: "file" },
      { name: "cloud_web/api/code.js", path: "cloud_web/api/code.js", size: "4.8 KB", type: "file" },
      { name: "cloud_web/api/models.js", path: "cloud_web/api/models.js", size: "2.6 KB", type: "file" },
      { name: "cloud_web/api/crm.js", path: "cloud_web/api/crm.js", size: "2.5 KB", type: "file" },
      { name: "cloud_web/api/owner.js", path: "cloud_web/api/owner.js", size: "3.5 KB", type: "file" },
      { name: "cloud_web/api/email.js", path: "cloud_web/api/email.js", size: "3.2 KB", type: "file" },
      { name: "cloud_web/api/evolution.js", path: "cloud_web/api/evolution.js", size: "2.8 KB", type: "file" },
      { name: "cloud_web/api/agency.js", path: "cloud_web/api/agency.js", size: "1.5 KB", type: "file" },
      { name: "cloud_web/api/leon.js", path: "cloud_web/api/leon.js", size: "3.2 KB", type: "file" },
      { name: "cloud_web/app.js", path: "cloud_web/app.js", size: "115 KB", type: "file" },
      { name: "cloud_web/index.html", path: "cloud_web/index.html", size: "77 KB", type: "file" },
      { name: "cloud_web/style.css", path: "cloud_web/style.css", size: "52 KB", type: "file" },
      { name: "cloud_web/vercel.json", path: "cloud_web/vercel.json", size: "0.8 KB", type: "file" }
    ]
  });
};
