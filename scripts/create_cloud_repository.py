"""
AETHER Sovereign Cloud Repository Creator & Deployer
=====================================================
Automates 1-click cloud repository creation and deployment across:
1. Hugging Face Spaces (Static or Docker) via huggingface_hub API
2. GitHub Repositories via GitHub REST API v3
3. Kaggle Cloud Agent & Dataset Hub

Usage:
  python scripts/create_cloud_repository.py --hf-token <HF_TOKEN> --space-name <SPACE_NAME>
  python scripts/create_cloud_repository.py --github-token <GH_TOKEN> --repo-name <REPO_NAME>
  python scripts/create_cloud_repository.py --interactive
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def deploy_huggingface_space(token: str, space_name: str = "aether-hud", sdk: str = "static"):
    """Create and push a Hugging Face Space automatically."""
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("[!] huggingface_hub not installed. Run: uv pip install huggingface_hub")
        return False

    api = HfApi(token=token)
    user = api.whoami().get("name")
    repo_id = f"{user}/{space_name}"

    print(f"[*] Authenticated as Hugging Face User: {user}")
    print(f"[*] Creating {sdk.upper()} Space: {repo_id}...")

    try:
        url = create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk=sdk,
            token=token,
            exist_ok=True,
            private=False
        )
        print(f"[OK] Space initialized: {url}")
    except Exception as e:
        print(f"[!] Note on repo creation: {e}")

    # Upload files
    source_dir = WORKSPACE_ROOT / "cloud_deployment" / ("static_space" if sdk == "static" else "")
    print(f"[*] Uploading files from {source_dir}...")

    try:
        api.upload_folder(
            folder_path=str(source_dir),
            repo_id=repo_id,
            repo_type="space",
            token=token
        )
        live_url = f"https://huggingface.co/spaces/{repo_id}"
        print(f"\n[SUCCESS] AETHER is live 24/7 on Hugging Face Spaces!")
        print(f"🌐 Live URL: {live_url}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to upload files: {e}")
        return False


def deploy_github_repo(token: str, repo_name: str = "aether-agent", private: bool = False):
    """Create a new GitHub repository via REST API and push main branch."""
    import httpx

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AETHER-Autonomous-Deployer/1.0"
    }

    # 1. Get user info
    with httpx.Client(timeout=15.0) as client:
        u_res = client.get("https://api.github.com/user", headers=headers)
        if u_res.status_code != 200:
            print(f"[ERROR] GitHub authentication failed (HTTP {u_res.status_code}): {u_res.text}")
            return False
        user = u_res.json().get("login")
        print(f"[*] Authenticated as GitHub User: {user}")

        # 2. Create repo
        payload = {
            "name": repo_name,
            "description": "AETHER: Autonomous Edge-Tiered Hierarchical Entity for Reasoning (200 Skills & 24/7 Cloud Autonomy)",
            "private": private,
            "auto_init": False
        }
        r_res = client.post("https://api.github.com/user/repos", headers=headers, json=payload)
        if r_res.status_code in (200, 201):
            print(f"[OK] Created GitHub repository: {user}/{repo_name}")
        elif r_res.status_code == 422:
            print(f"[*] Repository {user}/{repo_name} already exists. Proceeding to push...")
        else:
            print(f"[ERROR] Failed to create repository (HTTP {r_res.status_code}): {r_res.text}")
            return False

    # 3. Push main branch via git
    remote_url = f"https://{token}@github.com/{user}/{repo_name}.git"
    
    # Configure remote
    subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
    
    print(f"[*] Checking for repository {user}/{repo_name}...")
    ls_res = subprocess.run(["git", "ls-remote", "origin"], capture_output=True, text=True)
    if ls_res.returncode != 0:
        print(f"\n[NOTICE] Please create the empty repository on GitHub:")
        print(f"👉 Link: https://github.com/new?name={repo_name}")
        print(f"(Keep 'Add README' unchecked and click Create repository)")
        return False

    print("[*] Pushing 'main' branch to GitHub...")
    push_res = subprocess.run(["git", "push", "-u", "origin", "main", "--force"], capture_output=True, text=True)
    if push_res.returncode == 0:
        print(f"\n[SUCCESS] Successfully pushed AETHER to GitHub!")
        print(f"🌐 Repository URL: https://github.com/{user}/{repo_name}")
        return True
    else:
        print(f"[ERROR] Git push failed: {push_res.stderr}")
        return False


def interactive_mode():
    print("=" * 70)
    print("◈ AETHER 1-Click Cloud Repository & Space Creator")
    print("=" * 70)
    print("Select an option:")
    print("1) Deploy to Hugging Face Static Space (100% Free 24/7, No Server Needed)")
    print("2) Create and Push to a New GitHub Repository")
    print("3) Deploy to Hugging Face Docker Space (Full FastAPI backend)")
    print("=" * 70)

    choice = input("Enter choice (1, 2, or 3): ").strip()

    if choice in ("1", "3"):
        token = input("Enter your Hugging Face Token (from https://huggingface.co/settings/tokens): ").strip()
        space_name = input("Enter Space Name (default: aether-hud): ").strip() or "aether-hud"
        sdk = "static" if choice == "1" else "docker"
        if token:
            deploy_huggingface_space(token=token, space_name=space_name, sdk=sdk)
        else:
            print("[!] Token is required.")

    elif choice == "2":
        token = input("Enter your GitHub Personal Access Token (from https://github.com/settings/tokens): ").strip()
        repo_name = input("Enter Repo Name (default: aether-agent): ").strip() or "aether-agent"
        if token:
            deploy_github_repo(token=token, repo_name=repo_name)
        else:
            print("[!] Token is required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy AETHER to Cloud Repository")
    parser.add_argument("--hf-token", help="Hugging Face User Access Token")
    parser.add_argument("--space-name", default="aether-hud", help="Hugging Face Space name")
    parser.add_argument("--sdk", default="static", choices=["static", "docker"], help="Space SDK")
    parser.add_argument("--github-token", help="GitHub Personal Access Token")
    parser.add_argument("--repo-name", default="aether-agent", help="GitHub Repository name")
    parser.add_argument("--interactive", action="store_true", help="Run interactive wizard")

    args = parser.parse_args()

    if args.hf_token:
        deploy_huggingface_space(token=args.hf_token, space_name=args.space_name, sdk=args.sdk)
    elif args.github_token:
        deploy_github_repo(token=args.github_token, repo_name=args.repo_name)
    else:
        interactive_mode()
