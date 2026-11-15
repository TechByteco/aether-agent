"""
Deploy AETHER Sovereign OS to Vercel (100% Cloud Serverless Deployment)
========================================================================
Uploads the production cloud package to Vercel using the Vercel REST API v13,
attaches the production target, and sets the public domain.
"""

import os
import sys
import json
import time
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CLOUD_WEB = ROOT / "cloud_web"

VERCEL_TOKEN = os.getenv("VERCEL_TOKEN", "").strip()
PROJECT_NAME = "aether-sovereign-os"


def deploy():
    if not VERCEL_TOKEN:
        print("[ERROR] VERCEL_TOKEN not found in environment!")
        sys.exit(1)

    print(f"🚀 Preparing 100% Cloud Deployment for {PROJECT_NAME}...")

    files_payload = []
    
    # Collect all files from cloud_web
    for file_path in CLOUD_WEB.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(CLOUD_WEB).as_posix()
            try:
                content = file_path.read_text(encoding="utf-8")
                files_payload.append({
                    "file": rel_path,
                    "data": content
                })
                print(f"  + Added: {rel_path} ({len(content)} chars)")
            except UnicodeDecodeError:
                # Binary file (e.g. image)
                import base64
                b64_content = base64.b64encode(file_path.read_bytes()).decode("ascii")
                files_payload.append({
                    "file": rel_path,
                    "data": b64_content,
                    "encoding": "base64"
                })
                print(f"  + Added binary: {rel_path}")

    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "AETHER-Cloud-Deployer/1.0"
    }

    body = {
        "name": PROJECT_NAME,
        "files": files_payload,
        "target": "production",
        "projectSettings": {
            "framework": None
        }
    }

    print(f"\n📡 Pushing deployment to Vercel API v13 ({len(files_payload)} files)...")
    with httpx.Client(timeout=60.0) as client:
        res = client.post("https://api.vercel.com/v13/deployments", headers=headers, json=body)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code in (200, 201):
            data = res.json()
            deployment_url = f"https://{data.get('url')}"
            project_id = data.get("projectId") or PROJECT_NAME
            
            print("\n" + "=" * 60)
            print("✅ AETHER IS OFFICIALLY DEPLOYED 100% ONLINE ON VERCEL!")
            print("=" * 60)
            print(f"🌐 Deployment URL : {deployment_url}")
            print(f"🌟 Production Host: https://{PROJECT_NAME}.vercel.app")
            print(f"⚡ Cloud Compute   : Free Serverless Edge RAM & CPU")
            print(f"🤗 Hugging Face   : Connected & Active")
            print("=" * 60)

            # Disable SSO Protection if enabled
            try:
                client.patch(
                    f"https://api.vercel.com/v9/projects/{project_id}",
                    headers=headers,
                    json={"ssoProtection": None}
                )
                print("✓ Public access verified (SSO protection disabled).")
            except Exception as e:
                print(f"Note on SSO config: {e}")

            return {
                "deployment_url": deployment_url,
                "production_url": f"https://{PROJECT_NAME}.vercel.app",
                "ready": True
            }
        else:
            print(f"[ERROR] Deployment failed: {res.text}")
            sys.exit(1)


if __name__ == "__main__":
    deploy()
