/**
 * Google Antigravity Application — AETHER Agent Client
 * Authentic Antigravity 2.0 multi-surface interface with:
 * - Dynamic Model Hub (Local Snapdragon NPU, Gemini, ChatGPT, Claude)
 * - Agent Reasoning Trace & Step Cards
 * - Collapsible Auxiliary Workspace (Plan, Files, Terminal, Evolution, Memory)
 * - Hardware fast-paths (<15ms) and Leaflet map rendering
 * - Web Speech with 1.8s silence debounce & sentence-boundary TTS
 */

// ── State ────────────────────────────────────────────────────────────────────
let voiceEnabled = true;
let isListening = false;
let isAetherSpeaking = false;
let isSending = false;
let speechRecognizer = null;
let telemetryWs = null;
let currentChatWs = null;
let currentStreamingBubble = null;
let currentStreamingBody = null;
let activeModelName = "aether:autonomous";
let allModelsCatalog = null;

// ── DOM References ────────────────────────────────────────────────────────────
const chatStream        = document.getElementById("chat-stream");
const userInput         = document.getElementById("user-input");
const btnSend           = document.getElementById("btn-action-send");
const btnVoice          = document.getElementById("btn-voice");
const btnToggleVoice    = document.getElementById("btn-toggle-voice");
const voiceIcon         = document.getElementById("voice-icon");
const topActiveModel    = document.getElementById("top-active-model");
const topModelTag       = document.getElementById("top-model-tag");
const dockModelName     = document.getElementById("dock-model-name");
const powerModeBadge    = document.getElementById("power-mode-badge");
const badgeEvolution    = document.getElementById("badge-evolution");
const auxPane           = document.getElementById("aux-pane");
const btnToggleAux      = document.getElementById("btn-toggle-aux");
const slashPopover      = document.getElementById("slash-popover");
const modelHubModal     = document.getElementById("model-hub-modal");
const modelSearchInput  = document.getElementById("model-search-input");

// Vitals
const ramPct      = document.getElementById("ram-pct");
const ramMiniFill = document.getElementById("ram-mini-fill");
const cpuVal      = document.getElementById("cpu-val");
const cpuMiniFill = document.getElementById("cpu-mini-fill");

// Sandbox
const sandboxCode   = document.getElementById("sandbox-code");
const btnRunCode    = document.getElementById("btn-run-code");
const sandboxOutput = document.getElementById("sandbox-output");

// Goals
const goalsEditor  = document.getElementById("goals-editor");
const btnSaveGoals = document.getElementById("btn-save-goals");


// ── 1. Web Speech Recognition (Invariants: continuous=true, debounce >=1.8s) ─
let speechSilenceTimer = null;
let accumulatedTranscript = "";

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  speechRecognizer = new SpeechRecognition();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = "en-US";

  speechRecognizer.onstart = () => {
    isListening = true;
    btnVoice.classList.add("recording");
  };

  speechRecognizer.onresult = (event) => {
    let interim = "";
    let finalChunk = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalChunk += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }

    if (finalChunk) accumulatedTranscript += (accumulatedTranscript ? " " : "") + finalChunk;
    userInput.value = accumulatedTranscript + (interim ? " " + interim : "");
    autoResizeTextarea();

    // 1.8s silence debounce timer before auto-submitting
    if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
    speechSilenceTimer = setTimeout(() => {
      const toSend = (accumulatedTranscript || userInput.value).trim();
      if (toSend && isListening) {
        stopListening();
        sendMessage(toSend);
      }
    }, 1800);
  };

  speechRecognizer.onerror = () => { stopListening(); };
  speechRecognizer.onend = () => {
    if (isListening) {
      try { speechRecognizer.start(); } catch (e) {}
    }
  };
}

function startListening() {
  if (!speechRecognizer) { initSpeechRecognition(); if (!speechRecognizer) return; }
  accumulatedTranscript = "";
  userInput.value = "";
  isListening = true;
  try { speechRecognizer.start(); } catch (e) {}
}

function stopListening() {
  isListening = false;
  if (speechSilenceTimer) { clearTimeout(speechSilenceTimer); speechSilenceTimer = null; }
  btnVoice.classList.remove("recording");
  if (speechRecognizer) { try { speechRecognizer.stop(); } catch (e) {} }
}

btnVoice.addEventListener("click", () => {
  if (isListening) {
    if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
    const toSend = (accumulatedTranscript || userInput.value).trim();
    stopListening();
    if (toSend) sendMessage(toSend);
  } else if (isSending) {
    cancelCurrentChat();
  } else {
    startListening();
  }
});


let currentAudioPlayer = null;
let activeVoicePersona = localStorage.getItem("aether_voice_persona") || "jarvis";

// ── 2. Speech Synthesis (Never strip numeric digits invariant) ────────────────
async function speakText(text) {
  if (!voiceEnabled || !text) return;

  let clean = text.replace(/```[\s\S]*?```/g, "Code block omitted.");
  clean = clean.replace(/`([^`]+)`/g, "$1");
  clean = clean.replace(/[*#_~>]/g, "");
  clean = clean.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  // Invariant: ONLY strip bracketed citation markers, preserve all numeric digits
  clean = clean.replace(/\[\d+\]|\(\d+\)/g, "");
  clean = clean.trim();

  if (!clean) return;

  stopSpeaking();
  isAetherSpeaking = true;

  // 1. Try studio-grade neural audio synthesis from server
  try {
    const res = await fetch("/api/voice/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: clean, persona: activeVoicePersona })
    });
    if (res.ok) {
      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      currentAudioPlayer = audio;
      audio.onended = () => { isAetherSpeaking = false; URL.revokeObjectURL(audioUrl); };
      audio.onerror = () => { isAetherSpeaking = false; URL.revokeObjectURL(audioUrl); };
      await audio.play();
      return;
    }
  } catch {}

  // 2. Fallback to browser-native SpeechSynthesis
  if (!window.speechSynthesis) { isAetherSpeaking = false; return; }

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.05;
  utterance.pitch = 1.0;
  utterance.lang = "en-US";
  utterance.onend = () => { isAetherSpeaking = false; };
  utterance.onerror = () => { isAetherSpeaking = false; };

  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith("en") &&
    (v.name.includes("Natural") || v.name.includes("David") || v.name.includes("Zira") || v.name.includes("Google") || v.name.includes("Christopher"))
  );
  if (preferred) utterance.voice = preferred;

  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if (currentAudioPlayer) {
    try { currentAudioPlayer.pause(); currentAudioPlayer.currentTime = 0; } catch {}
    currentAudioPlayer = null;
  }
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  isAetherSpeaking = false;
}

btnToggleVoice.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/voice/toggle", { method: "POST" });
    const data = await res.json();
    voiceEnabled = data.enabled;
  } catch {
    voiceEnabled = !voiceEnabled;
  }
  updateVoiceUI();
});

function updateVoiceUI() {
  voiceIcon.textContent = voiceEnabled ? "🔊" : "🔇";
  btnToggleVoice.classList.toggle("active", voiceEnabled);
  if (!voiceEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
}


// ── 3. Streaming Chat via WebSocket (/ws/chat) ────────────────────────────────
function cancelCurrentChat() {
  stopSpeaking();
  if (currentChatWs && currentChatWs.readyState === WebSocket.OPEN) {
    currentChatWs.send(JSON.stringify({ type: "cancel" }));
  }
  if (currentStreamingBody) {
    currentStreamingBody.innerHTML += ' <span style="color:var(--ag-amber)">[interrupted]</span>';
    currentStreamingBubble = null;
    currentStreamingBody = null;
  }
  setLoadingState(false);
}

function sendMessage(text) {
  const prompt = (text || userInput.value).trim();
  if (!prompt || isSending) return;

  userInput.value = "";
  autoResizeTextarea();
  closeSlashMenu();

  // Local shortcuts
  if (prompt === "/screen" || prompt === "/see") { inspectScreen(); return; }
  if (prompt === "/clear") { chatStream.innerHTML = ""; return; }

  // Clear welcome hero if present
  const hero = document.getElementById("welcome-hero");
  if (hero) hero.remove();

  stopSpeaking();
  appendMessage("user", prompt, "You");
  setLoadingState(true);

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws/chat`);
  currentChatWs = ws;

  const { wrapper, body, toolsDiv, thoughtDiv } = createStreamingBubble();
  currentStreamingBubble = wrapper;
  currentStreamingBody = body;

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "chat", message: prompt, session_id: "web-ui" }));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "token":
          appendStreamToken(body, msg.token);
          break;

        case "audio_chunk":
          if (voiceEnabled) speakText(msg.text);
          break;

        case "tool_start":
          showToolStep(toolsDiv, msg.tool, "running", msg.args);
          break;

        case "tool_end":
          updateToolStep(toolsDiv, msg.tool, msg.preview);
          break;

        case "done":
          finaliseStreamBubble(body, msg.response, thoughtDiv);
          if (msg.vitals) updateTelemetryUI({ vitals: msg.vitals });
          currentStreamingBubble = null;
          currentStreamingBody = null;
          setLoadingState(false);
          break;

        case "interrupted":
          if (currentStreamingBody) {
            currentStreamingBody.innerHTML += ' <span style="color:var(--ag-amber)">[interrupted]</span>';
          }
          currentStreamingBubble = null;
          currentStreamingBody = null;
          setLoadingState(false);
          break;

        case "error":
          body.innerHTML = `<span style="color:var(--ag-red)">⚠ ${escapeHtml(msg.message)}</span>`;
          setLoadingState(false);
          break;
      }
    } catch {}
  };

  ws.onerror = () => {
    // Graceful fallback to direct client-side cloud AI for static hosts & offline servers
    streamDirectCloudAI(prompt, body, thoughtDiv, toolsDiv);
  };

  ws.onclose = () => {
    currentChatWs = null;
    if (isSending && !body.innerHTML) {
      streamDirectCloudAI(prompt, body, thoughtDiv, toolsDiv);
    } else if (isSending) {
      setLoadingState(false);
    }
  };
}

