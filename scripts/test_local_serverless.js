const path = require("path");
const chatHandler = require(path.join(__dirname, "../cloud_web/api/chat.js"));
const agencyHandler = require(path.join(__dirname, "../cloud_web/api/agency.js"));

async function runLocalTests() {
  console.log("=== Testing local chatHandler ===");
  const req1 = {
    method: "POST",
    url: "/api/chat",
    body: { message: "Hello AETHER" }
  };
  const res1 = {
    statusCode: 200,
    headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.statusCode = code; return this; },
    json(data) {
      console.log("Chat Response status:", this.statusCode);
      console.log("Chat Response keys:", Object.keys(data));
      console.log("Chat Response snippet:", (data.response || "").substring(0, 100));
      console.log("Choices present?", Boolean(data.choices && data.choices[0]?.message?.content));
    }
  };
  await chatHandler(req1, res1);

  console.log("\n=== Testing local agencyHandler Swarm Execute ===");
  const req2 = {
    method: "POST",
    url: "/api/swarm/execute",
    body: { task: "Design distributed authentication microservice in Rust", roles: ["Planner", "Architect", "Coder", "Security Auditor"] }
  };
  const res2 = {
    statusCode: 200,
    headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.statusCode = code; return this; },
    json(data) {
      console.log("Swarm Execute status:", this.statusCode);
      console.log("Task:", data.task);
      console.log("Agents count:", data.agents_data?.length);
      console.log("First agent role:", data.agents_data?.[0]?.role, data.agents_data?.[0]?.agent_name);
      console.log("First agent snippet:", data.agents_data?.[0]?.content?.substring(0, 80));
    }
  };
  await agencyHandler(req2, res2);

  console.log("\n=== Testing local agencyHandler Swarm Debate ===");
  const req3 = {
    method: "POST",
    url: "/api/swarm/debate",
    body: { topic: "Event-driven vs Monolith for edge AI" }
  };
  const res3 = {
    statusCode: 200,
    headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.statusCode = code; return this; },
    json(data) {
      console.log("Swarm Debate status:", this.statusCode);
      console.log("Transcript length:", data.transcript?.length);
      console.log("First speaker:", data.transcript?.[0]?.sender, data.transcript?.[0]?.content?.substring(0, 80));
    }
  };
  await agencyHandler(req3, res3);
}

runLocalTests().then(() => console.log("\nAll local tests completed successfully."));
