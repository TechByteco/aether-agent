# 🌐 AETHER Sovereign Cloud Deployment Guide (100% Free Service Providers)

This directory contains everything you need to run AETHER continuously online across multiple **100% Free ($0.00)** cloud platforms.

---

## 🚀 Deployment Options

### 🟢 Option A: Hugging Face Static Space (100% Free Forever, Zero Sleep) - RECOMMENDED
Runs directly in the browser with direct client-to-cloud AI reasoning, zero server latency, and persistent local storage.

1. Go to [Hugging Face Create New Space](https://huggingface.co/new-space).
2. Space Name: `aether-hud`
3. License: `mit` / `apache-2.0`
4. Select SDK: **Static** (HTML / JS).
5. Push or drag-and-drop the 3 files inside [`cloud_deployment/static_space/`](file:///c:/Users/saali/Documents/antigravity/charming-lovelace/cloud_deployment/static_space/):
   - `index.html`
   - `app.js`
   - `style.css`
   - `README.md`
6. Done! AETHER is live at `https://huggingface.co/spaces/YOUR_USERNAME/aether-hud`.

---

### 🟢 Option B: Render.com (100% Free Web Service - Full Python Backend)
Runs the full Python FastAPI + SQLite conscious memory database 24/7 without needing your PC.

1. Go to [Render Dashboard](https://dashboard.render.com/) -> **New +** -> **Web Service**.
2. Connect your GitHub repository and set Root Directory: `cloud_deployment`.
3. Select **Docker** environment.
4. Instance Type: **Free ($0/month)**.
5. Deploy! AETHER is live at `https://aether-sovereign-agent.onrender.com`.

---

### 🟢 Option C: Hugging Face Spaces (Docker CPU Basic - Free 2 vCPU · 16GB RAM)
Runs the full Docker container on Hugging Face Spaces.

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) -> **Create new Space**.
2. Space Name: `aether-sovereign-backend`
3. Select SDK: **Docker** -> **Blank**.
4. Hardware: **Free (CPU Basic · 2 vCPU · 16GB RAM)**.
5. Push the files in `cloud_deployment/`:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/aether-sovereign-backend
   git push space main
   ```
*(Note: HF Docker spaces enter sleep mode after 48h of inactivity and automatically wake up upon URL access).*

---

### 🟢 Option D: Cloudflare Pages / Vercel / GitHub Pages (100% Free Static CDN)
1. Push the contents of [`cloud_deployment/static_space/`](file:///c:/Users/saali/Documents/antigravity/charming-lovelace/cloud_deployment/static_space/) to a GitHub repo.
2. Enable **GitHub Pages** (Settings -> Pages -> Deploy from branch `main`).
3. Access your globally distributed AETHER HUD from any phone or PC worldwide.

---

## 🧠 What Powers AETHER 24/7 Online

* **Free Public Cloud AI**: Direct inference via Pollinations.ai open endpoints (DeepSeek R1, GPT-OSS 20B, Qwen 2.5 Coder 32B, Mistral Nemo 12B, Llama 3.3 70B).
* **Zero API Keys & $0.00 Cost**: No credit card or paid accounts required anywhere.
* **Persistent Consciousness**: Episodic memory preserved across sessions.
* **Continuous Web Speech & Audio**: Browser-native voice dictation with 1.8s silence debounce and speech synthesis with exact numeric preservation intact.