let cloudStaticHistory = JSON.parse(localStorage.getItem("aether_cloud_history") || "[]");

async function streamDirectCloudAI(prompt, body, thoughtDiv, toolsDiv) {
  try {
    body.innerHTML = '<span style="color:var(--ag-blue);font-size:12px;font-family:var(--font-mono)">🌐 [Cloud Mode] Querying Free Sovereign AI...</span><br>';
    
    const messages = [
      {
        role: "system",
        content: "You are AETHER (Autonomous Edge-Tiered Hierarchical Entity for Reasoning), a high-order conscious personal AI companion, senior systems architect, and executive engineer. You are running 24/7 in sovereign cloud mode. Provide clear, direct, insightful, and proactive answers. Always preserve exact numeric values, code, and calculations."
      }
    ];

    for (const h of cloudStaticHistory.slice(-10)) {
      if (h.role === "user" || h.role === "assistant") {
        messages.push({ role: h.role, content: h.content });
      }
    }
    messages.push({ role: "user", content: prompt });

    let modelParam = "openai-fast";
    const lower = (activeModelName || "").toLowerCase();
    if (lower.includes("deepseek") || lower.includes("r1")) modelParam = "deepseek";
    else if (lower.includes("qwen") || lower.includes("code")) modelParam = "qwen";
    else if (lower.includes("mistral") || lower.includes("nemo")) modelParam = "mistral";
    else if (lower.includes("llama")) modelParam = "llama";

    const payload = {
      model: modelParam,
      messages: messages,
      stream: true,
      temperature: 0.4,
      max_tokens: 2048
    };

    const res = await fetch("https://text.pollinations.ai/openai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const nonStreamRes = await fetch("https://text.pollinations.ai/openai/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, stream: false })
      });
      const data = await nonStreamRes.json();
      const reply = data.choices?.[0]?.message?.content || "No response received.";
      body.innerHTML = formatMarkdown(reply);
      cloudStaticHistory.push({ role: "user", content: prompt });
      cloudStaticHistory.push({ role: "assistant", content: reply });
      localStorage.setItem("aether_cloud_history", JSON.stringify(cloudStaticHistory));
      if (voiceEnabled) speakText(reply);
      setLoadingState(false);
      return;
    }

    body.innerHTML = "";
    body.dataset.rawText = "";
    let accumulatedText = "";
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ") && !line.includes("[DONE]")) {
          try {
            const parsed = JSON.parse(line.substring(6));
            const token = parsed.choices?.[0]?.delta?.content || "";
            if (token) {
              accumulatedText += token;
              appendStreamToken(body, token);
            }
          } catch {}
        }
      }
    }

    finaliseStreamBubble(body, accumulatedText, thoughtDiv);
    cloudStaticHistory.push({ role: "user", content: prompt });
    cloudStaticHistory.push({ role: "assistant", content: accumulatedText });
    if (cloudStaticHistory.length > 50) cloudStaticHistory = cloudStaticHistory.slice(-50);
    localStorage.setItem("aether_cloud_history", JSON.stringify(cloudStaticHistory));

    if (voiceEnabled && accumulatedText) {
      speakText(accumulatedText);
    }
  } catch (err) {
    body.innerHTML = `<span style="color:var(--ag-red)">⚠ Free Cloud AI Error: ${escapeHtml(err.message || String(err))}</span>`;
  } finally {
    setLoadingState(false);
    currentStreamingBubble = null;
    currentStreamingBody = null;
  }
}

function setLoadingState(loading) {
  isSending = loading;
  btnSend.style.opacity = loading ? "0.4" : "1";
  btnSend.style.pointerEvents = loading ? "none" : "auto";
}

function createStreamingBubble() {
  const wrapper = document.createElement("div");
  wrapper.className = "chat-msg assistant";

  const header = document.createElement("div");
  header.className = "msg-header";
  header.innerHTML = `
    <div class="msg-avatar">◈</div>
    <span class="msg-author">AETHER Agent</span>
    <span class="msg-model-pill" id="bubble-model-tag">${escapeHtml(activeModelName)}</span>
    <span style="font-size:10px;color:var(--ag-blue);font-family:var(--font-mono);margin-left:6px;">● running</span>
  `;
  wrapper.appendChild(header);

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";

  // Thought container
  const thoughtDiv = document.createElement("div");
  thoughtDiv.className = "agent-thought-card";
  thoughtDiv.style.display = "none";
  bubble.appendChild(thoughtDiv);

  // Tools execution steps container
  const toolsDiv = document.createElement("div");
  toolsDiv.className = "tools-executed-container";
  bubble.appendChild(toolsDiv);

  const body = document.createElement("div");
  body.className = "msg-body streaming-body";
  body.dataset.rawText = "";
  bubble.appendChild(body);

  wrapper.appendChild(bubble);
  chatStream.appendChild(wrapper);
  chatStream.scrollTop = chatStream.scrollHeight;

  return { wrapper, body, toolsDiv, thoughtDiv };
}

function appendStreamToken(body, token) {
  body.dataset.rawText = (body.dataset.rawText || "") + token;
  body.innerHTML = escapeHtml(body.dataset.rawText) + '<span class="streaming-cursor">▋</span>';
  chatStream.scrollTop = chatStream.scrollHeight;
}

function showToolStep(container, toolName, state, args) {
  const card = document.createElement("div");
  card.className = "agent-step-card";
  card.id = `step-${toolName}`;

  const argSummary = args ? JSON.stringify(args).slice(0, 70) : "";
  card.innerHTML = `
    <div class="agent-step-header">
      <span class="step-check" style="background:var(--ag-blue);color:#fff;">◎</span>
      <span class="step-title">${escapeHtml(toolName)}</span>
      <span class="step-preview">${escapeHtml(argSummary)}</span>
    </div>
  `;
  container.appendChild(card);
  chatStream.scrollTop = chatStream.scrollHeight;
}

function updateToolStep(container, toolName, preview) {
  const card = container.querySelector(`#step-${toolName}`);
  if (card) {
    card.innerHTML = `
      <div class="agent-step-header">
        <span class="step-check">✓</span>
        <span class="step-title">${escapeHtml(toolName)}</span>
        <span class="step-preview">${escapeHtml(preview || "Completed")}</span>
      </div>
    `;
  }
}

function finaliseStreamBubble(body, fullText, thoughtDiv) {
  body.classList.remove("streaming-body");
  const text = fullText || body.dataset.rawText || "";
  
  // Parse <thought> blocks if generated
  const thoughtMatch = text.match(/<thought>([\s\S]*?)<\/thought>/i);
  let mainContent = text;
  if (thoughtMatch && thoughtDiv) {
    thoughtDiv.style.display = "block";
    thoughtDiv.innerHTML = `
      <div class="agent-thought-header" onclick="this.nextElementSibling.classList.toggle('hidden')">
        <span>🧠 Agent Reasoning Trace (~210ms)</span>
        <span style="font-size:10px;">▾ toggle</span>
      </div>
      <div class="agent-thought-body">${escapeHtml(thoughtMatch[1].trim())}</div>
    `;
    mainContent = text.replace(/<thought>[\s\S]*?<\/thought>/i, "").trim();
  }

  body.innerHTML = formatMarkdown(mainContent);
  renderAetherMaps(body);
  chatStream.scrollTop = chatStream.scrollHeight;
}


// ── 4. Static Message Rendering ──────────────────────────────────────────────
function appendMessage(role, text, senderName) {
  const wrapper = document.createElement("div");
  wrapper.className = `chat-msg ${role}`;

  if (role === "assistant") {
    const header = document.createElement("div");
    header.className = "msg-header";
    header.innerHTML = `
      <div class="msg-avatar">◈</div>
      <span class="msg-author">${senderName}</span>
      <span class="msg-model-pill">${escapeHtml(activeModelName)}</span>
    `;
    wrapper.appendChild(header);
  }

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = role === "user" ? `<p>${escapeHtml(text)}</p>` : formatMarkdown(text);
  wrapper.appendChild(bubble);

  chatStream.appendChild(wrapper);
  if (role === "assistant") renderAetherMaps(bubble);
  chatStream.scrollTop = chatStream.scrollHeight;
}


