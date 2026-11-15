"""
AETHER Cyber-Guardian & Threat Reconnaissance Module
Provides sovereign, zero-dependency cybersecurity tools:
- Active socket & outbound connection audit
- Port & daemon exposure reconnaissance
- SSL/TLS certificate verification & expiration inspection
- High-speed repository secret & credential leak hunter
"""

import os
import re
import socket
import ssl
from pathlib import Path
from typing import Dict, List, Optional

import psutil

COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995,
    1433, 1521, 3000, 3306, 5000, 5432, 6379, 8000, 8080, 8443,
    9000, 11434, 27017
]

SECRET_PATTERNS = [
    (r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", "API Key"),
    (r"(?i)secret[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", "Secret Key"),
    (r"(?i)access[_-]?token\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", "Access Token"),
    (r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})", "Bearer Token"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Key Header"),
    (r"(?i)password\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]", "Plaintext Password"),
]


def audit_active_connections(filter_state: str = "ALL") -> str:
    """
    Audit active network connections across all local processes.
    Flags listening daemons, established outbound sessions, and process owners.
    """
    clean_filter = filter_state.upper().strip()
    try:
        connections = psutil.net_connections(kind="inet")
    except Exception as e:
        return f"Connection audit error (elevated privileges may be required): {e}"

    results = []
    listening_ports = []
    established = []

    for conn in connections:
        state = conn.status
        if clean_filter != "ALL" and state != clean_filter:
            continue

        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
        pid = conn.pid or "N/A"
        pname = "Unknown"
        if conn.pid:
            try:
                pname = psutil.Process(conn.pid).name()
            except Exception:
                pass

        entry = {
            "proto": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
            "local": laddr,
            "remote": raddr,
            "status": state,
            "pid": pid,
            "process": pname,
        }

        if state == "LISTEN":
            listening_ports.append(entry)
        elif state == "ESTABLISHED":
            established.append(entry)
        else:
            results.append(entry)

    lines = ["### 🛡️ AETHER Cyber-Guardian: Network Connection Audit\n"]
    lines.append(f"**Total Connections Found:** {len(connections)}")
    lines.append(f"**Open Listening Daemons:** {len(listening_ports)}")
    lines.append(f"**Established Outbound Sockets:** {len(established)}\n")

    lines.append("#### 👂 Open Listening Services:")
    if listening_ports:
        for item in listening_ports[:15]:
            lines.append(f"- `[{item['proto']}]` **{item['local']}** — PID `{item['pid']}` (`{item['process']}`)")
    else:
        lines.append("- *No open listening ports detected under current filter.*")

    lines.append("\n#### 🌐 Established External Connections:")
    if established:
        for item in established[:15]:
            lines.append(f"- **{item['local']}** ➔ **{item['remote']}** (`{item['process']}` [PID {item['pid']}])")
    else:
        lines.append("- *No active established sockets.*")

    return "\n".join(lines)


def scan_network_ports(host: str = "127.0.0.1", ports: str = "") -> str:
    """
    Perform a high-speed TCP socket sweep against target host to detect active network services.
    """
    clean_host = host.strip() or "127.0.0.1"
    target_ports = []
    if ports.strip():
        for part in ports.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = map(int, part.split("-"))
                    target_ports.extend(range(start, min(end + 1, 65535)))
                except Exception:
                    pass
            elif part.isdigit():
                target_ports.append(int(part))
    else:
        target_ports = COMMON_PORTS

    open_ports = []
    for port in target_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.35)
        try:
            res = s.connect_ex((clean_host, port))
            if res == 0:
                try:
                    service_name = socket.getservbyport(port, "tcp")
                except Exception:
                    service_name = "custom"
                open_ports.append((port, service_name))
        except Exception:
            pass
        finally:
            s.close()

    lines = [f"### 🔍 Port Reconnaissance: `{clean_host}`\n"]
    lines.append(f"**Scanned Ports:** {len(target_ports)} targets\n")
    if open_ports:
        lines.append(f"**Open Ports Identified ({len(open_ports)}):**")
        for p, srv in open_ports:
            lines.append(f"- **Port `{p}`** — `{srv.upper()}`")
    else:
        lines.append("✓ *No open ports detected in the specified range.*")

    return "\n".join(lines)


def inspect_ssl_cert(domain: str, port: int = 443) -> str:
    """
    Connect to a remote domain over TLS and inspect the SSL certificate, issuer, and validity period.
    """
    clean_domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((clean_domain, port), timeout=5.0) as sock:
            with ctx.wrap_socket(sock, server_hostname=clean_domain) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        common_name = subject.get("commonName", clean_domain)
        issuer_name = issuer.get("organizationName", issuer.get("commonName", "Unknown Issuer"))
        not_before = cert.get("notBefore", "N/A")
        not_after = cert.get("notAfter", "N/A")

        return (
            f"### 🔒 SSL/TLS Security Audit: `{clean_domain}`\n"
            f"- **Common Name:** `{common_name}`\n"
            f"- **Certificate Authority:** `{issuer_name}`\n"
            f"- **Valid From:** {not_before}\n"
            f"- **Expires On:** {not_after}\n"
            f"- **TLS Protocol:** `{version}`\n"
            f"- **Cipher Suite:** `{cipher[0]} ({cipher[2]}-bit)`\n"
            f"- **Status:** ✓ Trusted & Valid"
        )
    except ssl.SSLError as e:
        return f"⚠ SSL Security Warning for `{clean_domain}`: {e}"
    except Exception as e:
        return f"Could not complete TLS inspection for `{clean_domain}`: {e}"


def hunt_exposed_secrets(target_dir: str = ".") -> str:
    """
    Deep scan a directory or codebase to detect leaked API keys, tokens, passwords, and private keys.
    """
    base_path = Path(target_dir).resolve()
    if not base_path.exists():
        return f"Target path '{target_dir}' does not exist."

    findings = []
    scanned_count = 0
    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode", "dist", "build"}

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            if f.endswith((".pyc", ".png", ".jpg", ".jpeg", ".ico", ".bin", ".exe", ".dll", ".zip", ".tar", ".gz")):
                continue

            file_path = Path(root) / f
            scanned_count += 1
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat, label in SECRET_PATTERNS:
                    matches = re.finditer(pat, text)
                    for m in matches:
                        line_no = text[:m.start()].count("\n") + 1
                        matched_val = m.group(0)[:60]
                        # Redact the middle of the secret for security
                        if len(matched_val) > 12:
                            redacted = matched_val[:6] + "..." + matched_val[-4:]
                        else:
                            redacted = "[REDACTED]"

                        rel_path = file_path.relative_to(base_path)
                        findings.append({
                            "file": str(rel_path),
                            "line": line_no,
                            "type": label,
                            "sample": redacted
                        })
            except Exception:
                pass

    lines = [f"### 🛡️ Exposed Secret & Vulnerability Scan\n"]
    lines.append(f"**Directory Scanned:** `{base_path}`")
    lines.append(f"**Files Analyzed:** {scanned_count} files\n")

    if findings:
        lines.append(f"🚨 **Potential Exposed Secrets Detected ({len(findings)}):**\n")
        for f in findings[:25]:
            lines.append(f"- **{f['type']}** in `{f['file']}:{f['line']}` ➔ `{f['sample']}`")
        if len(findings) > 25:
            lines.append(f"\n*(Truncated: {len(findings) - 25} additional findings)*")
    else:
        lines.append("✓ **Clean Audit:** No exposed API keys, private keys, or plaintext secrets found.")

    return "\n".join(lines)
