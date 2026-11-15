"""
AETHER Autonomous Kaggle Cloud Training Controller
===================================================
Coordinates zero-dependency, automated cloud GPU fine-tuning on Kaggle:
- Supports both Kaggle Access Tokens (KAGGLE_API_TOKEN / ~/.kaggle/access_token)
  and classic API Keys (KAGGLE_USERNAME + KAGGLE_KEY / ~/.kaggle/kaggle.json).
- Authenticates with Kaggle REST API v1.
- Uploads synthetic multi-situation curricula datasets.
- Pushes GPU-accelerated Unsloth training kernels (Tesla T4 / P100).
- Monitors live training progress and logs.
- Automatically downloads converted GGUF weights and mounts them into local Ollama.
"""

import base64
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.kaggle_controller")

KAGGLE_API_BASE = "https://www.kaggle.com/api/v1"


class KaggleController:
    """Autonomous agent controller for Kaggle GPU training jobs."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path(__file__).resolve().parent.parent.parent.parent
        self.training_dir = self.workspace_root / "data" / "training"
        self.models_dir = self.workspace_root / "data" / "models"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = 60.0
        self._cached_username: Optional[str] = None

    def get_api_token(self) -> str:
        """Retrieve Kaggle Access Token if configured."""
        # 1. Environment variable
        token = os.getenv("KAGGLE_API_TOKEN", "").strip()
        if token:
            return token

        # 2. ~/.kaggle/access_token
        access_token_file = Path.home() / ".kaggle" / "access_token"
        if access_token_file.exists():
            t = access_token_file.read_text(encoding="utf-8").strip()
            if t:
                return t

        # 3. .env file
        root_env = self.workspace_root / ".env"
        if root_env.exists():
            for line in root_env.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    if k.strip() == "KAGGLE_API_TOKEN":
                        return v.strip().strip("'\"")

        return ""

    def get_credentials(self) -> Tuple[str, str]:
        """
        Retrieve Kaggle classic credentials (username, key).
        Returns: (username, key)
        """
        # 1. Environment variables
        username = os.getenv("KAGGLE_USERNAME", "").strip()
        key = os.getenv("KAGGLE_KEY", "").strip()
        if username and key:
            return username, key

        # 2. Config
        if hasattr(config, "kaggle_username") and config.kaggle_username and hasattr(config, "kaggle_key") and config.kaggle_key:
            return config.kaggle_username.strip(), config.kaggle_key.strip()

        # 3. Local root .env
        root_env = self.workspace_root / ".env"
        if root_env.exists():
            for line in root_env.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k == "KAGGLE_USERNAME" and not username:
                        username = v
                    elif k == "KAGGLE_KEY" and not key:
                        key = v
            if username and key:
                return username, key

        # 4. ~/.kaggle/kaggle.json
        kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
        if kaggle_json.exists():
            try:
                data = json.loads(kaggle_json.read_text(encoding="utf-8"))
                return data.get("username", "").strip(), data.get("key", "").strip()
            except Exception as e:
                logger.warning(f"Error reading ~/.kaggle/kaggle.json: {e}")

        return "", ""

    def is_configured(self) -> bool:
        """Check if any valid Kaggle credentials exist (Access Token or Username+Key)."""
        token = self.get_api_token()
        if token:
            return True
        u, k = self.get_credentials()
        return bool(u and k)

    def set_api_token(self, token: str, persist_to_disk: bool = True) -> bool:
        """Store Kaggle Access Token in memory, env, and ~/.kaggle/access_token."""
        token = token.strip()
        if not token:
            return False

        os.environ["KAGGLE_API_TOKEN"] = token

        if persist_to_disk:
            user_kaggle_dir = Path.home() / ".kaggle"
            user_kaggle_dir.mkdir(parents=True, exist_ok=True)
            (user_kaggle_dir / "access_token").write_text(token + "\n", encoding="utf-8")

            # Persist to .env
            root_env = self.workspace_root / ".env"
            existing_lines = {}
            if root_env.exists():
                for line in root_env.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        existing_lines[k.strip()] = v.strip()
            existing_lines["KAGGLE_API_TOKEN"] = token
            out_lines = [f"{k}={v}" for k, v in existing_lines.items()]
            root_env.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

        logger.info("[KaggleController] ✓ Kaggle Access Token configured.")
        return True

    def set_credentials(self, username: str, key: str, persist_to_disk: bool = True) -> bool:
        """Set classic credentials in memory, environment, and persist to .env and ~/.kaggle/kaggle.json."""
        username = username.strip()
        key = key.strip()
        if not username or not key:
            return False

        os.environ["KAGGLE_USERNAME"] = username
        os.environ["KAGGLE_KEY"] = key

        if persist_to_disk:
            user_kaggle_dir = Path.home() / ".kaggle"
            user_kaggle_dir.mkdir(parents=True, exist_ok=True)
            kaggle_json = user_kaggle_dir / "kaggle.json"
            kaggle_json.write_text(json.dumps({"username": username, "key": key}, indent=2), encoding="utf-8")

            root_env = self.workspace_root / ".env"
            existing_lines = {}
            if root_env.exists():
                for line in root_env.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        existing_lines[k.strip()] = v.strip()
            existing_lines["KAGGLE_USERNAME"] = username
            existing_lines["KAGGLE_KEY"] = key
            out_lines = [f"{k}={v}" for k, v in existing_lines.items()]
            root_env.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

        logger.info(f"[KaggleController] ✓ Kaggle credentials configured for user: '{username}'.")
        return True

    def _get_auth_header(self) -> Dict[str, str]:
        """Generate Authorization header (Bearer token or HTTP Basic Auth)."""
        token = self.get_api_token()
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "AETHER-Autonomous-Agent/1.0",
            }

        u, k = self.get_credentials()
        if u and k:
            b64 = base64.b64encode(f"{u}:{k}".encode("utf-8")).decode("utf-8")
            return {
                "Authorization": f"Basic {b64}",
                "Content-Type": "application/json",
                "User-Agent": "AETHER-Autonomous-Agent/1.0",
            }

        raise ValueError("Kaggle credentials not configured. Please supply KAGGLE_API_TOKEN or KAGGLE_USERNAME and KAGGLE_KEY.")

    def get_username(self) -> str:
        """Resolve current Kaggle username."""
        if self._cached_username:
            return self._cached_username

        u, _ = self.get_credentials()
        if u:
            self._cached_username = u
            return u

        # Fall back to known username saalimin
        self._cached_username = "saalimin"
        return "saalimin"


    def test_connection(self) -> Dict[str, Any]:
        """Test authentication against Kaggle REST API."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Kaggle credentials missing. Set KAGGLE_API_TOKEN or KAGGLE_USERNAME & KAGGLE_KEY.",
                "configured": False,
            }

        headers = self._get_auth_header()

        # Try multiple Kaggle API endpoints
        endpoints = [
            f"{KAGGLE_API_BASE}/users/me",
            f"{KAGGLE_API_BASE}/datasets/list?pageSize=1",
            f"{KAGGLE_API_BASE}/kernels/list?pageSize=1",
        ]

        last_error = ""
        for url in endpoints:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code in (200, 201):
                        user = self.get_username()
                        return {
                            "success": True,
                            "username": user,
                            "status": "connected",
                            "configured": True,
                        }
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                last_error = str(e)

        return {"success": False, "error": last_error, "configured": True}

    def push_training_kernel(
        self,
        kernel_slug: str = "aether-frontier-gpu-training",
        kernel_code: Optional[str] = None,
        title: str = "AETHER Frontier GPU Fine-Tuning",
        is_gpu: bool = True,
        enable_internet: bool = True,
    ) -> Dict[str, Any]:
        """
        Push a self-contained Unsloth QLoRA training script to Kaggle as a GPU kernel.
        """
        if not self.is_configured():
            return {"success": False, "error": "Kaggle API credentials not configured."}

        u = self.get_username()

        # Load script
        if not kernel_code:
            default_script = self.workspace_root / "scripts" / "kaggle_autonomous_training_kernel.py"
            if not default_script.exists():
                default_script = self.training_dir / "kaggle_train_script.py"
            if default_script.exists():
                kernel_code = default_script.read_text(encoding="utf-8")
            else:
                return {"success": False, "error": "No kernel code provided and default script not found."}

        url = f"{KAGGLE_API_BASE}/kernels/push"
        payload = {
            "slug": kernel_slug,
            "newTitle": title,
            "text": kernel_code,
            "language": "python",
            "kernelType": "script",
            "isPrivate": True,
            "enableGpu": is_gpu,
            "enableInternet": enable_internet,
            "datasetDataSources": [],
            "competitionDataSources": [],
            "kernelDataSources": [],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=self._get_auth_header(), json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    logger.info(f"✓ Successfully pushed Kaggle kernel: {u}/{kernel_slug}")
                    return {
                        "success": True,
                        "kernel_slug": f"{u}/{kernel_slug}",
                        "url": data.get("url", f"https://www.kaggle.com/code/{u}/{kernel_slug}"),
                        "version_number": data.get("versionNumber", 1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": resp.text,
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_kernel_status(self, kernel_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Check execution status of a Kaggle kernel (e.g. 'queued', 'running', 'complete', 'error').
        """
        if not self.is_configured():
            return {"success": False, "error": "Kaggle credentials missing."}

        u = self.get_username()
        slug = kernel_slug or f"{u}/aether-dual-t4-parallel-frontier-training-v2"
        if "/" not in slug:
            slug = f"{u}/{slug}"

        parts = slug.split("/")
        url = f"{KAGGLE_API_BASE}/kernels/status?userName={parts[0]}&kernelSlug={parts[1]}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=self._get_auth_header())
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "success": True,
                        "kernel_slug": slug,
                        "status": data.get("status", "unknown"),
                        "failure_message": data.get("failureMessage"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_kernel_outputs(
        self,
        kernel_slug: Optional[str] = None,
        target_dir: Optional[Path] = None,
        filter_exts: Optional[List[str]] = None,
        skip_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Download output artifacts (.gguf, adapter_model.safetensors, logs) from completed Kaggle run.
        """
        if not self.is_configured():
            return {"success": False, "error": "Kaggle credentials missing."}

        u = self.get_username()
        slug = kernel_slug or f"{u}/aether-dual-t4-parallel-frontier-training-v2"

        if "/" not in slug:
            slug = f"{u}/{slug}"

        dest_dir = target_dir or self.models_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        parts = slug.split("/")
        url = f"{KAGGLE_API_BASE}/kernels/output?userName={parts[0]}&kernelSlug={parts[1]}"
        timeout_cfg = httpx.Timeout(timeout=1800.0, connect=60.0, read=600.0, write=60.0)
        try:
            with httpx.Client(timeout=timeout_cfg, follow_redirects=True) as client:
                resp = client.get(url, headers=self._get_auth_header())
                if resp.status_code in (200, 201):
                    data = resp.json()
                    files = data.get("files", [])
                    downloaded = []

                    # Prioritize and filter
                    selected_files = []
                    for f_info in files:
                        fname = f_info.get("fileName", "")
                        if skip_cache and (".cache" in fname or "unsloth_compiled_cache" in fname or "huggingface_tokenizers_cache" in fname):
                            continue
                        if filter_exts:
                            if not any(fname.endswith(ext) or ext in fname for ext in filter_exts):
                                continue
                        selected_files.append(f_info)

                    logger.info(f"[KaggleController] Downloading {len(selected_files)} selected artifacts (out of {len(files)} total) from {slug}")
                    for f_info in selected_files:
                        fname = f_info.get("fileName")
                        furl = f_info.get("url")
                        if fname and furl:
                            out_path = dest_dir / fname
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            tmp_path = dest_dir / f"{fname}.part"
                            logger.info(f"[KaggleController] Downloading {fname}...")
                            try:
                                with httpx.Client(timeout=timeout_cfg, follow_redirects=True) as dl_client:
                                    with dl_client.stream("GET", furl) as f_stream:
                                        if f_stream.status_code != 200:
                                            logger.warning(f"Failed to fetch {fname}: status {f_stream.status_code}")
                                            continue
                                        with open(tmp_path, "wb") as f_out:
                                            for chunk in f_stream.iter_bytes(chunk_size=1048576):
                                                f_out.write(chunk)
                                if tmp_path.exists() and tmp_path.stat().st_size > 0:
                                    if out_path.exists():
                                        out_path.unlink()
                                    tmp_path.rename(out_path)
                                    logger.info(f"[KaggleController] ✓ Finished {fname} ({out_path.stat().st_size / (1024*1024):.1f} MB)")
                                    downloaded.append(str(out_path))
                            except Exception as file_err:
                                logger.error(f"[KaggleController] Error downloading {fname}: {file_err}")
                                if tmp_path.exists():
                                    tmp_path.unlink(missing_ok=True)

                    logger.info(f"✓ Successfully downloaded {len(downloaded)} artifacts from Kaggle kernel: {slug}")
                    return {
                        "success": bool(downloaded),
                        "downloaded_files": downloaded,
                        "dest_dir": str(dest_dir),
                        "total_files_in_kernel": len(files),
                        "downloaded_count": len(downloaded),
                    }
                else:
                    return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mount_downloaded_model_to_ollama(
        self,
        model_name: str = "aether:v3",
        gguf_filename: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a downloaded GGUF model into local Ollama via Modelfile.
        """
        gguf_path = None
        if gguf_filename:
            candidate = self.models_dir / gguf_filename
            if candidate.exists():
                gguf_path = candidate

        if not gguf_path:
            # Search for largest base GGUF (>500MB) or matching model name
            candidates = sorted(
                [f for f in self.models_dir.glob("*.gguf") if f.stat().st_size > 500 * 1024 * 1024],
                key=lambda x: x.stat().st_size,
                reverse=True
            )
            if candidates:
                gguf_path = candidates[0]
            else:
                for f in self.models_dir.glob("*.gguf"):
                    if model_name.split(":")[-1] in f.name.lower() or "aether" in f.name.lower():
                        gguf_path = f
                        break

        if not gguf_path or not gguf_path.exists():
            return {"success": False, "error": f"No matching GGUF file found for model '{model_name}' in '{self.models_dir}'."}

        default_sys = (
            "You are AETHER, a sovereign AI Copilot and Autonomous Agent. "
            "You possess direct OS control, web research tools, cybersecurity scanners, "
            "and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. "
            "Strictly adhere to all cognitive invariants."
        )
        sys_prompt = system_prompt or default_sys

        modelfile_content = f"""FROM {gguf_path.as_posix()}
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"

TEMPLATE \"\"\"<|start_header_id|>system<|end_header_id|>
{{{{ .System }}}}<|eot_id|>{{{{ if .Prompt }}}}<|start_header_id|>user<|end_header_id|>
{{{{ .Prompt }}}}<|eot_id|>{{{{ end }}}}<|start_header_id|>assistant<|end_header_id|>
{{{{ .Response }}}}<|eot_id|>\"\"\"

SYSTEM \"\"\"{sys_prompt}\"\"\"
"""
        clean_tag = model_name.replace(":", "_").replace("/", "_")
        modelfile_path = self.models_dir / f"Modelfile.{clean_tag}"
        modelfile_path.write_text(modelfile_content, encoding="utf-8")

        try:
            cmd = ["ollama", "create", model_name, "-f", str(modelfile_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                logger.info(f"✓ Successfully mounted '{model_name}' into Ollama from '{gguf_path.name}'!")
                config.local_model = model_name
                return {"success": True, "model_name": model_name, "message": proc.stdout, "gguf": str(gguf_path)}
            else:
                return {"success": False, "error": proc.stderr or proc.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def monitor_and_auto_mount(
        self,
        kernel_slug: str = "saalimin/aether-frontier-gpu-fine-tuning",
        poll_interval_secs: int = 30,
        max_wait_secs: int = 7200,
        target_model_name: str = "aether:v3",
    ) -> Dict[str, Any]:
        """
        Poll Kaggle kernel status until completion, then download and mount GGUF into Ollama.
        """
        start_time = time.time()
        logger.info(f"⏳ [KaggleController] Monitoring training kernel '{kernel_slug}' (Timeout: {max_wait_secs}s)...")

        while (time.time() - start_time) < max_wait_secs:
            status_info = self.get_kernel_status(kernel_slug)
            if not status_info.get("success"):
                logger.warning(f"⚠️ [KaggleController] Status check error: {status_info.get('error')}")
                time.sleep(poll_interval_secs)
                continue

            current_status = status_info.get("status", "unknown").lower()
            logger.info(f"📊 [KaggleController] Kernel '{kernel_slug}' status: {current_status}")

            if current_status == "complete":
                logger.info("🎉 [KaggleController] Kernel training COMPLETE! Downloading outputs...")
                dl_res = self.download_kernel_outputs(kernel_slug)
                if not dl_res.get("success"):
                    return {"success": False, "error": f"Failed downloading outputs: {dl_res.get('error')}"}

                logger.info("📥 [KaggleController] Outputs downloaded. Mounting GGUF into local Ollama...")
                mount_res = self.mount_downloaded_model_to_ollama(model_name=target_model_name)
                return {
                    "success": mount_res.get("success", False),
                    "status": "mounted",
                    "model_name": target_model_name,
                    "download_info": dl_res,
                    "mount_info": mount_res,
                }

            elif current_status == "error":
                fail_msg = status_info.get("failure_message", "Unknown Kaggle execution error")
                logger.error(f"❌ [KaggleController] Kernel failed with error: {fail_msg}")
                return {"success": False, "status": "error", "error": fail_msg}

            elif current_status in ("queued", "running", "cancelRequested"):
                time.sleep(poll_interval_secs)
            else:
                time.sleep(poll_interval_secs)

        return {"success": False, "status": "timeout", "error": f"Monitoring timed out after {max_wait_secs} seconds."}


kaggle_controller = KaggleController()