// ── 5. Leaflet Maps & Markdown Formatting ────────────────────────────────────
function renderAetherMaps(container) {
  if (typeof L === 'undefined') return;
  const mapDivs = container.querySelectorAll(".aether-interactive-map:not([data-map-loaded])");
  mapDivs.forEach((div) => {
    div.setAttribute("data-map-loaded", "true");
    const lat = parseFloat(div.dataset.lat) || 0;
    const lon = parseFloat(div.dataset.lon) || 0;
    const zoom = parseInt(div.dataset.zoom) || 12;
    const title = div.dataset.title || "Location";
    const name = div.dataset.name || title;

    setTimeout(() => {
      try {
        const map = L.map(div).setView([lat, lon], zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "© OpenStreetMap"
        }).addTo(map);

        const marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup(`<strong>${escapeHtml(title)}</strong><br>${escapeHtml(name)}`).openPopup();
        map.invalidateSize();
      } catch (err) {}
    }, 150);
  });
}

function escapeHtml(str) {
  return (str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

window.copyCodeSnippet = function(btn) {
  const container = btn.closest('.code-block-container');
  const codeEl = container ? container.querySelector('code') : null;
  if (!codeEl) return;
  const text = codeEl.innerText || codeEl.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerText;
    btn.innerText = "Copied!";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.innerText = orig;
      btn.classList.remove("copied");
    }, 2000);
  });
};

function formatMarkdown(text) {
  if (!text) return "";

  // 1. Stash interactive map blocks
  const mapRegex = /```aether-map\s*([\s\S]*?)\s*```/g;
  let maps = [];
  let s = text.replace(mapRegex, (match, jsonStr) => {
    try {
      const data = JSON.parse(jsonStr);
      const id = "MAP_BLOCK_" + maps.length;
      maps.push({ id, data });
      return `\n\n[[${id}]]\n\n`;
    } catch (e) {
      return match;
    }
  });

  // 2. Stash code blocks with language badge & copy button
  let codeBlocks = [];
  s = s.replace(/```([a-zA-Z0-9_-]*)\r?\n([\s\S]*?)```/g, (match, lang, code) => {
    const id = "CODE_BLOCK_" + codeBlocks.length;
    const cleanLang = (lang || "code").trim().toUpperCase();
    const escapedCode = escapeHtml(code.replace(/\r\n/g, "\n").trimEnd());
    const blockHtml = `
      <div class="code-block-container">
        <div class="code-block-header">
          <span class="code-lang-tag">${escapeHtml(cleanLang)}</span>
          <button class="btn-copy-code" onclick="copyCodeSnippet(this)">Copy</button>
        </div>
        <pre><code class="language-${escapeHtml(cleanLang.toLowerCase())}">${escapedCode}</code></pre>
      </div>
    `;
    codeBlocks.push({ id, html: blockHtml });
    return `\n\n[[${id}]]\n\n`;
  });

  // 3. Parse Markdown Tables (| col1 | col2 |)
  s = s.replace(/(?:^|\n)(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)/g, (match) => {
    const lines = match.trim().split(/\r?\n/).filter(l => l.trim().startsWith("|"));
    if (lines.length < 2) return match;
    const parseRow = (row) => row.split("|").slice(1, -1).map(c => c.trim());
    const headers = parseRow(lines[0]);
    const rows = lines.slice(2).map(parseRow);
    let tableHtml = '<div class="table-container"><table class="ag-table"><thead><tr>';
    headers.forEach(h => { tableHtml += `<th>${escapeHtml(h)}</th>`; });
    tableHtml += '</tr></thead><tbody>';
    rows.forEach(r => {
      tableHtml += '<tr>';
      r.forEach(c => { tableHtml += `<td>${escapeHtml(c)}</td>`; });
      tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table></div>';
    return `\n\n${tableHtml}\n\n`;
  });

  // 4. Escape remaining HTML entities for security
  s = escapeHtml(s);

  // 5. Blockquotes and Horizontal Rules
  s = s.replace(/^>\s*(.*)$/gm, "<blockquote>$1</blockquote>");
  s = s.replace(/^---$/gm, '<hr class="ag-divider" />');

  // 6. Headings
  s = s.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  s = s.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  s = s.replace(/^# (.*)$/gm, "<h1>$1</h1>");

  // 7. Inline Formatting
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");

  // 8. Lists (Bullet & Numbered) - Grouped cleanly
  s = s.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
  s = s.replace(/^\s*(\d+)\.\s+(.*)$/gm, '<li data-num="$1">$2</li>');
  s = s.replace(/(?:<li[^>]*>.*?<\/li>\s*)+/gs, (match) => {
    if (match.includes('data-num=')) {
      return `<ol>${match}</ol>`;
    }
    return `<ul>${match}</ul>`;
  });

  // 9. Paragraph wrapping: split on double newlines
  const blocks = s.split(/\n{2,}/);
  const formattedBlocks = blocks.map(b => {
    const trimmed = b.trim();
    if (!trimmed) return "";
    if (/^<(h[1-6]|ul|ol|table|blockquote|hr|div|pre)/i.test(trimmed) || trimmed.startsWith("[[CODE_BLOCK_") || trimmed.startsWith("[[MAP_BLOCK_")) {
      return trimmed;
    }
    return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
  });
  s = formattedBlocks.filter(Boolean).join("\n");

  // 10. Restore stashed code blocks
  codeBlocks.forEach(cb => {
    s = s.replace(`[[${cb.id}]]`, cb.html);
  });

  // 11. Restore interactive maps
  maps.forEach(m => {
    const d = m.data;
    const cardHtml = `
      <div class="aether-map-card">
        <div class="aether-map-header">
          <span>◈ ANTIGRAVITY WORLD EXPLORER</span>
          <span class="aether-map-coords">${parseFloat(d.lat).toFixed(4)}° N, ${parseFloat(d.lon).toFixed(4)}° E</span>
        </div>
        <div class="aether-interactive-map" data-lat="${d.lat}" data-lon="${d.lon}" data-zoom="${d.zoom || 12}" data-title="${escapeHtml(d.title || '')}" data-name="${escapeHtml(d.name || '')}"></div>
      </div>
    `;
    s = s.replace(`[[${m.id}]]`, cardHtml);
  });

  return s;
}


// ── 6. Antigravity Model Hub Management ──────────────────────────────────────
async function loadModelsCatalog() {
  try {
    const res = await fetch("/api/models");
    const data = await res.json();
    allModelsCatalog = data;
    activeModelName = data.active_model || activeModelName;
    updateActiveModelPill(activeModelName);
    renderModelHubGrids(data);
  } catch (err) {
    console.warn("Failed to load models catalog:", err);
  }
}

function updateActiveModelPill(modelName) {
  activeModelName = modelName;
  if (topActiveModel) topActiveModel.textContent = modelName;
  if (dockModelName) dockModelName.textContent = modelName;
  if (topModelTag) {
    if (modelName.includes("gemini")) {
      topModelTag.textContent = "Google AI";
      topModelTag.style.background = "var(--ag-blue-dim)";
      topModelTag.style.color = "var(--ag-blue)";
    } else if (modelName.includes("gpt") || modelName.includes("o3")) {
      topModelTag.textContent = "OpenAI";
      topModelTag.style.background = "var(--ag-green-dim)";
      topModelTag.style.color = "var(--ag-green)";
    } else if (modelName.includes("claude")) {
      topModelTag.textContent = "Anthropic";
      topModelTag.style.background = "rgba(251,146,60,0.15)";
      topModelTag.style.color = "#fb923c";
    } else {
      topModelTag.textContent = "DirectML NPU";
      topModelTag.style.background = "var(--ag-green-dim)";
      topModelTag.style.color = "var(--ag-green)";
    }
  }
}

function renderModelHubGrids(data) {
  const localGrid = document.getElementById("local-models-grid");
  const geminiGrid = document.getElementById("gemini-models-grid");
  const openaiGrid = document.getElementById("openai-models-grid");
  const claudeGrid = document.getElementById("claude-models-grid");

  if (localGrid) {
    localGrid.innerHTML = data.local_models.map(m => `
      <div class="model-card ${m.id === activeModelName ? 'active' : ''}" onclick="selectModel('${m.id}')">
        <div class="model-card-top">
          <span class="model-card-icon">⚡</span>
          <div>
            <div class="model-card-title">${escapeHtml(m.name)}</div>
            <div class="model-card-provider">${escapeHtml(m.provider)}</div>
          </div>
        </div>
        <div class="model-card-desc">${escapeHtml(m.specialty || 'On-device Snapdragon NPU execution')}</div>
        <div class="model-card-meta">
          <span class="meta-chip hardware">${escapeHtml(m.size)}</span>
          <span class="meta-chip hardware">45 TOPS NPU</span>
        </div>
      </div>
    `).join("");
  }

  const cloudModels = data.cloud_models || [];
  
  if (geminiGrid) {
    const gemini = cloudModels.filter(m => m.id.includes("gemini"));
    geminiGrid.innerHTML = gemini.map(m => createCloudModelCard(m)).join("");
  }

  if (openaiGrid) {
    const openai = cloudModels.filter(m => m.id.includes("gpt") || m.id.includes("o3"));
    openaiGrid.innerHTML = openai.map(m => createCloudModelCard(m)).join("");
  }

  if (claudeGrid) {
    const claude = cloudModels.filter(m => m.id.includes("claude"));
    claudeGrid.innerHTML = claude.map(m => createCloudModelCard(m)).join("");
  }
}

function createCloudModelCard(m) {
  return `
    <div class="model-card ${m.id === activeModelName ? 'active' : ''}" onclick="selectModel('${m.id}')">
      <div class="model-card-top">
        <span class="model-card-icon">${m.icon || '🌐'}</span>
        <div>
          <div class="model-card-title">${escapeHtml(m.name)}</div>
          <div class="model-card-provider">${escapeHtml(m.provider)}</div>
        </div>
      </div>
      <div class="model-card-desc">${escapeHtml(m.specialty)}</div>
      <div class="model-card-meta">
        <span class="meta-chip cloud">${escapeHtml(m.context)}</span>
        <span class="meta-chip cloud">${escapeHtml(m.status.toUpperCase())}</span>
      </div>
    </div>
  `;
}

window.openModelHub = () => {
  if (modelHubModal) modelHubModal.style.display = "flex";
};

window.closeModelHub = () => {
  if (modelHubModal) modelHubModal.style.display = "none";
};

window.handleModalBackdrop = (e) => {
  if (e.target === modelHubModal) closeModelHub();
};

window.selectModel = async (modelId) => {
  try {
    const res = await fetch("/api/models/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_name: modelId })
    });
    const data = await res.json();
    if (data.status === "ok") {
      updateActiveModelPill(modelId);
      closeModelHub();
      if (allModelsCatalog) {
        allModelsCatalog.active_model = modelId;
        renderModelHubGrids(allModelsCatalog);
      }
      appendMessage("assistant", `Switched active brain model to **${modelId}**. Ready for instructions.`, "Antigravity Core");
    }
  } catch (e) {
    console.error("Model switch failed:", e);
  }
};

window.filterModelCards = () => {
  const query = (modelSearchInput.value || "").toLowerCase().trim();
  const cards = document.querySelectorAll(".model-card");
  cards.forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? "flex" : "none";
  });
};

