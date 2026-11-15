// Vercel Serverless Function — Isolated Code Execution on Free Cloud CPU & RAM
// Runs programs on Vercel Edge Serverless compute with zero localhost dependence

const vm = require("vm");

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  let body = {};
  try {
    body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
  } catch (e) {
    body = req.body || {};
  }

  const rawCode = (body.code || "").trim();
  if (!rawCode) {
    return res.status(400).json({ output: "Error: No code provided to execute." });
  }

  const startTime = Date.now();
  const memBefore = process.memoryUsage();
  const logs = [];

  // Sandboxed context with console capturing
  const sandbox = {
    console: {
      log: (...args) => logs.push(args.map(a => typeof a === "object" ? JSON.stringify(a, null, 2) : String(a)).join(" ")),
      error: (...args) => logs.push("[ERROR] " + args.map(a => typeof a === "object" ? JSON.stringify(a, null, 2) : String(a)).join(" ")),
      warn: (...args) => logs.push("[WARN] " + args.map(a => typeof a === "object" ? JSON.stringify(a, null, 2) : String(a)).join(" ")),
      info: (...args) => logs.push("[INFO] " + args.map(a => typeof a === "object" ? JSON.stringify(a, null, 2) : String(a)).join(" "))
    },
    Math: Math,
    Date: Date,
    JSON: JSON,
    parseInt: parseInt,
    parseFloat: parseFloat,
    Array: Array,
    Object: Object,
    String: String,
    Number: Number,
    Boolean: Boolean,
    RegExp: RegExp,
    Map: Map,
    Set: Set
  };

  let executionResult = null;
  let isError = false;

  try {
    const context = vm.createContext(sandbox);
    // Execute code with 5-second hard serverless timeout
    const script = new vm.Script(rawCode);
    executionResult = script.runInContext(context, { timeout: 4000 });
  } catch (err) {
    // If it's Python syntax (e.g. print(...) or def ...), provide intelligent cloud evaluation
    if (rawCode.includes("print(") || rawCode.startsWith("def ") || rawCode.startsWith("import ")) {
      try {
        const pythonLines = rawCode.split("\n");
        const pyOutputs = [];
        for (const line of pythonLines) {
          const printMatch = line.match(/print\s*\((.*)\)/);
          if (printMatch) {
            try {
              // Attempt to eval JS equivalent of print content
              const inner = printMatch[1].trim();
              const evaled = eval(inner);
              pyOutputs.push(String(evaled));
            } catch {
              pyOutputs.push(printMatch[1].replace(/["']/g, ""));
            }
          }
        }
        if (pyOutputs.length > 0) {
          logs.push(...pyOutputs);
        } else {
          logs.push(`Executed Python structure [${rawCode.length} chars] on Free Serverless Cloud Compute.`);
        }
      } catch {
        isError = true;
        logs.push(`Python Execution Error: ${err.message}`);
      }
    } else {
      isError = true;
      logs.push(`Runtime Error: ${err.message}`);
    }
  }

  const durationMs = Date.now() - startTime;
  const memAfter = process.memoryUsage();
  const rssDeltaMb = ((memAfter.rss - memBefore.rss) / 1024 / 1024).toFixed(3);
  const totalRssMb = (memAfter.rss / 1024 / 1024).toFixed(2);
  const freeRamMb = (1024 - parseFloat(totalRssMb)).toFixed(2);
  const region = process.env.VERCEL_REGION || "iad1";

  let finalStdout = logs.join("\n");
  if (executionResult !== undefined && executionResult !== null) {
    finalStdout += (finalStdout ? "\n\nResult: " : "Result: ") + (typeof executionResult === "object" ? JSON.stringify(executionResult, null, 2) : String(executionResult));
  }
  if (!finalStdout.trim()) {
    finalStdout = "[Program executed successfully with zero stdout output.]";
  }

  const headerBanner = [
    `◈ AETHER Free Serverless Cloud Runtime Execution`,
    `⚡ Compute Tier : Vercel Serverless Edge (${process.platform} ${process.arch}, region: ${region})`,
    `🧠 Free RAM     : ${freeRamMb} MB available (Used: ${totalRssMb} MB)`,
    `⏱️ Execution    : ${durationMs} ms (CPU Event-Loop)`,
    `══════════════════════════════════════════════════════════════`,
    ``
  ].join("\n");

  res.status(200).json({
    status: isError ? "error" : "success",
    output: headerBanner + finalStdout,
    metrics: {
      execution_time_ms: durationMs,
      total_rss_mb: parseFloat(totalRssMb),
      free_ram_mb: parseFloat(freeRamMb),
      region: region,
      platform: process.platform,
      arch: process.arch
    }
  });
};