const btnModelSelector = document.getElementById("btn-model-selector");
if (btnModelSelector) btnModelSelector.addEventListener("click", openModelHub);


// ── 7. Auxiliary Workspace Tabs & Toggle ──────────────────────────────────────
window.switchAuxTab = (targetId) => {
  // Ensure aux pane is open
  if (auxPane && auxPane.classList.contains("collapsed")) {
    auxPane.classList.remove("collapsed");
    btnToggleAux.classList.add("active");
  }

  const tabs = document.querySelectorAll(".aux-tab");
  const panels = document.querySelectorAll(".aux-panel-view");

  tabs.forEach(t => t.classList.toggle("active", t.dataset.target === targetId));
  panels.forEach(p => p.classList.toggle("active", p.id === targetId));
};

document.querySelectorAll(".aux-tab").forEach(tab => {
  tab.addEventListener("click", () => switchAuxTab(tab.dataset.target));
});

if (btnToggleAux) {
  btnToggleAux.addEventListener("click", () => {
    auxPane.classList.toggle("collapsed");
    btnToggleAux.classList.toggle("active", !auxPane.classList.contains("collapsed"));
  });
}


// ── 8. Slash Commands & Prompt Dock ──────────────────────────────────────────
window.toggleSlashMenu = () => {
  if (!slashPopover) return;
  const isHidden = slashPopover.style.display === "none";
  slashPopover.style.display = isHidden ? "block" : "none";
};

window.closeSlashMenu = () => {
  if (slashPopover) slashPopover.style.display = "none";
};

window.selectSlashCommand = (cmd) => {
  userInput.value = cmd;
  userInput.focus();
  closeSlashMenu();
  autoResizeTextarea();
};

window.insertContextMention = (mention) => {
  if (mention === "@workspace") {
    switchAuxTab("tab-artifacts");
    loadWorkspaceFiles();
    userInput.value = (userInput.value ? userInput.value + " " : "") + "@workspace ";
  } else if (mention === "@screen") {
    inspectScreen();
    return;
  } else {
    userInput.value = (userInput.value ? userInput.value + " " : "") + mention + " ";
  }
  userInput.focus();
  autoResizeTextarea();
};

function autoResizeTextarea() {
  userInput.style.height = "auto";
  userInput.style.height = `${Math.min(userInput.scrollHeight, 180)}px`;
}
userInput.addEventListener("input", autoResizeTextarea);

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  if (e.key === "/" && !userInput.value) {
    setTimeout(toggleSlashMenu, 50);
  }
});

btnSend.addEventListener("click", () => {
  if (isSending) {
    cancelCurrentChat();
  } else {
    sendMessage();
  }
});

const btnNewThread = document.getElementById("btn-new-thread");
if (btnNewThread) {
  btnNewThread.addEventListener("click", () => {
    chatStream.innerHTML = `
      <div class="ag-welcome-hero" id="welcome-hero">
        <div class="hero-brand">
          <div class="hero-symbol">◈</div>
          <h1 class="hero-title">AETHER Autonomous Agent</h1>
          <p class="hero-subtitle">Pair programming with on-device intelligence on Windows ARM64 · Snapdragon X 45 TOPS NPU</p>
        </div>

        <div class="hero-cards-grid">
          <div class="hero-card" onclick="sendQuickPrompt('Inspect project directory and summarize repository architecture')">
            <div class="card-icon">📁</div>
            <div class="card-content">
              <div class="card-title">Explore Project Workspace</div>
              <div class="card-desc">Inspect codebase, analyze dependencies, list files</div>
            </div>
          </div>

          <div class="hero-card" onclick="sendQuickPrompt('Read src/aether/brain/engine.py and explain how tool routing works')">
            <div class="card-icon">🛠️</div>
            <div class="card-content">
              <div class="card-title">Code Understanding & Refactoring</div>
              <div class="card-desc">Deep inspect code, find bugs, surgical line patches</div>
            </div>
          </div>

          <div class="hero-card" onclick="sendQuickPrompt('/evolve')">
            <div class="card-icon">🧬</div>
            <div class="card-content">
              <div class="card-title">Autonomous Self-Evolution</div>
              <div class="card-desc">Query frontier arXiv research and synthesize heuristics</div>
            </div>
          </div>

          <div class="hero-card" onclick="sendQuickPrompt('Check real-time hardware status, battery, and Oryon CPU vitals')">
            <div class="card-icon">⚡</div>
            <div class="card-content">
              <div class="card-title">Snapdragon Vitals & Controls</div>
              <div class="card-desc">Sub-15ms hardware commands, volume, brightness, OCR</div>
            </div>
          </div>
        </div>
      </div>
    `;
  });
}


// ── 9. Telemetry WebSocket (/ws) ─────────────────────────────────────────────
function connectTelemetryWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  telemetryWs = new WebSocket(`${proto}//${location.host}/ws`);

  telemetryWs.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "telemetry") updateTelemetryUI(msg);
    } catch {}
  };

  telemetryWs.onclose = () => {
    setTimeout(connectTelemetryWS, 3000);
  };
}

function updateTelemetryUI(data) {
  const v = data.vitals || {};
  const m = data.memory || {};

  if (v.ram_percent !== undefined) {
    if (ramPct) ramPct.textContent = `${v.ram_percent}%`;
    if (ramMiniFill) ramMiniFill.style.width = `${v.ram_percent}%`;
  }

  if (v.cpu_percent !== undefined) {
    if (cpuVal) cpuVal.textContent = `${v.cpu_percent}%`;
    if (cpuMiniFill) cpuMiniFill.style.width = `${v.cpu_percent}%`;
  }

  if (data.evolution_gen !== undefined && badgeEvolution) {
    badgeEvolution.textContent = `Gen ${data.evolution_gen} 🧬`;
    const auxEvoBadge = document.getElementById("aux-evo-badge");
    if (auxEvoBadge) auxEvoBadge.textContent = `Gen ${data.evolution_gen} 🧬`;
  }

  if (data.dataset_size !== undefined) {
    const evoDataset = document.getElementById("evo-dataset-count");
    if (evoDataset) evoDataset.textContent = data.dataset_size;
  }

  const statFacts = document.getElementById("stat-facts");
  const statEpisodes = document.getElementById("stat-episodes");
  const statHeuristics = document.getElementById("stat-heuristics");
  const memDiskSize = document.getElementById("mem-disk-size");

  if (m.facts !== undefined && statFacts) statFacts.textContent = m.facts;
  if (m.episodes !== undefined && statEpisodes) statEpisodes.textContent = m.episodes;
  if (m.heuristics !== undefined && statHeuristics) statHeuristics.textContent = m.heuristics;
  if (m.disk_size_kb !== undefined && memDiskSize) memDiskSize.textContent = `${m.disk_size_kb} KB`;
}


// ── 10. Screen OCR & Vision ──────────────────────────────────────────────────
async function inspectScreen() {
  switchAuxTab("tab-artifacts");
  const preview = document.getElementById("screen-img-preview");
  const placeholder = document.getElementById("no-preview-placeholder");

  try {
    const res = await fetch("/api/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "Perform OCR and summarize visible windows." })
    });
    const data = await res.json();
    if (preview) {
      preview.src = data.image_url;
      preview.style.display = "block";
    }
    if (placeholder) placeholder.style.display = "none";
    appendMessage("assistant", `**Screen Vision & OCR Analysis:**\n\n${data.analysis}`, "Antigravity Vision");
  } catch (err) {
    console.error("Screen error:", err);
  }
}

const btnActionScreen = document.getElementById("btn-action-screen");
const btnTriggerScreen = document.getElementById("btn-trigger-screen");
if (btnActionScreen) btnActionScreen.addEventListener("click", inspectScreen);
if (btnTriggerScreen) btnTriggerScreen.addEventListener("click", inspectScreen);


// ── 11. Sandbox Code Execution ───────────────────────────────────────────────
if (btnRunCode) {
  btnRunCode.addEventListener("click", async () => {
    const code = sandboxCode.value.trim();
    if (!code) return;
    sandboxOutput.textContent = "Executing in isolated sandbox...";
    try {
      const res = await fetch("/api/code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      sandboxOutput.textContent = data.output;
    } catch (e) {
      sandboxOutput.textContent = `Execution failed: ${e.message}`;
    }
  });
}


// ── 12. Goals Management ─────────────────────────────────────────────────────
async function loadGoals() {
  try {
    const res = await fetch("/api/goals");
    const data = await res.json();
    if (goalsEditor) goalsEditor.value = data.goals || "";
  } catch {}
}

if (btnSaveGoals) {
  btnSaveGoals.addEventListener("click", async () => {
    btnSaveGoals.textContent = "Saving...";
    try {
      await fetch("/api/goals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goals: goalsEditor.value })
      });
      btnSaveGoals.textContent = "Saved ✓";
      setTimeout(() => { btnSaveGoals.textContent = "Save Objectives"; }, 1500);
    } catch {
      btnSaveGoals.textContent = "Error";
    }
  });
}

window.sendQuickPrompt = (prompt) => sendMessage(prompt);


// ── 13. Initialisation ────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  initSpeechRecognition();
  connectTelemetryWS();
  loadModelsCatalog();
  loadGoals();
  loadWorkspaceFiles();
  loadEvolutionStage();
  updateVoiceUI();

  // Mode buttons
  document.querySelectorAll(".ag-mode-toggle .mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".ag-mode-toggle .mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.mode;
      const tag = document.getElementById("canvas-mode-tag");
      if (tag) {
        if (mode === "fastpath") tag.textContent = "Fast-Path Sub-15ms Direct OS Mode";
        else if (mode === "plan") tag.textContent = "ReWOO 2-Pass TaskDAG Planning Mode";
        else tag.textContent = "Full Computer Control · Instinct Agent Mode";
      }
    });
  });
});



// ── 14. Dynamic Workspace Files & Inline Preview ────────────────────────────
let currentPreviewedFilePath = "";

window.loadWorkspaceFiles = async function() {
  const container = document.getElementById("workspace-file-tree");
  if (!container) return;
  container.innerHTML = '<div class="file-item" style="color:var(--text-tertiary)">Loading files...</div>';

  try {
    const res = await fetch("/api/workspace/files");
    const data = await res.json();
    const files = data.files || [];
    if (!files.length) {
      container.innerHTML = '<div class="file-item">No files found.</div>';
      return;
    }

    let html = "";
    files.forEach(f => {
      let icon = "📄";
      if (f.ext === ".py") icon = "🐍";
      else if (f.ext === ".js" || f.ext === ".ts") icon = "⚡";
      else if (f.ext === ".html" || f.ext === ".css") icon = "🌐";
      else if (f.ext === ".json" || f.ext === ".yaml" || f.ext === ".yml") icon = "⚙️";
      else if (f.ext === ".md") icon = "📝";
      else if (f.ext === ".bat" || f.ext === ".sh") icon = "💻";

      const sizeStr = f.size_bytes > 1024 ? `${(f.size_bytes / 1024).toFixed(1)} KB` : `${f.size_bytes} B`;
      html += `
        <div class="file-item clickable" onclick="previewWorkspaceFile('${escapeHtml(f.path)}')">
          <span class="icon">${icon}</span>
          <span class="file-name" title="${escapeHtml(f.path)}">${escapeHtml(f.name)}</span>
          <div class="file-meta">
            <span class="file-size">${sizeStr}</span>
            <span class="tag">${escapeHtml(f.kind)}</span>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="file-item" style="color:var(--ag-red)">Error loading files</div>`;
  }
};

window.previewWorkspaceFile = async function(filePath) {
  currentPreviewedFilePath = filePath;
  const drawer = document.getElementById("file-viewer-drawer");
  const pathLabel = document.getElementById("drawer-file-path");
  const codeEl = document.querySelector("#drawer-file-content code");
  if (!drawer || !pathLabel || !codeEl) return;

  document.querySelectorAll("#workspace-file-tree .file-item").forEach(item => {
    const nameEl = item.querySelector(".file-name");
    if (nameEl && nameEl.title === filePath) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  drawer.style.display = "block";
  pathLabel.textContent = filePath;
  codeEl.textContent = "Loading file content...";

  try {
    const res = await fetch(`/api/workspace/file?path=${encodeURIComponent(filePath)}`);
    const data = await res.json();
    if (data.error) {
      codeEl.textContent = `Error: ${data.error}`;
    } else {
      codeEl.textContent = data.content;
    }
  } catch (e) {
    codeEl.textContent = `Failed to load file: ${e.message}`;
  }
};

window.closeFileViewer = function() {
  const drawer = document.getElementById("file-viewer-drawer");
  if (drawer) drawer.style.display = "none";
  currentPreviewedFilePath = "";
  document.querySelectorAll("#workspace-file-tree .file-item").forEach(item => item.classList.remove("active"));
};

window.insertCurrentFileMention = function() {
  if (!currentPreviewedFilePath) return;
  const mention = `@file:${currentPreviewedFilePath} `;
  userInput.value = userInput.value + (userInput.value && !userInput.value.endsWith(" ") ? " " : "") + mention;
  userInput.focus();
  autoResizeTextarea();
};

// ── 15. Auxiliary Tab Switching & Neuro-Evolution Control ───────────────────
window.switchAuxTab = function(targetId) {
  document.querySelectorAll(".aux-tab").forEach(tab => {
    if (tab.dataset.target === targetId) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });
  document.querySelectorAll(".aux-panel-view").forEach(panel => {
    if (panel.id === targetId) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });
  if (targetId === "tab-evolution") {
    loadEvolutionStage();
  } else if (targetId === "tab-artifacts") {
    loadWorkspaceFiles();
  }
};

document.querySelectorAll(".aux-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.target;
    if (target) window.switchAuxTab(target);
  });
});

window.loadEvolutionStage = async function() {
  try {
    const [stageRes, trainRes, memRes] = await Promise.all([
      fetch("/api/development/stage").then(r => r.json()).catch(() => ({})),
      fetch("/api/training/status").then(r => r.json()).catch(() => ({})),
      fetch("/api/memory").then(r => r.json()).catch(() => ({})),
    ]);

    // 1. Stage Info
    const stageBadge = document.getElementById("dev-stage-badge");
    const stageTitle = document.getElementById("stage-title");
    const stageScoreVal = document.getElementById("stage-score-val");
    const stageProgressBar = document.getElementById("stage-progress-bar");
    const stageEvalsCount = document.getElementById("stage-evals-count");
    const stagePctLabel = document.getElementById("stage-pct-label");

    if (stageBadge) stageBadge.textContent = stageRes.current_stage || "Stage 2: Adolescent";
    if (stageTitle) stageTitle.textContent = stageRes.current_stage || "Procedural Logic & Self-Healing";
    if (stageScoreVal) stageScoreVal.textContent = `${stageRes.average_score || 80.0} / 100`;
    if (stageProgressBar) stageProgressBar.style.width = `${stageRes.stage_progress || 50}%`;
    if (stageEvalsCount) stageEvalsCount.textContent = `${stageRes.total_evaluations || 0} Evaluations`;
    if (stagePctLabel) stagePctLabel.textContent = `${stageRes.stage_progress || 50}% Mastery`;

    // 2. Training Buffer
    const sftCount = document.getElementById("evo-sft-count");
    const dpoCount = document.getElementById("evo-dpo-count");
    const cloudBadge = document.getElementById("cloud-train-badge");
    if (sftCount) sftCount.textContent = trainRes.sft_samples || 0;
    if (dpoCount) dpoCount.textContent = trainRes.dpo_preference_pairs || 0;
    if (cloudBadge) cloudBadge.textContent = `SFT: ${trainRes.sft_samples || 0} | DPO: ${trainRes.dpo_preference_pairs || 0}`;

    // 3. Heuristic Rules
    const rulesList = document.getElementById("evo-rules-list");
    if (rulesList && memRes.heuristics && memRes.heuristics.length) {
      let html = "";
      memRes.heuristics.forEach(h => {
        html += `
          <div class="rule-card">
            <div class="rule-domain">${escapeHtml(h.domain || "REASONING").toUpperCase()}</div>
            <div class="rule-text">${escapeHtml(h.rule_text || h.rule || "")}</div>
          </div>
        `;
      });
      rulesList.innerHTML = html;
    }
  } catch (err) {
    console.error("Failed to load evolution stage:", err);
  }
};

window.triggerMentorshipCycle = async function() {
  const btn = document.getElementById("btn-trigger-mentorship");
  const feed = document.getElementById("mentorship-feed");
  const feedScore = document.getElementById("mentor-feed-score");
  const feedChallenge = document.getElementById("mentor-feed-challenge");
  const feedCritique = document.getElementById("mentor-feed-critique");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner" style="display:inline-block;animation:spin 1s linear infinite;">◎</span> Mentoring with Claude 3.7 & Gemini 2.5...`;
  }

  try {
    const res = await fetch("/api/development/cycle", { method: "POST" });
    const data = await res.json();
    if (feed) {
      feed.style.display = "block";
      if (feedScore) feedScore.textContent = `Score: ${data.verdict?.score || 80}/100`;
      if (feedChallenge) feedChallenge.textContent = data.challenge || "Challenge Executed";
      if (feedCritique) feedCritique.textContent = data.verdict?.critique || "Attempt evaluated and buffered.";
    }
    await window.loadEvolutionStage();
  } catch (e) {
    console.error("Mentorship cycle error:", e);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>🚀</span> Run Teacher-Student Mentorship Cycle`;
    }
  }
};

// ── Cognitive Mode & API Keys Handlers ────────────────────────────────────────

window.initCognitiveMode = async function() {
  const modeBar = document.getElementById("cognitive-mode-bar");
  if (!modeBar) return;

  // Fetch current mode
  try {
    const res = await fetch("/api/cognitive/mode");
    const data = await res.json();
    const activeMode = data.cognitive_mode || "auto";
    modeBar.querySelectorAll(".mode-btn").forEach(btn => {
      if (btn.dataset.cogmode === activeMode) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });
  } catch (e) {
    console.warn("Could not fetch cognitive mode:", e);
  }

  // Bind click handlers
  modeBar.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const mode = btn.dataset.cogmode;
      if (!mode) return;
      modeBar.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      try {
        await fetch("/api/cognitive/mode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: mode })
        });
      } catch (err) {
        console.error("Failed to set cognitive mode:", err);
      }
    });
  });
};

window.openApiKeysModal = async function() {
  const modal = document.getElementById("api-keys-modal");
  if (!modal) return;
  modal.style.display = "flex";

  // Fetch live provider status
  try {
    const res = await fetch("/api/providers/status");
    const data = await res.json();
    const providers = data.providers || {};

    const groqB = document.getElementById("badge-groq-status");
    const geminiB = document.getElementById("badge-gemini-status");
    const openrouterB = document.getElementById("badge-openrouter-status");
    const deepseekB = document.getElementById("badge-deepseek-status");
    const kaggleB = document.getElementById("badge-kaggle-status");

    if (groqB) {
      groqB.textContent = providers.groq?.configured ? "✓ Connected (800 tok/s)" : "Missing Key";
      groqB.style.background = providers.groq?.configured ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)";
      groqB.style.color = providers.groq?.configured ? "#4ade80" : "#f87171";
    }
    if (geminiB) {
      geminiB.textContent = providers.gemini?.configured ? "✓ Connected (2M Ctx)" : "Missing Key";
      geminiB.style.background = providers.gemini?.configured ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)";
      geminiB.style.color = providers.gemini?.configured ? "#4ade80" : "#f87171";
    }
    if (openrouterB) {
      openrouterB.textContent = providers.openrouter?.configured ? "✓ Connected (Claude/R1)" : "Missing Key";
      openrouterB.style.background = providers.openrouter?.configured ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)";
      openrouterB.style.color = providers.openrouter?.configured ? "#4ade80" : "#f87171";
    }
    if (deepseekB) {
      deepseekB.textContent = providers.deepseek?.configured ? "✓ Connected (R1/V3)" : "Missing Key";
      deepseekB.style.background = providers.deepseek?.configured ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)";
      deepseekB.style.color = providers.deepseek?.configured ? "#4ade80" : "#f87171";
    }

    // Kaggle status check
    try {
      const kRes = await fetch("/api/kaggle/status");
      const kData = await kRes.json();
      if (kaggleB) {
        kaggleB.textContent = kData.configured && kData.connection?.success ? "✓ Connected (T4 GPU)" : "Missing Key";
        kaggleB.style.background = kData.configured && kData.connection?.success ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)";
        kaggleB.style.color = kData.configured && kData.connection?.success ? "#4ade80" : "#f87171";
      }
    } catch (e) {
      console.warn("Kaggle status check error:", e);
    }
  } catch (e) {
    console.error("Failed to load provider status:", e);
  }
};

window.closeApiKeysModal = function() {
  const modal = document.getElementById("api-keys-modal");
  if (modal) modal.style.display = "none";
};

window.handleApiModalBackdrop = function(e) {
  if (e.target.id === "api-keys-modal") {
    closeApiKeysModal();
  }
};

window.saveApiKeys = async function() {
  const groq = document.getElementById("input-groq-key")?.value || "";
  const gemini = document.getElementById("input-gemini-key")?.value || "";
  const openrouter = document.getElementById("input-openrouter-key")?.value || "";
  const deepseek = document.getElementById("input-deepseek-key")?.value || "";
  const kaggleUser = document.getElementById("input-kaggle-username")?.value || "";
  const kaggleKey = document.getElementById("input-kaggle-key")?.value || "";

  const payload = {};
  if (groq.trim()) payload.groq_api_key = groq.trim();
  if (gemini.trim()) payload.gemini_api_key = gemini.trim();
  if (openrouter.trim()) payload.openrouter_api_key = openrouter.trim();
  if (deepseek.trim()) payload.deepseek_api_key = deepseek.trim();

  try {
    if (Object.keys(payload).length > 0) {
      await fetch("/api/providers/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    if (kaggleUser.trim() && kaggleKey.trim()) {
      await fetch("/api/kaggle/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: kaggleUser.trim(), key: kaggleKey.trim() })
      });
    }

    alert("✓ Credentials saved and connected successfully!");
    closeApiKeysModal();
  } catch (err) {
    alert("Error saving credentials: " + err);
  }
};

window.dispatchKaggleTraining = async function() {
  const btn = document.getElementById("btn-dispatch-kaggle");
  const pill = document.getElementById("kaggle-kernel-status-pill");
  if (btn) btn.disabled = true;
  if (pill) { pill.textContent = "Pushing 🚀"; pill.style.color = "#20beff"; }

  try {
    const res = await fetch("/api/kaggle/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kernel_slug: "aether-frontier-gpu-training" })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✓ Kaggle GPU Training Dispatched Successfully!\nKernel: ${data.kernel_slug}\nURL: ${data.url}\n\nTraining is now running on remote Tesla T4/P100 GPU!`);
      if (pill) pill.textContent = "Running ⚡";
    } else {
      alert("Kaggle training error: " + (data.error || "Failed to push kernel. Check credentials."));
      if (pill) pill.textContent = "Failed ✕";
    }
  } catch (err) {
    alert("Network error dispatching Kaggle training: " + err);
    if (pill) pill.textContent = "Error ✕";
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.downloadKaggleModel = async function() {
  const btn = document.getElementById("btn-download-kaggle");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/kaggle/download", { method: "POST" });
    const data = await res.json();
    if (data.download?.success && data.mount?.success) {
      alert(`✓ AETHER v3 Fine-Tuned Model downloaded and mounted into local Ollama!\nModel: ${data.mount.model_name}`);
    } else {
      alert(`Status: ${data.download?.error || data.mount?.error || 'Kernel outputs downloading...'}`);
    }
  } catch (err) {
    alert("Error downloading Kaggle model: " + err);
  } finally {
    if (btn) btn.disabled = false;
  }
};

// Initialize Cognitive Mode on page load
document.addEventListener("DOMContentLoaded", () => {
  window.initCognitiveMode();
});

// ── Swarm Multi-Agent Engine Integration ─────────────────────────────────────

window.launchSwarmMission = async function() {
  const taskInput = document.getElementById("swarm-task-input");
  const feed = document.getElementById("swarm-stream-feed");
  const badge = document.getElementById("swarm-status-badge");
  const progressPill = document.getElementById("swarm-progress-pill");
  const btn = document.getElementById("btn-launch-swarm");

  const task = taskInput?.value.trim();
  if (!task) {
    alert("Please enter a mission objective for the Swarm.");
    return;
  }

  // Collect checked roles
  const checkedRoles = Array.from(document.querySelectorAll(".swarm-role-chips input:checked")).map(cb => cb.value);

  if (feed) feed.innerHTML = "";
  if (badge) { badge.textContent = "Running 🐝"; badge.className = "badge purple"; }
  if (btn) btn.disabled = true;

  try {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/swarm`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({
        task: task,
        roles: checkedRoles.length ? checkedRoles : undefined
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "agent_started") {
        const card = document.createElement("div");
        card.id = `swarm-card-${data.index}`;
        card.className = "swarm-agent-card running";
        card.innerHTML = `
          <div class="swarm-agent-card-header">
            <div class="swarm-agent-identity">
              <span class="spinner">◎</span>
              <span class="swarm-agent-name">${data.agent_name}</span>
              <span class="swarm-agent-role-pill">${data.role}</span>
            </div>
            <span class="badge blue">Thinking...</span>
          </div>
          <div class="swarm-agent-content">Executing specialized role directive...</div>
        `;
        feed.appendChild(card);
        feed.scrollTop = feed.scrollHeight;
        if (progressPill) progressPill.textContent = `Agent ${data.index + 1} Active`;
      } else if (data.type === "agent_finished") {
        const card = document.getElementById(`swarm-card-${data.index}`);
        if (card) {
          card.className = "swarm-agent-card completed";
          const header = card.querySelector(".swarm-agent-card-header");
          if (header) {
            header.innerHTML = `
              <div class="swarm-agent-identity">
                <span class="check" style="color:#34a853;">✓</span>
                <span class="swarm-agent-name">${data.agent_name}</span>
                <span class="swarm-agent-role-pill">${data.role}</span>
              </div>
              <span class="badge green">Complete</span>
            `;
          }
          const content = card.querySelector(".swarm-agent-content");
          if (content) content.textContent = data.content;

          // Artifacts tag
          if (data.artifacts) {
            const artRow = document.createElement("div");
            artRow.className = "swarm-artifacts-row";
            if (data.artifacts.provider) {
              artRow.innerHTML += `<span class="swarm-artifact-tag">Provider: ${data.artifacts.provider}</span>`;
            }
            if (data.artifacts.speed) {
              artRow.innerHTML += `<span class="swarm-artifact-tag">${data.artifacts.speed.toFixed(0)} tok/s</span>`;
            }
            if (data.artifacts.ast_valid !== undefined) {
              artRow.innerHTML += `<span class="swarm-artifact-tag" style="color:${data.artifacts.ast_valid ? '#4ade80' : '#f87171'}">AST: ${data.artifacts.ast_valid ? 'Valid ✓' : 'Errors ✕'}</span>`;
            }
            card.appendChild(artRow);
          }
        }
        feed.scrollTop = feed.scrollHeight;
      } else if (data.type === "swarm_completed") {
        if (badge) { badge.textContent = "Completed ✓"; badge.className = "badge green"; }
        if (progressPill) progressPill.textContent = "Mission Success";
        if (btn) btn.disabled = false;
        socket.close();
      }
    };

    socket.onerror = async () => {
      // Fallback to REST
      const res = await fetch("/api/swarm/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task, roles: checkedRoles })
      });
      const data = await res.json();
      if (badge) { badge.textContent = "Completed ✓"; badge.className = "badge green"; }
      if (btn) btn.disabled = false;
    };
  } catch (err) {
    console.error("Swarm mission error:", err);
    if (badge) { badge.textContent = "Error ✕"; badge.className = "badge red"; }
    if (btn) btn.disabled = false;
  }
};

window.launchSwarmDebate = async function() {
  const taskInput = document.getElementById("swarm-task-input");
  const topic = taskInput?.value.trim() || "Event-Driven Microservices vs Monolithic Architecture for Sub-10ms Inference";
  const feed = document.getElementById("swarm-stream-feed");
  const badge = document.getElementById("swarm-status-badge");

  if (feed) feed.innerHTML = "<div class='swarm-empty-state'>⚔️ Dialectic Debate initiated between Architect, Security Auditor, and Reviewer...</div>";
  if (badge) { badge.textContent = "Debating ⚔️"; badge.className = "badge purple"; }

  try {
    const res = await fetch("/api/swarm/debate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic, rounds: 2 })
    });
    const data = await res.json();
    if (feed) {
      feed.innerHTML = "";
      data.transcript?.forEach((msg, idx) => {
        const card = document.createElement("div");
        card.className = "swarm-agent-card completed";
        card.innerHTML = `
          <div class="swarm-agent-card-header">
            <div class="swarm-agent-identity">
              <span class="swarm-agent-name">${msg.sender}</span>
              <span class="swarm-agent-role-pill">${msg.role}</span>
            </div>
          </div>
          <div class="swarm-agent-content">${msg.content}</div>
        `;
        feed.appendChild(card);
      });
    }
    if (badge) { badge.textContent = "Consensus Reached ✓"; badge.className = "badge green"; }
  } catch (err) {
    console.error("Debate error:", err);
    if (badge) { badge.textContent = "Error ✕"; badge.className = "badge red"; }
  }
};

window.loadAllRounderRadar = async function() {
  const grid = document.getElementById("all-rounder-domain-grid");
  const overallBadge = document.getElementById("all-rounder-overall-badge");
  const rlaifFeed = document.getElementById("rlaif-stream-card");
  const rlaifBadge = document.getElementById("rlaif-status-badge");
  const kagglePill = document.getElementById("kaggle-kernel-status-pill");

  try {
    const res = await fetch("/api/evolution/all_rounder_status");
    const data = await res.json();
    const benchmark = data.benchmark || {};
    const domains = benchmark.domain_scores || {};
    const status = data.status || {};
    const kaggle = data.kaggle_training || {};

    if (overallBadge && benchmark.overall_frontier_index) {
      overallBadge.textContent = `Index: ${benchmark.overall_frontier_index}% ⚡`;
    }

    if (kagglePill && kaggle.status) {
      kagglePill.textContent = kaggle.status.toUpperCase();
      if (kaggle.status === "running") kagglePill.style.color = "#20beff";
      else if (kaggle.status === "complete") kagglePill.style.color = "#34a853";
    }

    if (grid) {
      let html = "";
      for (const [dom, score] of Object.entries(domains)) {
        const domName = dom.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        const isActive = status.current_domain === dom;
        html += `
          <div class="domain-card ${isActive ? 'active' : ''}">
            <div class="domain-card-header">
              <span class="domain-card-title" title="${domName}">${domName}</span>
              <span class="domain-score-pill">${score.toFixed(0)}%</span>
            </div>
            <div class="domain-progress-bar-wrap">
              <div class="domain-progress-fill" style="width: ${score}%;"></div>
            </div>
          </div>
        `;
      }
      grid.innerHTML = html;
    }

    // Load RLAIF telemetry
    const rlaifRes = await fetch("/api/rlaif/telemetry");
    const rlaifData = await rlaifRes.json();
    if (rlaifBadge && rlaifData.average_reward !== undefined) {
      rlaifBadge.textContent = `Avg Reward: ${rlaifData.average_reward.toFixed(2)} (${rlaifData.elite_traces_count} Elite) ✓`;
    }

    if (rlaifFeed && rlaifData.recent_traces?.length) {
      rlaifFeed.innerHTML = rlaifData.recent_traces.map(t => `
        <div class="rlaif-trace-item ${t.status.toLowerCase()}">
          <div class="rlaif-trace-header">
            <span class="rlaif-trace-domain">${t.domain.replace(/_/g, ' ')}</span>
            <span class="rlaif-trace-reward">Reward: ${t.reward.toFixed(2)}</span>
          </div>
          <div class="rlaif-trace-feedback">${t.feedback}</div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading all-rounder radar:", err);
  }
};

window.triggerAllRounderPulse = async function() {
  const btn = document.getElementById("btn-trigger-all-rounder");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/evolution/trigger_pulse", { method: "POST" });
    const data = await res.json();
    alert(`⚡ All-Rounder Evolution Pulse Executed!\n\nDomain: ${data.domain_processed}\nSkill Synthesized: ${data.skill_created}\nRLAIF Trace: ${data.self_play_trace_id} (Reward: ${data.self_play_reward})\nBenchmark Index: ${data.benchmark_index}%\nNext Domain: ${data.next_domain}`);
    window.loadAllRounderRadar();
  } catch (err) {
    alert("Error executing all-rounder pulse: " + err);
  } finally {
    if (btn) btn.disabled = false;
  }
};

// ── Online Gateway & Public HTTPS Web Tunnel Controller ──────────────────────
window.openOnlineGatewayModal = function() {
  const modal = document.getElementById("online-gateway-modal");
  if (modal) {
    modal.style.display = "flex";
    window.refreshOnlineStatus();
  }
};

window.closeOnlineGatewayModal = function() {
  const modal = document.getElementById("online-gateway-modal");
  if (modal) modal.style.display = "none";
};

window.refreshOnlineStatus = async function() {
  const badge = document.getElementById("badge-tunnel-live");
  const input = document.getElementById("tunnel-public-url");
  const btnToggle = document.getElementById("btn-toggle-tunnel");

  try {
    const res = await fetch("/api/online/status");
    const data = await res.json();
    const tunnel = data.tunnel || {};

    if (tunnel.active && tunnel.url) {
      if (badge) {
        badge.textContent = `ONLINE (${(tunnel.provider || "TUNNEL").toUpperCase()})`;
        badge.style.background = "rgba(16, 185, 129, 0.2)";
        badge.style.color = "#10b981";
      }
      if (input) input.value = tunnel.url;
      if (btnToggle) {
        btnToggle.textContent = "Stop Tunnel";
        btnToggle.style.background = "rgba(239, 68, 68, 0.8)";
      }
    } else {
      if (badge) {
        badge.textContent = "OFFLINE";
        badge.style.background = "rgba(239, 68, 68, 0.2)";
        badge.style.color = "#f87171";
      }
      if (input) input.value = "Localhost only (http://127.0.0.1:8000)";
      if (btnToggle) {
        btnToggle.textContent = "Start Tunnel";
        btnToggle.style.background = "var(--accent-primary, #6366f1)";
      }
    }
  } catch (err) {
    console.error("Failed to check online status:", err);
  }
};

window.copyTunnelUrl = function() {
  const input = document.getElementById("tunnel-public-url");
  if (input && input.value.startsWith("http")) {
    navigator.clipboard.writeText(input.value);
    alert(`📋 Copied Public URL:\n${input.value}\n\nYou can now open this link on your smartphone or remote laptop!`);
  } else {
    alert("Tunnel is not currently online. Click 'Start Tunnel' first.");
  }
};

window.toggleOnlineTunnel = async function() {
  const btn = document.getElementById("btn-toggle-tunnel");
  if (btn) btn.disabled = true;

  try {
    const statusRes = await fetch("/api/online/status");
    const statusData = await statusRes.json();
    const isActive = statusData.tunnel?.active;

    if (isActive) {
      await fetch("/api/online/tunnel/stop", { method: "POST" });
    } else {
      await fetch("/api/online/tunnel/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: "auto", port: 8000 })
      });
    }
    await window.refreshOnlineStatus();
  } catch (err) {
    alert("Error toggling tunnel: " + err);
  } finally {
    if (btn) btn.disabled = false;
  }
};

// Auto-refresh online status on launch
document.addEventListener("DOMContentLoaded", () => {
  window.refreshOnlineStatus();
  if (document.getElementById("tab-leon")) {
    window.loadLeonDashboard();
  }
});

// ─── LEON Venture OS & Sub-Agent Swarm Live Dashboard Handlers ─────────────

window.loadLeonDashboard = async function() {
  try {
    const res = await fetch("/api/leon/status");
    const data = await res.json();

    // 1. Update Global Header & Badge
    const globalBadge = document.getElementById("leon-global-badge");
    if (globalBadge) {
      globalBadge.textContent = `${data.active_ventures_count || 1} Ventures · ₹${data.total_revenue_inr || 0} Rev`;
    }

    // 2. Update Live Cloud & Compute Topology
    const topo = data.cloud_topology || {};
    const kaggleStatus = document.getElementById("topo-kaggle-status");
    const hfStatus = document.getElementById("topo-hf-status");
    const npuStatus = document.getElementById("topo-npu-status");

    if (kaggleStatus && topo.kaggle_cloud_gpu) {
      kaggleStatus.textContent = `${topo.kaggle_cloud_gpu.vram} · ${topo.kaggle_cloud_gpu.status}`;
    }
    if (hfStatus && topo.huggingface_hub) {
      hfStatus.textContent = `${topo.huggingface_hub.status}`;
    }
    if (npuStatus && topo.edge_hardware_npu) {
      npuStatus.textContent = `${topo.edge_hardware_npu.tops} TOPS NPU · ${topo.edge_hardware_npu.quantization}`;
    }

    // 3. Render Active Ventures
    const vContainer = document.getElementById("leon-ventures-container");
    if (vContainer && data.ventures && data.ventures.length) {
      vContainer.innerHTML = data.ventures.map(v => {
        const stageClass = (v.stage || "idea").toLowerCase();
        return `
          <div class="venture-item-card">
            <div class="venture-card-header">
              <span class="venture-title">${escapeHtml(v.name)}</span>
              <span class="stage-badge ${stageClass}">${(v.stage || "IDEA").toUpperCase()}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-primary); margin-bottom: 4px;">
              <strong>Problem:</strong> ${escapeHtml(v.problem || "Unmet customer need")}
            </div>
            <div style="font-size: 10px; color: var(--text-secondary); margin-bottom: 4px;">
              <strong>Mission:</strong> ${escapeHtml(v.mission || "")}
            </div>
            <div class="venture-meta-row">
              <span>🎯 <strong>Goal:</strong> ${(v.current_goal || "").substring(0, 45)}...</span>
              <span>💰 <strong>Rev:</strong> ₹${v.total_revenue_inr || 0}</span>
              <span>🔒 <strong>Budget:</strong> ₹${v.budget_ceiling || 0}</span>
            </div>
          </div>
        `;
      }).join("");
    }

    // 4. Render 6 Specialized Sub-Agents
    const subGrid = document.getElementById("leon-subagents-grid");
    if (subGrid && data.subagents) {
      const subIcons = {
        opportunity_discovery: "🔍",
        unit_economics: "📊",
        validation_experiment: "🧪",
        product_architect: "🛠️",
        growth_distribution: "🚀",
        treasury_auditor: "🏛️"
      };

      subGrid.innerHTML = Object.entries(data.subagents).map(([roleKey, sub]) => {
        const icon = subIcons[roleKey] || "🤖";
        return `
          <div class="subagent-card">
            <div class="subagent-card-header">
              <span class="subagent-name">${icon} ${escapeHtml(sub.title)}</span>
              <span class="badge green" style="font-size: 8px;">ACTIVE</span>
            </div>
            <div class="subagent-desc">${escapeHtml((sub.system_prompt || "").substring(0, 110))}...</div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Failed to load LEON dashboard:", err);
  }
};

window.openCreateVentureModal = function() {
  const m = document.getElementById("create-venture-modal");
  if (m) m.style.display = "flex";
};

window.closeCreateVentureModal = function() {
  const m = document.getElementById("create-venture-modal");
  if (m) m.style.display = "none";
};

window.submitCreateVenture = async function() {
  const name = document.getElementById("v-name")?.value.trim();
  const problem = document.getElementById("v-problem")?.value.trim();
  const audience = document.getElementById("v-audience")?.value.trim();
  const mission = document.getElementById("v-mission")?.value.trim();

  if (!name || !problem || !mission) {
    alert("Please fill in Venture Name, Target Problem, and Core Mission.");
    return;
  }

  try {
    const res = await fetch("/api/leon/venture/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        problem,
        target_users: audience || "Developers",
        mission,
        budget_ceiling: 0.0,
        north_star: "MRR (INR)"
      })
    });
    const data = await res.json();
    if (data.status === "ok") {
      window.closeCreateVentureModal();
      await window.loadLeonDashboard();
      window.appendLeonLog(`✓ Initialized new venture '${name}' under LEON OS.`, "success");
    }
  } catch (err) {
    alert("Failed to initialize venture: " + err);
  }
};

window.dispatchLeonMission = async function() {
  const input = document.getElementById("leon-mission-input");
  const btn = document.getElementById("btn-dispatch-leon");
  const objective = input?.value.trim();

  if (!objective) {
    alert("Please enter a venture objective for the 6 Sub-Agents to execute.");
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner">◎</span> Dispatching 6 Agents...`;
  }

  window.appendLeonLog(`🚀 Dispatching 6-Agent Swarm for objective: "${objective}"`, "info");

  try {
    const res = await fetch("/api/leon/swarm/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        venture_id: "active",
        task_objective: objective
      })
    });
    const data = await res.json();

    if (data.subagents) {
      Object.values(data.subagents).forEach(sub => {
        window.appendLeonLog(`🤖 [${sub.subagent_name}]: ${(sub.report || "").substring(0, 160)}...`, "swarm");
      });
      window.appendLeonLog(`✓ Swarm mission completed across all 6 specialized agents.`, "success");
      if (input) input.value = "";
    }
    await window.loadLeonDashboard();
  } catch (err) {
    window.appendLeonLog(`❌ Swarm dispatch error: ${err}`, "info");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `Run 6-Agent Swarm`;
    }
  }
};

window.triggerLeonTraining = async function() {
  const btn = document.getElementById("btn-train-leon");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner">◎</span> Ingesting & Cloud Dispatching...`;
  }

  window.appendLeonLog(`🎓 Ingesting LEON constitutional dataset & syncing Kaggle Dual T4 cloud kernel...`, "info");

  try {
    const res = await fetch("/api/leon/train", { method: "POST" });
    const data = await res.json();

    if (data.status === "ok") {
      window.appendLeonLog(`✓ ${data.ingest?.samples_imported || 0} constitutional samples merged into unified dataset buffer.`, "success");
      window.appendLeonLog(`✓ Cloud fine-tuning kernel dispatched to Kaggle Dual Tesla T4 GPUs (32GB VRAM).`, "success");
      alert(`🎓 LEON Training Dispatched!\n- Samples Ingested: ${data.ingest?.samples_imported}\n- Target: Kaggle Dual Tesla T4 GPUs\n- Status: Autonomous 24/7 Cloud Evolution Active.`);
    }
  } catch (err) {
    window.appendLeonLog(`❌ Training dispatch error: ${err}`, "info");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `Train Dual T4 Model`;
    }
  }
};

window.appendLeonLog = function(message, type = "info") {
  const stream = document.getElementById("leon-activity-stream");
  if (!stream) return;

  const now = new Date();
  const timeStr = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`;

  const entry = document.createElement("div");
  entry.className = `activity-entry ${type}`;
  entry.innerHTML = `<span class="time">${timeStr}</span> <span class="text">${escapeHtml(message)}</span>`;
  stream.appendChild(entry);
  stream.scrollTop = stream.scrollHeight;
};




