"""
AETHER Cognitive Engine
Handles LLM execution, native tool-calling loops, memory recall, and full OS/computer control.
Engineered for Snapdragon compute acceleration, natural language synthesis, and zero JSON leakage.
"""

import gc
import re
from typing import Any, Callable, Dict, List, Optional

import ollama

# ── AGI self-directing planner & observability ───────────────────────────────
from aether.agi.planner import agi_planner
from aether.brain.antigravity_codex_agent import antigravity_codex_agent
from aether.brain.ast_guard import ast_guard
from aether.brain.auto_learner import auto_learner
from aether.brain.autonomous_model_evolver import (
    tool_dispatch_autonomous_cloud_evolution, tool_get_model_evolution_status,
    tool_run_self_play_curriculum_step)
from aether.brain.claude_agent import claude_agent
from aether.brain.cognitive_learner import cognitive_learner
from aether.brain.curriculum_learner import (FRONTIER_DISCIPLINES,
                                             curriculum_learner)
from aether.brain.evolution import evolution_engine
from aether.brain.hybrid_desktop_agent import hybrid_desktop_agent
from aether.brain.kaggle_controller import kaggle_controller
from aether.brain.leon_business_intelligence import (
    tool_leon_business_blueprint, tool_leon_customize_brand,
    tool_leon_find_leads, tool_leon_generate_business_ideas)
from aether.brain.leon_deployer import (tool_leon_create_razorpay_checkout,
                                        tool_leon_create_stripe_payment_link,
                                        tool_leon_deploy_venture_to_cloud,
                                        tool_leon_get_deployed_ventures)
from aether.brain.leon_growth_engine import (
    tool_leon_assign_ui_archetype, tool_leon_draft_personalized_outreach,
    tool_leon_generate_seo_and_web_spec, tool_leon_search_and_qualify_leads)
from aether.brain.leon_portfolio_manager import (
    tool_leon_auto_scale_portfolio_pricing, tool_leon_get_portfolio_status,
    tool_leon_launch_all_low_cost_businesses,
    tool_leon_revise_business_pricing)
from aether.brain.leon_venture_os import (tool_leon_create_venture,
                                          tool_leon_dispatch_subagent_swarm,
                                          tool_leon_get_venture_ledger,
                                          tool_train_leon_venture_model)
from aether.brain.multi_channel_gateway import (
    tool_generate_morning_audio_briefing,
    tool_get_multi_channel_gateway_status)
from aether.brain.multi_provider_router import multi_provider_router
from aether.brain.online_cortex import online_cortex
from aether.brain.online_gateway import (online_gateway,
                                         tool_get_online_tunnel_status,
                                         tool_list_free_online_models,
                                         tool_query_free_online_ai,
                                         tool_start_online_tunnel,
                                         tool_stop_online_tunnel)
from aether.brain.prompts import build_system_prompt
from aether.brain.reflexion_engine import (reflexion_engine,
                                           tool_audit_error_invariants,
                                           tool_reflect_on_error)
from aether.brain.skills_vault import skills_vault
from aether.brain.swarm import SwarmRole, swarm_engine
from aether.brain.task_engagement import EngagementPersona, task_engagement
from aether.brain.thinking_cortex import thinking_cortex
from aether.brain.tool_genesis import (tool_delete_generated_tool,
                                       tool_genesis, tool_list_generated_tools,
                                       tool_synthesize_new_tool)
from aether.cloud.cloud_consciousness_vault import \
    tool_export_cloud_consciousness
from aether.config import config
from aether.memory.hybrid_knowledge_graph import (
    tool_extract_knowledge_triples, tool_query_hybrid_memory,
    tool_query_semantic_knowledge_graph)
from aether.memory.persona import persona
from aether.memory.store import memory
from aether.skills_galaxy import SKILLS_GALAXY_REGISTRY
from aether.system.deterministic_mode import DETERMINISTIC, verify_output
from aether.tools.claude_tools import (claude_bash, claude_edit, claude_find,
                                       claude_grep, claude_subagent,
                                       claude_todo, claude_todos, claude_view,
                                       claude_write)
from aether.tools.cybersecurity import (audit_active_connections,
                                        hunt_exposed_secrets, inspect_ssl_cert,
                                        scan_network_ports)
from aether.tools.desktop_controller import tool_interact_ui as dc_interact_ui
from aether.tools.desktop_controller import \
    tool_launch_or_focus_app as dc_launch_app
from aether.tools.desktop_controller import \
    tool_list_running_applications as dc_list_apps
from aether.tools.desktop_controller import \
    tool_manage_windows_service as dc_manage_service
from aether.tools.desktop_controller import \
    tool_see_screen_and_analyze as dc_see_screen
from aether.tools.entrepreneur import \
    tool_model_venture_unit_economics as ep_model_economics
from aether.tools.entrepreneur import \
    tool_orchestrate_executive_sprint as ep_orchestrate_sprint
from aether.tools.entrepreneur import \
    tool_simulate_cap_table_and_dilution as ep_simulate_cap_table
from aether.tools.entrepreneur import \
    tool_synthesize_investor_memo_and_pitch as ep_synthesize_memo
from aether.tools.entrepreneur import \
    tool_synthesize_technical_prd as ep_synthesize_prd
from aether.tools.global_master import (audit_codebase_architecture,
                                        benchmark_api_endpoint,
                                        inspect_git_repositories,
                                        profile_process_telemetry)
from aether.tools.guardrails import (assert_safe_resources,
                                     format_vitals_summary, get_system_vitals)
from aether.tools.intel_gatherer import (fetch_daily_threat_intel,
                                         fetch_tech_frontier_radar,
                                         generate_morning_briefing,
                                         profile_domain_osint)
from aether.tools.npu_accelerator import (get_npu_status,
                                          hardware_accelerated_screen_ocr)
from aether.tools.npu_speculative_accelerator import (
    tool_benchmark_speculative_decoding, tool_inspect_hardware_acceleration)
from aether.tools.open_knowledge import (browse_web_page, deep_web_research,
                                         search_arxiv, search_web,
                                         search_wikipedia)
from aether.tools.system_ops import (control_system_volume, diff_files,
                                     execute_system_command, find_files,
                                     get_active_window_title, get_current_time,
                                     get_network_status, get_recent_files,
                                     get_storage_status, get_system_info,
                                     inspect_directory, list_running_processes,
                                     lock_workstation, lookup_world_map,
                                     open_application, open_browser_url,
                                     play_youtube_media, read_clipboard,
                                     read_text_file, search_files_by_content,
                                     set_display_brightness, take_screenshot,
                                     translate_language, write_clipboard,
                                     write_text_file)
from aether.tools.vision import analyze_image, analyze_live_screen
from aether.tools.visual_som_grounding import (tool_capture_screen_with_som,
                                               tool_execute_som_action)
from aether.tools.voice import (tool_list_available_voices,
                                tool_set_voice_persona, tool_speak_phrase,
                                voice)
from aether.tools.wake_word_engine import (tool_get_wake_word_status,
                                           tool_start_wake_word_listener)
from aether.utils.asset_registry import asset_registry

# --- Tool Definitions exposed to the Model ---

def tool_query_online_cortex(prompt: str, model: str = "", system_directive: str = "") -> str:
    """Query high-intelligence online models via FreeLLMAPI (e.g. Llama-3.3-70B, DeepSeek-R1, Gemini 2.0 Flash) using 7.4B monthly free token pool."""
    try:
        return online_cortex.query_online_cortex(
            prompt=prompt,
            model=model if model.strip() else None,
            system_prompt=system_directive if system_directive.strip() else None,
        )
    except Exception as e:
        return f"Online Cortex error: {e}"


def tool_dispatch_online_agent_swarm(objective: str, roles: str = "code_architect,security_auditor,reasoning_analyst") -> str:
    """Concurrently dispatch an objective across specialized online AI agents via FreeLLMAPI and synthesize multi-agent findings."""
    role_list = [r.strip() for r in roles.split(",") if r.strip()]
    res = online_cortex.dispatch_agent_swarm(objective=objective, roles=role_list)
    if "error" in res:
        return f"Swarm dispatch error: {res['error']}"
    lines = [f"### 🤖 Online Agent Swarm ({res['agents_count']} Agents Active)\n**Objective:** {res['objective']}\n"]
    for role, report in res.get("agents", {}).items():
        lines.append(f"#### Agent [{role.upper()}]\n{report}\n")
    return "\n".join(lines)


def tool_freellmapi_status() -> str:
    """Check the operational status of the FreeLLMAPI gateway, port 3001, and connected free LLM providers."""
    status = online_cortex.check_gateway_health()
    if status.get("online"):
        return (
            f"✓ FreeLLMAPI Gateway is ONLINE\n"
            f"- Endpoint: {status['endpoint']}\n"
            f"- Endpoints Available: {status['model_count']}\n"
            f"- Sample Models: {', '.join(status['models'][:5])}"
        )
    return (
        f"⚠ FreeLLMAPI Gateway is OFFLINE\n"
        f"- Target Endpoint: {status['endpoint']}\n"
        f"- Error: {status.get('error', 'Unreachable')}\n"
        f"- Hint: {status.get('hint', '')}"
    )


def tool_trigger_evolution(topic: str = "") -> str:
    """Trigger an autonomous evolutionary self-learning cycle to research frontiers, acquire new heuristic rules, and curate fine-tuning data."""
    active_m = engine.resolve_active_model() if 'engine' in globals() else config.local_model
    res = evolution_engine.run_evolution_cycle(topic=topic if topic.strip() else None, active_model=active_m)
    rules_text = "\n".join([f"- [#{r['id']}] ({r['domain'].upper()}) {r['rule']}" for r in res.get("rules_added", [])])
    return (
        f"### 🧬 Evolutionary Cycle Complete (Gen {res['generation']} → Gen {res['next_generation']})\n"
        f"**Topic Researched:** {res['topic']}\n"
        f"**New Rules Acquired:**\n{rules_text or 'None extracted'}\n"
        f"**Synthetic Training Dataset Size:** {res['dataset_count']} paired samples"
    )


def tool_inspect_auto_learning_metrics() -> str:
    """Inspect real-time continuous learning statistics, total procedural rules, and curated training dataset size."""
    metrics = auto_learner.get_learning_metrics()
    rules_sample = "\n".join([f"- {r}" for r in metrics.get("recent_rules", [])[:5]])
    return (
        f"### 🧠 AETHER Continuous Auto-Learning System\n"
        f"- **Status:** {metrics['status']}\n"
        f"- **Total Procedural Heuristics:** {metrics['total_rules_in_memory']}\n"
        f"- **Personal Facts Stored:** {metrics['total_facts_stored']}\n"
        f"- **Curated Synthetic Fine-Tuning Samples:** {metrics['synthetic_dataset_samples']} pairs\n\n"
        f"**Recent Learned Rules:**\n{rules_sample or '- None active yet'}"
    )


def tool_auto_learn_from_context(title: str, text: str, domain: str = "general") -> str:
    """Explicitly ingest a document, code snippet, or guidelines to distill procedural heuristics and training pairs."""
    auto_learner.curate_training_example(title, text, domain=domain)
    rule_id = memory.add_heuristic_rule(f"{title}: {text[:150]}...", domain=domain)
    return f"✓ Ingested '{title}' into long-term procedural memory (Rule #{rule_id})."


def tool_search_skills(query: str, limit: int = 6) -> str:
    """Search across 2,400+ Antigravity skills, design registries, and agent blueprints for relevant techniques and frameworks."""
    results = skills_vault.search_skills(query, limit=limit)
    if not results:
        return f"No skills matching '{query}' found."
    lines = [f"### 🔍 Antigravity Skills Search Results for '{query}':"]
    for s in results:
        lines.append(f"- **{s['name']}** (`{s['category']}` | {s['source']}): {s['description']}")
    lines.append("\n*To load any skill's full workflow and directives, call `tool_load_skill('<skill-name>')`.*")
    return "\n".join(lines)


def tool_load_skill(skill_name: str) -> str:
    """Load the complete operational workflow, patterns, and instructions of any Antigravity skill from its SKILL.md."""
    return skills_vault.load_skill(skill_name)


def tool_list_skills(category: str = "", limit: int = 20) -> str:
    """Browse skills in the Universal Vault by category (ui_ux, security, architecture_code, ai_agents, cloud_data, science_bio)."""
    results = skills_vault.list_skills(category=category, limit=limit)
    if not results:
        return f"No skills found in category '{category}'."
    header = f"### 📚 Available Antigravity Skills ({category.upper() or 'ALL'}):\n"
    lines = [f"- **{s['name']}** [{s['category']}]: {s['description']}" for s in results]
    return header + "\n".join(lines)


def tool_skills_vault_status() -> str:
    """Check the operational status, total indexed skills, and component registries in the Universal Antigravity Vault."""
    stats = skills_vault.get_vault_stats()
    cat_str = "\n".join([f"  * {k}: {v} skills" for k, v in stats['by_category'].items()])
    src_str = "\n".join([f"  * {k}: {v} skills" for k, v in stats['by_source'].items()])
    regs = ", ".join(stats.get('design_registries', []))
    return (
        f"### 🏛️ Universal Antigravity Skill Vault Status\n"
        f"- **Total Indexed Skills:** {stats['total_skills']}\n"
        f"- **Component Registries Connected:** {regs}\n\n"
        f"**By Category:**\n{cat_str}\n\n"
        f"**By Source:**\n{src_str}"
    )

# ── Cyber-Guardian & Threat Reconnaissance Tools ────────────────────────────
def tool_audit_active_connections(filter_state: str = "ALL") -> str:
    """Audit active network connections across all local processes. Inspects open listening ports, established sockets, and process owners."""
    return audit_active_connections(filter_state=filter_state)


def tool_scan_network_ports(host: str = "127.0.0.1", ports: str = "") -> str:
    """Scan target host ports to detect active network services, exposed daemons, and listening endpoints."""
    return scan_network_ports(host=host, ports=ports)


def tool_inspect_ssl_cert(domain: str, port: int = 443) -> str:
    """Connect to a remote domain over TLS and inspect the SSL certificate, expiration date, issuer, and cipher strength."""
    return inspect_ssl_cert(domain=domain, port=port)


def tool_hunt_exposed_secrets(target_dir: str = ".") -> str:
    """Deep scan a directory or codebase to detect leaked API keys, tokens, passwords, and private keys."""
    return hunt_exposed_secrets(target_dir=target_dir)


# ── Daily Intel Gathering & Frontier OSINT Radar Tools ──────────────────────
def tool_fetch_daily_threat_intel(limit: int = 5) -> str:
    """Fetch active high-severity cybersecurity threats, zero-days, and CVE advisories from CISA KEV and vulnerability databases."""
    return fetch_daily_threat_intel(limit=limit)


def tool_fetch_tech_frontier_radar(category: str = "all", limit: int = 5) -> str:
    """Fetch trending breakthroughs in AI/ML, distributed systems, and open-source frontiers from Hacker News and ArXiv."""
    return fetch_tech_frontier_radar(category=category, limit=limit)


def tool_profile_domain_osint(domain: str) -> str:
    """Perform OSINT domain footprinting: DNS resolution (IPs, MX, TXT), HTTP security headers, and server fingerprinting."""
    return profile_domain_osint(domain=domain)


def tool_generate_morning_briefing() -> str:
    """Synthesize an autonomous executive morning intelligence briefing: threat advisories + frontier tech headlines + system vitals."""
    return generate_morning_briefing()


# ── Global Master Tech & Systems Architecture Tools ─────────────────────────
def tool_benchmark_api_endpoint(url: str, num_requests: int = 10, method: str = "GET") -> str:
    """Benchmark an API endpoint or website: measures min/p50/p95/max latency, throughput (req/sec), status code distribution, and response payload size."""
    return benchmark_api_endpoint(url=url, num_requests=num_requests, method=method)


def tool_audit_codebase_architecture(target_dir: str = ".", max_files: int = 100) -> str:
    """Perform deep static analysis of a codebase: flags monolith files (>500 lines), god functions (>50 lines), technical debt tags (TODO/FIXME), and computes Clean-Code Health Grade."""
    return audit_codebase_architecture(target_dir=target_dir, max_files=max_files)


def tool_profile_process_telemetry(target: str = "") -> str:
    """Profile system processes: inspects memory usage (RSS, VMS), CPU utilization, thread allocation, open file handles, and flags potential memory leaks."""
    return profile_process_telemetry(target=target)


def tool_inspect_git_repositories(search_dir: str = ".") -> str:
    """Search and audit Git repositories under a path: reports branch name, uncommitted changes, untracked files, ahead/behind upstream status, and last commit."""
    return inspect_git_repositories(search_dir=search_dir)


# ── Claude Code Agent Tools ──────────────────────────────────────────────────
def tool_claude_bash(command: str, timeout_secs: int = 45, cwd: str = "") -> str:
    """Execute shell command with strict exit code reporting, working directory support, and stdout/stderr separation."""
    return claude_bash(command, timeout_secs=timeout_secs, cwd=cwd if cwd.strip() else None)

def tool_claude_view(file_path: str, start_line: int = 1, end_line: int = 100) -> str:
    """Read file contents with 1-indexed line numbers (cat -n style). Supports pagination to prevent context saturation."""
    return claude_view(file_path, start_line=start_line, end_line=end_line)

def tool_claude_edit(file_path: str, old_string: str, new_string: str) -> str:
    """Surgical string replacement editor (str_replace_editor). Requires exact unique match and verifies with a unified diff."""
    return claude_edit(file_path, old_string=old_string, new_string=new_string)

def tool_claude_write(file_path: str, content: str) -> str:
    """Create or overwrite a file with complete content, automatically creating parent directories."""
    return claude_write(file_path, content)

def tool_claude_grep(query: str, path: str = ".", glob_filter: str = "*", case_sensitive: bool = False) -> str:
    """Fast ripgrep-compatible regex search across codebases with line numbers."""
    return claude_grep(query, path=path, glob_filter=glob_filter, case_sensitive=case_sensitive)

def tool_claude_find(pattern: str, path: str = ".", max_results: int = 50) -> str:
    """Fast filename and directory search using glob patterns."""
    return claude_find(pattern, path=path, max_results=max_results)

def tool_claude_todo(action: str = "list", text: str = "", task_id: str = "") -> str:
    """Manage Claude Code's internal task tracking list ('add', 'start', 'done', 'list', 'clear')."""
    return claude_todo(action=action, text=text, task_id=task_id)

def tool_claude_subagent(role: str, objective: str, context: str = "") -> str:
    """Spawn an autonomous specialized subagent in an isolated context to execute a task and report back."""
    return claude_subagent(role=role, objective=objective, context=context)


def tool_control_volume(action: str = "toggle") -> str:

    """Control PC system volume immediately (actions: 'up', 'down', 'mute', 'unmute', 'toggle')."""
    return control_system_volume(action)


def tool_set_brightness(level: int) -> str:
    """Set laptop screen brightness percentage (0-100) via Windows WMI hardware controller."""
    return set_display_brightness(level)


def tool_translate_text(text: str, target_lang: str = "spanish") -> str:
    """Translate text into a target language (e.g. 'French', 'Spanish', 'Japanese', 'German', 'Hindi') in ~250ms."""
    return translate_language(text, target_lang)


def tool_show_world_map(location: str, zoom: int = 12) -> str:
    """Geocode a location and display an interactive Leaflet world map with pins and coordinates in the HUD."""
    return lookup_world_map(location, zoom)


def tool_instant_screen_ocr(*args, **kwargs) -> str:
    """Instantly extract visible text from the screen using hardware-accelerated WinRT OCR (~200ms). Preferred over vision models when looking for error text, codes, or readable content."""
    return hardware_accelerated_screen_ocr()


def tool_execute_python_code(code: str) -> str:
    """Execute Python code in a safe sandbox to perform calculations, data processing, file manipulation, or algorithm testing."""
    return execute_python_code(code)


def tool_analyze_screen(prompt: str = "Describe what is visible on my screen.") -> str:
    """Capture the current computer screen and analyze its visual contents, active windows, text, or errors."""
    return analyze_live_screen(prompt=prompt)


def tool_analyze_image(image_path: str, prompt: str = "Describe what you see in detail.") -> str:
    """Analyze any image file or photo on disk (PNG, JPG, etc.) and describe its visual elements, objects, and text."""
    return analyze_image(image_path=image_path, prompt=prompt)


def tool_play_youtube_media(song_or_query: str) -> str:
    """Play any song, music, artist, or video on YouTube. Automatically opens Google Chrome and starts playing."""
    return play_youtube_media(song_or_query)


def tool_open_application(app_name: str) -> str:
    """Launch an application on this computer (e.g. 'chrome', 'notepad', 'calculator', 'edge', 'spotify', 'terminal')."""
    return open_application(app_name)


def tool_open_browser_url(url: str) -> str:
    """Open any website URL in Google Chrome (or default browser)."""
    return open_browser_url(url)


def tool_lock_computer() -> str:
    """Lock the computer screen immediately."""
    return lock_workstation()


def tool_take_screenshot(filename: str = "") -> str:
    """Capture the current computer screen and save it to data/screenshots/."""
    return take_screenshot(filename)


def tool_search_web(query: str) -> str:
    """Search the internet for current news, live facts, schedules, documentation, and external information."""
    return search_web(query)


def tool_browse_web_page(url: str) -> str:
    """Visit a specific website URL and read its actual article text."""
    return browse_web_page(url)


def tool_deep_web_research(query: str) -> str:
    """Perform deep multi-source research across the web with full page extracts and citations."""
    return deep_web_research(query)


def tool_search_wikipedia(query: str) -> str:
    """Search Wikipedia for definitions, concepts, biographies, scientific principles, and history."""
    return search_wikipedia(query)


def tool_search_arxiv(query: str) -> str:
    """Search arXiv for peer-reviewed research papers and AI breakthroughs."""
    return search_arxiv(query)


def tool_remember_fact(entity: str, attribute: str, value: str) -> str:
    """
    Store an important personal fact or project preference into disk memory.
    Use this when learning user details, preferences, or ongoing goals.
    """
    memory.remember_fact(entity, attribute, value)
    persona.append_fact_to_profile(f"{entity.capitalize()} {attribute}: {value}")
    return f"Stored to long-term memory: [{entity}] {attribute} = {value}"


def tool_recall_facts(entity: str = "") -> str:
    """Recall structured facts stored in disk-backed memory about the user or system."""
    facts = memory.recall_facts(entity if entity else None)
    if not facts:
        return f"No memories found for '{entity}'." if entity else "No facts currently stored in memory."
    return "\n".join([f"- [{f['entity']}] {f['attribute']}: {f['value']}" for f in facts])


def tool_inspect_directory(path: str = ".") -> str:
    """Inspect and list files in a directory on this PC."""
    return inspect_directory(path)


def tool_read_file(file_path: str) -> str:
    """Read snippet of a text or code file safely from disk."""
    return read_text_file(file_path)


def tool_write_file(file_path: str, content: str) -> str:
    """Create or overwrite a file on disk with code, scripts, notes, or configuration."""
    return write_text_file(file_path, content)


def tool_execute_command(command: str) -> str:
    """Execute a system shell command (PowerShell / Windows CMD) to check status, run CLI tools, or manage system files."""
    return execute_system_command(command)


def tool_lock_computer(*args, **kwargs) -> str:
    """Lock the computer screen immediately."""
    return lock_workstation()


def tool_get_system_vitals(*args, **kwargs) -> str:
    """Check the real-time hardware status: RAM usage, CPU load, and battery power."""
    return format_vitals_summary()


def tool_read_clipboard(*args, **kwargs) -> str:
    """Read the current contents of the Windows clipboard — useful to get text the user just copied."""
    return read_clipboard()


def tool_write_clipboard(text: str = "", *args, **kwargs) -> str:
    """Write text to the Windows clipboard so the user can paste it anywhere."""
    return write_clipboard(text)


def tool_list_processes(filter_name: str = "", *args, **kwargs) -> str:
    """List running processes on this computer. Optionally filter by name (e.g. 'chrome', 'python')."""
    return list_running_processes(filter_name)


def tool_system_info(*args, **kwargs) -> str:
    """Get comprehensive system information: OS version, CPU specs, RAM usage, battery, and uptime."""
    return get_system_info()


def tool_search_file_content(directory: str, pattern: str) -> str:
    """Search files inside a directory for lines matching a text pattern — like grep. Returns file paths and matching lines."""
    return search_files_by_content(directory, pattern)


def tool_find_files(directory: str, name_pattern: str) -> str:
    """Find files by name pattern in a directory tree (e.g. '*.py', 'config*.json')."""
    return find_files(directory, name_pattern)


def tool_recent_files(directory: str = "~", days: int = 3) -> str:
    """List recently modified files in a directory over the last N days."""
    return get_recent_files(directory, days)


def tool_diff_files(file_a: str, file_b: str) -> str:
    """Show the differences (unified diff) between two text files."""
    return diff_files(file_a, file_b)


def tool_active_window(*args, **kwargs) -> str:
    """Get the title of the currently focused application window."""
    return get_active_window_title()


def tool_network_status(*args, **kwargs) -> str:
    """Check network interfaces and internet connectivity status."""
    return get_network_status()


def tool_read_file_window(file_path: str, start_line: int = 1, window_size: int = 80) -> str:
    """Read a specific line window of a file with line numbers (1-indexed). Essential for code reading without blowing context."""
    return ACIFileEditor.read_window(file_path, start_line, window_size)


def tool_replace_file_lines(file_path: str, start_line: int, end_line: int, new_content: str) -> str:
    """Surgically replace lines start_line to end_line (inclusive) in a file with new content."""
    return ACIFileEditor.replace_lines(file_path, start_line, end_line, new_content)


def tool_patch_file_block(file_path: str, search_block: str, replace_block: str) -> str:
    """Surgically replace an exact code block in a file without rewriting the entire file."""
    return ACIFileEditor.patch_block(file_path, search_block, replace_block)


def tool_plan_and_execute_task(task: str) -> str:
    """
    Decompose a complex multi-step objective into a ReWOO dependency blueprint,
    execute all steps autonomously, and synthesize the result.
    """
    active_m = engine.resolve_active_model() if 'engine' in globals() else config.local_model
    planner = ReWOOPlanner(model=active_m, tools=TOOL_DISPATCHER, keep_alive=config.keep_alive)
    return planner.execute(task)


def tool_learn_heuristic_rule(rule: str, domain: str = "general") -> str:
    """Store an operational rule, self-improvement lesson, or behavioral correction into procedural memory."""
    rule_id = memory.add_heuristic_rule(rule, domain)
    return f"Learned procedural heuristic #{rule_id}: {rule}"


def tool_deliberate_problem(problem: str) -> str:
    """Execute System 2 multi-perspective deliberation (Architect vs. Critic vs. Synthesizer) on a complex problem."""
    d_res = thinking_cortex.deliberate(problem)
    return f"{d_res.full_trace}\n\n### 🎯 Synthesized Execution Blueprint\n{d_res.synthesizer_plan}"


def tool_assimilate_skill(skill_name: str) -> str:
    """Permanently assimilate an Antigravity skill from the 2,400+ vault into long-term heuristic memory."""
    res = cognitive_learner.assimilate_skill(skill_name)
    return res.get("summary", res.get("error", "Assimilation failed."))


def tool_consolidate_memory() -> str:
    """Consolidate episodic dialogue into structured facts and high-order insights."""
    res = cognitive_learner.consolidate_episodes()
    return f"✓ Memory consolidated: {res.get('facts_added', 0)} facts, {res.get('insights_consolidated', 0)} insights."


def tool_view_learned_invariants() -> str:
    """List all active Reflexion error invariants learned from past mistakes."""
    invs = cognitive_learner.get_learned_invariants(limit=10)
    if not invs:
        return "No Reflexion error invariants recorded yet."
    return "### 🛡️ Active Learned Invariants (Reflexion Memory):\n" + "\n".join([f"- {inv}" for inv in invs])


def tool_trigger_self_play(domain: str = "coding") -> str:
    """Trigger autonomous self-play synthetic problem generation and finetune dataset curation."""
    res = cognitive_learner.run_self_play(domain)
    if res.get("success"):
        return f"✓ Self-Play completed in '{domain}'!\n**Problem:** {res['problem']}\n**Dataset total:** {res['total_dataset_samples']} pairs."
    return f"Self-play failed: {res.get('error')}"


def tool_run_adversarial_tournament(discipline: str = "distributed_systems") -> str:
    """Run a 4-role Adversarial Self-Play Tournament (Synthesizer -> Solver -> Red-Teamer -> Judge) in a frontier discipline."""
    res = curriculum_learner.run_adversarial_tournament(discipline)
    return (
        f"### ⚔️ Adversarial Tournament Completed: {discipline.upper()}\n"
        f"**Problem:** {res.problem}\n\n"
        f"**Judge Verdict:**\n{res.judge_verdict}\n\n"
        f"**Invariants Extracted:** {len(res.invariants_extracted)} rules committed."
    )


def tool_synthesize_cross_skills(skill_a: str, skill_b: str) -> str:
    """Synthesize two disparate skills from the 2,076 vault into a unified hybrid engineering invariant."""
    res = curriculum_learner.synthesize_cross_domain_skills(skill_a, skill_b)
    return f"✓ Cross-skill rule #{res['rule_id']} synthesized: {res['synthesized_rule']}"


def tool_create_engagement_dag(objective: str) -> str:
    """Initialize a hierarchical Task DAG for proactive multi-step objective engagement with persistent checkpointing."""
    return task_engagement.create_engagement_dag(objective)


def tool_advance_engagement_task(task_id: str = "", result_summary: str = "") -> str:
    """Mark a task in the active engagement DAG completed and unblock dependent tasks."""
    if not task_id:
        current_task = task_engagement.get_current_actionable_task()
        task_id = current_task.id if current_task else "T1"
    res = task_engagement.advance_task(task_id, result_summary=result_summary)
    return f"{res}\n\n{task_engagement.format_dag_markdown()}"


def tool_get_active_engagement_status() -> str:
    """Get the active multi-turn engagement DAG status, completed milestones, and immediate focus."""
    return task_engagement.format_dag_markdown()


def tool_set_engagement_persona(persona_name: str) -> str:
    """Switch cognitive engagement posture (ARCHITECT, BUILDER, SECURITY_AUDITOR, PERFORMANCE_PROFILER, UI_ARTISAN)."""
    p_clean = persona_name.strip().upper()
    if p_clean in EngagementPersona._value2member_map_:
        return task_engagement.set_persona(EngagementPersona(p_clean))
    return f"Invalid persona. Choose from: {', '.join(list(EngagementPersona._value2member_map_.keys()))}"


def tool_dispatch_swarm_mission(task: str) -> str:
    """Dispatch a full autonomous multi-agent swarm mission (Planner -> Architect -> Coder -> Reviewer -> Synthesizer) on a complex objective."""
    res = swarm_engine.run_sequential_pipeline(task)
    return (
        f"### 🐝 Swarm Mission Completed: {res.get('mission_id')}\n\n"
        f"**Pipeline:** {' ➔ '.join(res.get('pipeline', []))}\n\n"
        f"**Executive Synthesis:**\n{res.get('summary', '')}"
    )


def tool_run_swarm_debate(topic: str, rounds: int = 2) -> str:
    """Execute dialectic consensus debate between Architect, Security Auditor, and Reviewer on a technical topic."""
    res = swarm_engine.run_dialectic_debate(topic, rounds=rounds)
    return (
        f"### ⚔️ Swarm Dialectic Debate Completed\n\n"
        f"**Topic:** {res.get('topic')}\n\n"
        f"**Consensus Verdict:**\n{res.get('verdict')}"
    )


def tool_analyze_code_ast(code: str) -> str:
    """Perform static AST syntax inspection, cyclomatic complexity analysis, and security invariant verification on Python code."""
    import json
    res = ast_guard.analyze_python_code(code)
    return json.dumps(res.to_dict(), indent=2)


def tool_dispatch_kaggle_gpu_training(kernel_slug: str = "aether-frontier-gpu-training") -> str:
    """Dispatch autonomous GPU fine-tuning of AETHER on Kaggle cloud (30+ hrs free GPU quota)."""
    from pathlib import Path
    kernel_script = Path(__file__).resolve().parent.parent.parent / "scripts" / "kaggle_autonomous_training_kernel.py"
    code = kernel_script.read_text(encoding="utf-8") if kernel_script.exists() else None
    res = kaggle_controller.push_training_kernel(kernel_slug=kernel_slug, kernel_code=code)
    if res.get("success"):
        return f"### 🚀 Kaggle GPU Training Dispatched Successfully!\n**Kernel:** {res.get('kernel_slug')}\n**URL:** {res.get('url')}\n\nTraining is actively executing on remote Tesla T4/P100 GPU."
    return f"Failed to dispatch Kaggle training: {res.get('error')}"


def tool_check_kaggle_training_status(kernel_slug: str = "aether-frontier-gpu-training") -> str:
    """Check the real-time execution status of a Kaggle GPU fine-tuning kernel."""
    res = kaggle_controller.get_kernel_status(kernel_slug=kernel_slug)
    if res.get("success"):
        return f"**Kaggle Kernel Status:** `{res.get('status')}` (Target: `{res.get('kernel_slug')}`)"
    return f"Status check failed: {res.get('error')}"


def tool_download_and_mount_kaggle_model() -> str:
    """Download converted GGUF model from Kaggle run and mount directly into local Ollama."""
    d_res = kaggle_controller.download_kernel_outputs()
    if not d_res.get("success"):
        return f"Download failed: {d_res.get('error')}"
    m_res = kaggle_controller.mount_downloaded_model_to_ollama()
    if m_res.get("success"):
        return f"### ✓ AETHER v3 Fine-Tuned Model Mounted Successfully!\n**Model:** `{m_res.get('model_name')}`\nActivated as primary local brain."
    return f"Downloaded {len(d_res.get('downloaded_files', []))} files, but mount failed: {m_res.get('error')}"


# ── Hybrid Edge-Cloud Desktop Agent & UI Actuation ─────────────────────────
def tool_launch_or_focus_app(app_name: str, args: str = "") -> str:
    """Launch or focus a Windows desktop application (e.g. 'chrome', 'vscode', 'spotify', 'terminal', 'powershell', 'explorer', 'notepad')."""
    res = dc_launch_app(app_name=app_name, args=args if args.strip() else None)
    return res.get("details", res.get("message", str(res)))


def tool_manage_windows_service(service_name: str, action: str = "status") -> str:
    """Query, start, stop, or restart a Windows system background service (e.g. 'wuauserv', 'LanmanWorkstation', 'Spooler'). Actions: status, start, stop, restart."""
    res = dc_manage_service(service_name=service_name, action=action)
    return f"Service [{service_name}] Status: {res.get('status')}\nOutput: {res.get('output', '')}"


def tool_interact_ui(action: str, x: int = 0, y: int = 0, text: str = "", key_combo: str = "") -> str:
    """Actuate hardware UI controls: mouse click, mouse double-click, keyboard typing, hotkeys, or scrolling. Actions: 'click', 'double_click', 'right_click', 'type', 'hotkey', 'scroll'."""
    res = dc_interact_ui(action=action, x=x, y=y, text=text, key_combo=key_combo)
    return f"UI Interaction [{action}]: {res.get('status')}"


def tool_see_screen_and_analyze(prompt: str = "Identify active windows, main open applications, and prominent text.") -> str:
    """Capture the high-res Windows display, inspect active applications, and perform multimodal visual reasoning."""
    res = dc_see_screen(prompt=prompt)
    return (
        f"### 🖥️ Desktop Display Analysis\n"
        f"- Resolution: {res.get('resolution')}\n"
        f"- Active Applications: {', '.join(res.get('active_applications', []))}\n"
        f"- Capture Path: {res.get('image_path')}\n\n"
        f"**Visual Summary:**\n{res.get('visual_summary')}"
    )


def tool_execute_hybrid_desktop_task(objective: str) -> str:
    """Execute an autonomous end-to-end desktop automation mission using hybrid edge-cloud orchestration (seeing screen, launching apps, interacting with UI, and visual verification)."""
    res = hybrid_desktop_agent.execute_autonomous_desktop_mission(objective)
    steps_md = "\n".join([f"- Step {s['step_id']} [{s['action']}]: {s['status']} ({s['output']})" for s in res.get("executed_steps", [])])
    return (
        f"### 🤖 Hybrid Desktop Mission Completed\n"
        f"**Objective:** {res.get('goal')}\n"
        f"**Status:** {res.get('status')}\n"
        f"**Executed Steps ({res.get('total_steps')} total):**\n{steps_md}"
    )


# ── Entrepreneur & Engineering Companion ───────────────────────────────────
def tool_model_venture_unit_economics(cac: float, arpu: float, gross_margin_pct: float, churn_rate_monthly: float, monthly_burn: float, cash_balance: float) -> str:
    """Model venture SaaS/AI unit economics, LTV/CAC ratio, payback periods, and runway in months."""
    res = ep_model_economics(cac=cac, arpu=arpu, gross_margin_pct=gross_margin_pct, churn_rate_monthly=churn_rate_monthly, monthly_burn=monthly_burn, cash_balance=cash_balance)
    return (
        f"### 📊 Venture Unit Economics Analysis\n"
        f"- Health Rating: **{res.get('health_assessment')}**\n"
        f"- LTV: ${res.get('ltv', 0):,.2f} | CAC: ${res.get('cac', 0):,.2f}\n"
        f"- LTV/CAC Ratio: {res.get('ltv_cac_ratio', 0):.2f}x\n"
        f"- CAC Payback Period: {res.get('cac_payback_months', 0):.1f} months\n"
        f"- Projected Runway: {res.get('runway_months', 0):.1f} months\n\n"
        f"**Strategic Insights:**\n" + "\n".join([f"- {i}" for i in res.get("insights", [])])
    )


def tool_simulate_cap_table_and_dilution(pre_money_valuation: float, investment_amount: float, option_pool_pct: float = 10.0, current_shares: int = 10000000) -> str:
    """Simulate equity dilution, post-money valuation, investor ownership, and option pool expansion for a venture round."""
    res = ep_simulate_cap_table(pre_money_valuation=pre_money_valuation, investment_amount=investment_amount, option_pool_pct=option_pool_pct, current_shares=current_shares)
    return (
        f"### 📈 Cap Table Dilution Simulation\n"
        f"- Pre-Money Valuation: ${res.get('pre_money_valuation', 0):,.2f}\n"
        f"- Post-Money Valuation: ${res.get('post_money_valuation', 0):,.2f}\n"
        f"- Investor Ownership: {res.get('investor_ownership_pct', 0):.2f}%\n"
        f"- Founder Retention: {res.get('founder_ownership_post_pct', 0):.2f}%\n"
        f"- Share Price: ${res.get('share_price', 0):.4f}\n"
        f"- Total Post-Round Shares: {res.get('post_round_total_shares', 0):,}"
    )


def tool_synthesize_technical_prd(product_name: str, core_problem: str, target_audience: str, key_features_csv: str, architecture_stack: str = "FastAPI + React + Ollama") -> str:
    """Generate a production-grade Technical PRD (Product Requirements Document) with architecture, data models, API contracts, and phased milestones."""
    features = [f.strip() for f in key_features_csv.split(",") if f.strip()]
    return ep_synthesize_prd(product_name=product_name, core_problem=core_problem, target_audience=target_audience, key_features=features, architecture_stack=architecture_stack)


def tool_synthesize_investor_memo_and_pitch(company_name: str, one_liner: str, market_tam: str, traction: str, ask_amount: str) -> str:
    """Synthesize an institutional Silicon Valley-grade Investor Memo and 10-slide Pitch Deck narrative."""
    return ep_synthesize_memo(company_name=company_name, one_liner=one_liner, market_tam=market_tam, traction=traction, ask_amount=ask_amount)


def tool_orchestrate_executive_sprint(current_blockers: str, top_goals: str, hours_available: float = 8.0) -> str:
    """Orchestrate an intensive founder/engineering executive sprint using Eisenhower matrix categorization and timeboxing."""
    blockers = [b.strip() for b in current_blockers.split(",") if b.strip()]
    goals = [g.strip() for g in top_goals.split(",") if g.strip()]
    res = ep_orchestrate_sprint(current_blockers=blockers, top_goals=goals, hours_available=hours_available)
    blocks_md = "\n".join([f"- **Block {b['block']}** ({b['duration_hours']}h | `{b['type']}`): {b['focus']}" for b in res.get("schedule", [])])
    return (
        f"### ⚡ Executive Engineering Sprint\n"
        f"- Sprint Window: {res.get('hours_allocated')} Hours | Planned Blocks: {res.get('total_sprint_blocks')}\n\n"
        f"**Blocker Resolutions:**\n" + "\n".join([f"- {r}" for r in res.get("resolved_blockers", [])]) + "\n\n"
        f"**Execution Schedule:**\n{blocks_md}"
    )


AVAILABLE_TOOLS = [
    tool_play_youtube_media,
    tool_open_application,
    tool_open_browser_url,
    tool_lock_computer,
    tool_take_screenshot,
    tool_search_web,
    tool_deep_web_research,
    tool_browse_web_page,
    tool_search_wikipedia,
    tool_search_arxiv,
    tool_remember_fact,
    tool_recall_facts,
    tool_inspect_directory,
    tool_read_file,
    tool_write_file,
    tool_execute_command,
    tool_get_system_vitals,
    tool_analyze_screen,
    tool_analyze_image,
    tool_execute_python_code,
    # Deep System Intelligence
    tool_read_clipboard,
    tool_write_clipboard,
    tool_list_processes,
    tool_system_info,
    tool_search_file_content,
    tool_find_files,
    tool_recent_files,
    tool_diff_files,
    tool_active_window,
    tool_network_status,
    # ACI File Mastery & ReWOO Autonomy
    tool_read_file_window,
    tool_replace_file_lines,
    tool_patch_file_block,
    tool_plan_and_execute_task,
    tool_learn_heuristic_rule,
    # Snapdragon Hardware Acceleration & Copilot Controls
    tool_instant_screen_ocr,
    tool_control_volume,
    tool_set_brightness,
    tool_translate_text,
    tool_show_world_map,
    # Continuous Recurrent Evolution
    tool_trigger_evolution,
    # FreeLLMAPI & Online Agent Cortex
    tool_query_online_cortex,
    tool_dispatch_online_agent_swarm,
    tool_freellmapi_status,
    # Autonomous Auto-Learning Cortex
    tool_inspect_auto_learning_metrics,
    tool_auto_learn_from_context,
    # Universal Antigravity Skill Vault
    tool_search_skills,
    tool_load_skill,
    tool_list_skills,
    tool_skills_vault_status,
    # Claude Code Agentic Tools
    tool_claude_bash,
    tool_claude_view,
    tool_claude_edit,
    tool_claude_write,
    tool_claude_grep,
    tool_claude_find,
    tool_claude_todo,
    tool_claude_subagent,
    # Cognitive Deliberation & Neuroplastic Learning
    tool_deliberate_problem,
    tool_assimilate_skill,
    tool_consolidate_memory,
    tool_view_learned_invariants,
    tool_trigger_self_play,
    # Diversified Curriculum & Task Engagement
    tool_run_adversarial_tournament,
    tool_synthesize_cross_skills,
    tool_create_engagement_dag,
    tool_advance_engagement_task,
    tool_get_active_engagement_status,
    tool_set_engagement_persona,
    # Cyber-Guardian & Threat Reconnaissance
    tool_audit_active_connections,
    tool_scan_network_ports,
    tool_inspect_ssl_cert,
    tool_hunt_exposed_secrets,
    # Daily Intel Gathering & Frontier OSINT Radar
    tool_fetch_daily_threat_intel,
    tool_fetch_tech_frontier_radar,
    tool_profile_domain_osint,
    tool_generate_morning_briefing,
    # Global Master Tech & Systems Architecture
    tool_benchmark_api_endpoint,
    tool_audit_codebase_architecture,
    tool_profile_process_telemetry,
    tool_inspect_git_repositories,
    # Dynamic Tool Genesis (Option A)
    tool_synthesize_new_tool,
    tool_list_generated_tools,
    tool_delete_generated_tool,
    # Autonomous Reflexion Loop (Option B)
    tool_reflect_on_error,
    tool_audit_error_invariants,
    # Autonomous Multi-Agent Swarm & AST Code Intelligence
    tool_dispatch_swarm_mission,
    tool_run_swarm_debate,
    tool_analyze_code_ast,
    # Autonomous Kaggle Cloud GPU Fine-Tuning
    tool_dispatch_kaggle_gpu_training,
    tool_check_kaggle_training_status,
    tool_download_and_mount_kaggle_model,
    # Sovereign Desktop Vision & Application Actuation
    tool_launch_or_focus_app,
    tool_manage_windows_service,
    tool_interact_ui,
    tool_see_screen_and_analyze,
    tool_execute_hybrid_desktop_task,
    # Entrepreneur & Engineering Executive Companion
    tool_model_venture_unit_economics,
    tool_simulate_cap_table_and_dilution,
    tool_synthesize_technical_prd,
    tool_synthesize_investor_memo_and_pitch,
    tool_orchestrate_executive_sprint,
    # Sovereign Online Gateway & Free Remote Access
    tool_query_free_online_ai,
    tool_start_online_tunnel,
    tool_get_online_tunnel_status,
    tool_stop_online_tunnel,
    tool_list_free_online_models,
    # Cloud Consciousness Vault
    tool_export_cloud_consciousness,
    # Neural Voice Studio & Speech Personas
    tool_set_voice_persona,
    tool_list_available_voices,
    tool_speak_phrase,
    # Hardware & Speculative NPU Acceleration
    tool_inspect_hardware_acceleration,
    tool_benchmark_speculative_decoding,
    # Visual Set-of-Mark (SoM) Computer-Use
    tool_capture_screen_with_som,
    tool_execute_som_action,
    # Autonomous Cloud Self-Play & Model Evolution
    tool_run_self_play_curriculum_step,
    tool_dispatch_autonomous_cloud_evolution,
    tool_get_model_evolution_status,
    # Hybrid Dense RAG & Semantic Knowledge Graph
    tool_query_hybrid_memory,
    tool_query_semantic_knowledge_graph,
    tool_extract_knowledge_triples,
    # Sovereign Multi-Channel Gateway (Telegram/Discord & Briefings)
    tool_get_multi_channel_gateway_status,
    tool_generate_morning_audio_briefing,
    # Zero-CPU Offline Wake-Word Engine
    tool_start_wake_word_listener,
    tool_get_wake_word_status,
    # LEON Autonomous Venture OS & Sub-Agent Swarm
    tool_leon_create_venture,
    tool_leon_dispatch_subagent_swarm,
    tool_train_leon_venture_model,
    tool_leon_get_venture_ledger,
    # LEON Marketing, UI Assignment, Lead Prospecting, Cold Outreach & SEO
    tool_leon_assign_ui_archetype,
    tool_leon_search_and_qualify_leads,
    tool_leon_draft_personalized_outreach,
    tool_leon_generate_seo_and_web_spec,
    # LEON 1-Click Live Web Deployer, Razorpay & Stripe Payment Gateways
    tool_leon_deploy_venture_to_cloud,
    tool_leon_create_stripe_payment_link,
    tool_leon_create_razorpay_checkout,
    tool_leon_get_deployed_ventures,
    # LEON Business Portfolio & Low-Cost Subscription Revision Engine
    tool_leon_launch_all_low_cost_businesses,
    tool_leon_get_portfolio_status,
    tool_leon_revise_business_pricing,
    tool_leon_auto_scale_portfolio_pricing,
    # LEON Business Intelligence: Ideation, Brand, Leads
    tool_leon_generate_business_ideas,
    tool_leon_business_blueprint,
    tool_leon_customize_brand,
    tool_leon_find_leads,
]

# ── AGI planner tool wrappers (registered after TOOL_DISPATCHER is built) ───

def tool_agi_run_plan(goal: str, steps_json: str) -> str:
    """
    Execute a deterministic multi-step plan through the AGI Planner.

    Args:
        goal:       Human-readable goal description.
        steps_json: JSON array of step dicts, each with 'name', 'tool', 'args'.
                    The 'tool' must be a key in TOOL_DISPATCHER.

    Returns:
        JSON summary of the completed plan (id, status, per-step results).
    """
    import json as _json
    steps = _json.loads(steps_json)
    # Wire the planner with the current dispatcher so it can call any tool
    agi_planner.register_tools(TOOL_DISPATCHER)
    plan = agi_planner.run_goal(goal=goal, steps=steps)
    return _json.dumps({
        "plan_id": plan.id,
        "status": plan.status.value,
        "steps": [
            {"name": s.name, "status": s.status.value,
             "result": str(s.result)[:200] if s.result else None,
             "error": s.error}
            for s in plan.steps
        ],
    }, indent=2)


def tool_agi_list_plans() -> str:
    """Return a JSON summary of all plans executed this session."""
    import json as _json
    return _json.dumps(agi_planner.list_plans(), indent=2)


def tool_agi_asset_registry_summary() -> str:
    """Return the current asset registry summary (total count + by-type breakdown)."""
    import json as _json
    return _json.dumps(asset_registry.summary(), indent=2)


def tool_agi_force_self_evaluation() -> str:
    """
    Manually trigger the nightly self-evaluation job immediately.
    Useful for debugging asset health without waiting for 00:15 UTC.
    """
    import json as _json
    try:
        from aether.daemon.autonomous_operator import autonomous_operator
        autonomous_operator.job_self_evaluation()
        return _json.dumps({"status": "self_evaluation_triggered"})
    except Exception as e:
        return _json.dumps({"status": "error", "detail": str(e)})


def tool_agency_dispatch_specialist(agent_slug_or_name: str, task: str, context: str = "") -> str:
    """
    Dispatch a specialized agency agent (from 267+ agency specialists) with its full
    custom playbook, methodology, and persona to execute a domain-specific task.
    """
    import json as _json

    from aether.brain.agency_specialists_engine import agency_engine
    res = agency_engine.dispatch_specialist(agent_slug_or_name, task, context=context)
    return _json.dumps(res, indent=2)


def tool_agency_recommend_specialists(goal: str) -> str:
    """Recommend the top-fit specialized agency agents for a specific project, venture, or technical goal."""
    import json as _json

    from aether.brain.agency_specialists_engine import agency_engine
    recs = agency_engine.recommend_specialists(goal, top_k=5)
    return _json.dumps(recs, indent=2)


def tool_agency_list_divisions() -> str:
    """List all 18 operational divisions in the Agency Agents roster with specialist counts."""
    import json as _json

    from aether.brain.agency_specialists_engine import agency_engine
    return _json.dumps(agency_engine.list_divisions(), indent=2)


def tool_agency_sync_training_and_memory() -> str:
    """Ingest agency procedural rules into SQLite FTS5 conscious memory and regenerate training dataset."""
    import json as _json

    from aether.brain.agency_training_synthesizer import \
        agency_training_synthesizer
    rules = agency_training_synthesizer.extract_heuristics_and_rules(max_agents=100)
    dataset_res = agency_training_synthesizer.synthesize_finetuning_dataset()
    return _json.dumps({
        "status": "synchronized",
        "rules_injected_to_memory": rules,
        "dataset_samples": dataset_res["samples_count"],
        "dataset_path": dataset_res["dataset_path"],
    }, indent=2)


TOOL_DISPATCHER: Dict[str, Callable] = {fn.__name__: fn for fn in AVAILABLE_TOOLS}
# Merge all 200 sovereign skills from Skills Galaxy (Windows OS, Hardware, Apps, Forensics, Cognitive, Math, Training)
TOOL_DISPATCHER.update(SKILLS_GALAXY_REGISTRY)

# Cold-boot mount all dynamically generated tools from disk
tool_genesis.load_all_generated_tools()

# ── Register AGI planner tools (defined after TOOL_DISPATCHER was built) ─────
TOOL_DISPATCHER["tool_agi_run_plan"]               = tool_agi_run_plan
TOOL_DISPATCHER["tool_agi_list_plans"]             = tool_agi_list_plans
TOOL_DISPATCHER["tool_agi_asset_registry_summary"] = tool_agi_asset_registry_summary
TOOL_DISPATCHER["tool_agi_force_self_evaluation"]  = tool_agi_force_self_evaluation

# ── Register Agency Specialists tools ────────────────────────────────────────
TOOL_DISPATCHER["tool_agency_dispatch_specialist"]        = tool_agency_dispatch_specialist
TOOL_DISPATCHER["tool_agency_recommend_specialists"]      = tool_agency_recommend_specialists
TOOL_DISPATCHER["tool_agency_list_divisions"]             = tool_agency_list_divisions
TOOL_DISPATCHER["tool_agency_sync_training_and_memory"]   = tool_agency_sync_training_and_memory

ACTION_KEYWORDS = {
    # Sovereign Desktop Vision & Hybrid Application Automation
    "desktop": ["tool_see_screen_and_analyze", "tool_execute_hybrid_desktop_task", "tool_launch_or_focus_app"],
    "screen": ["tool_see_screen_and_analyze", "tool_take_screenshot"],
    "display": ["tool_see_screen_and_analyze"],
    "look": ["tool_see_screen_and_analyze"],
    "app": ["tool_launch_or_focus_app", "tool_open_application"],
    "apps": ["tool_launch_or_focus_app", "tool_open_application"],
    "launch": ["tool_launch_or_focus_app", "tool_open_application"],
    "service": ["tool_manage_windows_service"],
    "services": ["tool_manage_windows_service"],
    "click": ["tool_interact_ui"],
    "type": ["tool_interact_ui"],
    "hotkey": ["tool_interact_ui"],
    "automate": ["tool_execute_hybrid_desktop_task"],
    "automation": ["tool_execute_hybrid_desktop_task"],
    "mission": ["tool_execute_hybrid_desktop_task", "tool_dispatch_swarm_mission"],

    # Entrepreneur & Engineering Executive Companion
    "economics": ["tool_model_venture_unit_economics"],
    "unit_economics": ["tool_model_venture_unit_economics"],
    "runway": ["tool_model_venture_unit_economics"],
    "cac": ["tool_model_venture_unit_economics"],
    "ltv": ["tool_model_venture_unit_economics"],
    "captable": ["tool_simulate_cap_table_and_dilution"],
    "dilution": ["tool_simulate_cap_table_and_dilution"],
    "equity": ["tool_simulate_cap_table_and_dilution"],
    "valuation": ["tool_simulate_cap_table_and_dilution"],
    "prd": ["tool_synthesize_technical_prd"],
    "requirements": ["tool_synthesize_technical_prd"],
    "pitch": ["tool_synthesize_investor_memo_and_pitch"],
    "pitchdeck": ["tool_synthesize_investor_memo_and_pitch"],
    "investor": ["tool_synthesize_investor_memo_and_pitch"],
    "memo": ["tool_synthesize_investor_memo_and_pitch"],
    "sprint": ["tool_orchestrate_executive_sprint"],
    "blockers": ["tool_orchestrate_executive_sprint"],

    # Kaggle Cloud GPU Fine-Tuning
    "kaggle": ["tool_dispatch_kaggle_gpu_training", "tool_check_kaggle_training_status", "tool_download_and_mount_kaggle_model"],
    "finetune": ["tool_dispatch_kaggle_gpu_training", "tool_check_kaggle_training_status"],
    "train": ["tool_dispatch_kaggle_gpu_training"],
    "gpu": ["tool_dispatch_kaggle_gpu_training"],

    # Multi-Agent Swarm & AST Intelligence
    "swarm": ["tool_dispatch_swarm_mission", "tool_run_swarm_debate"],
    "multiagent": ["tool_dispatch_swarm_mission", "tool_run_swarm_debate"],
    "teamwork": ["tool_dispatch_swarm_mission"],
    "debate": ["tool_run_swarm_debate"],
    "consensus": ["tool_run_swarm_debate"],
    "ast": ["tool_analyze_code_ast"],
    "complexity": ["tool_analyze_code_ast"],

    # Dynamic Tool Genesis & Autonomous Reflexion
    "genesis": ["tool_synthesize_new_tool", "tool_list_generated_tools"],
    "newtool": ["tool_synthesize_new_tool"],
    "synthesize": ["tool_synthesize_new_tool"],
    "createskill": ["tool_synthesize_new_tool"],
    "customtool": ["tool_synthesize_new_tool", "tool_list_generated_tools"],
    "reflexion": ["tool_reflect_on_error", "tool_audit_error_invariants"],
    "reflect": ["tool_reflect_on_error"],
    "selfheal": ["tool_reflect_on_error"],
    "healinvariant": ["tool_audit_error_invariants"],

    # Global Master Tech & Systems Architecture
    "benchmark": ["tool_benchmark_api_endpoint"],
    "stress": ["tool_benchmark_api_endpoint"],
    "latency": ["tool_benchmark_api_endpoint"],
    "throughput": ["tool_benchmark_api_endpoint"],
    "architecture": ["tool_audit_codebase_architecture"],
    "cleancode": ["tool_audit_codebase_architecture"],
    "debt": ["tool_audit_codebase_architecture"],
    "refactor": ["tool_audit_codebase_architecture"],
    "profile": ["tool_profile_process_telemetry"],
    "telemetry": ["tool_profile_process_telemetry"],
    "leak": ["tool_profile_process_telemetry", "tool_hunt_exposed_secrets"],
    "memoryleak": ["tool_profile_process_telemetry"],
    "handles": ["tool_profile_process_telemetry"],
    "git": ["tool_inspect_git_repositories"],
    "repos": ["tool_inspect_git_repositories"],
    "repository": ["tool_inspect_git_repositories", "tool_audit_codebase_architecture"],
    "repositories": ["tool_inspect_git_repositories"],

    # Daily Intel Gathering & Frontier OSINT Radar
    "intel": ["tool_fetch_daily_threat_intel", "tool_fetch_tech_frontier_radar", "tool_generate_morning_briefing"],
    "briefing": ["tool_generate_morning_briefing", "tool_fetch_daily_threat_intel"],
    "morning": ["tool_generate_morning_briefing"],
    "cve": ["tool_fetch_daily_threat_intel"],
    "threat": ["tool_fetch_daily_threat_intel"],
    "threats": ["tool_fetch_daily_threat_intel"],
    "vulnerabilities": ["tool_fetch_daily_threat_intel", "tool_hunt_exposed_secrets"],
    "osint": ["tool_profile_domain_osint", "tool_inspect_ssl_cert"],
    "dns": ["tool_profile_domain_osint"],
    "domain": ["tool_profile_domain_osint", "tool_inspect_ssl_cert"],
    "radar": ["tool_fetch_tech_frontier_radar"],
    "news": ["tool_fetch_tech_frontier_radar", "tool_search_web"],

    # Cyber-Guardian & Threat Reconnaissance
    "cyber": ["tool_audit_active_connections", "tool_scan_network_ports", "tool_hunt_exposed_secrets"],
    "cybersecurity": ["tool_audit_active_connections", "tool_scan_network_ports", "tool_hunt_exposed_secrets"],
    "security": ["tool_audit_active_connections", "tool_hunt_exposed_secrets", "tool_inspect_ssl_cert"],
    "audit": ["tool_audit_active_connections", "tool_hunt_exposed_secrets"],
    "port": ["tool_scan_network_ports"],
    "ports": ["tool_scan_network_ports"],
    "portscan": ["tool_scan_network_ports"],
    "sockets": ["tool_audit_active_connections"],
    "connections": ["tool_audit_active_connections"],
    "ssl": ["tool_inspect_ssl_cert"],
    "tls": ["tool_inspect_ssl_cert"],
    "certificate": ["tool_inspect_ssl_cert"],
    "cert": ["tool_inspect_ssl_cert"],
    "secret": ["tool_hunt_exposed_secrets"],
    "secrets": ["tool_hunt_exposed_secrets"],
    "leak": ["tool_hunt_exposed_secrets"],
    "vulnerability": ["tool_hunt_exposed_secrets", "tool_audit_active_connections"],

    # Diversified Curriculum & Task Engagement
    "tournament": ["tool_run_adversarial_tournament"],
    "adversarial": ["tool_run_adversarial_tournament"],
    "engage": ["tool_create_engagement_dag", "tool_get_active_engagement_status"],
    "dag": ["tool_create_engagement_dag", "tool_get_active_engagement_status", "tool_advance_engagement_task"],
    "persona": ["tool_set_engagement_persona"],
    "cross-skill": ["tool_synthesize_cross_skills"],

    # Cognitive Deliberation & Neuroplastic Learning
    "deliberate": ["tool_deliberate_problem", "tool_plan_and_execute_task"],
    "deliberation": ["tool_deliberate_problem"],
    "assimilate": ["tool_assimilate_skill", "tool_load_skill"],
    "consolidate": ["tool_consolidate_memory", "tool_remember_fact"],
    "invariant": ["tool_view_learned_invariants", "tool_learn_heuristic_rule"],
    "invariants": ["tool_view_learned_invariants"],
    "selfplay": ["tool_trigger_self_play", "tool_trigger_evolution"],
    "critique": ["tool_deliberate_problem"],

    # Claude Code Agent Operations
    "claude": ["tool_claude_bash", "tool_claude_view", "tool_claude_edit", "tool_claude_write", "tool_claude_todo"],
    "agent": ["tool_claude_subagent", "tool_claude_todo", "tool_claude_bash"],
    "bash": ["tool_claude_bash", "tool_execute_command"],
    "terminal": ["tool_claude_bash", "tool_execute_command"],
    "todo": ["tool_claude_todo"],
    "subagent": ["tool_claude_subagent", "tool_dispatch_online_agent_swarm"],

    # Antigravity Skill Vault
    "skill": ["tool_load_skill", "tool_search_skills", "tool_skills_vault_status"],
    "skills": ["tool_list_skills", "tool_search_skills", "tool_skills_vault_status"],
    "vault": ["tool_skills_vault_status", "tool_list_skills"],

    # Auto-Learning & Continuous Improvement
    "autolearn": ["tool_inspect_auto_learning_metrics", "tool_auto_learn_from_context"],
    "learning": ["tool_inspect_auto_learning_metrics", "tool_auto_learn_from_context"],
    "metrics": ["tool_inspect_auto_learning_metrics", "tool_get_system_vitals"],
    "training": ["tool_inspect_auto_learning_metrics", "tool_trigger_evolution"],

    # Free Online Gateway & Public HTTPS Tunneling & Consciousness Vault
    "tunnel": ["tool_start_online_tunnel", "tool_get_online_tunnel_status", "tool_stop_online_tunnel"],
    "online": ["tool_query_free_online_ai", "tool_start_online_tunnel", "tool_get_online_tunnel_status", "tool_query_online_cortex"],
    "remotegateway": ["tool_start_online_tunnel", "tool_get_online_tunnel_status"],
    "publicurl": ["tool_get_online_tunnel_status", "tool_start_online_tunnel"],
    "freeai": ["tool_query_free_online_ai", "tool_list_free_online_models"],
    "freellmapi": ["tool_freellmapi_status", "tool_query_online_cortex"],
    "swarm": ["tool_dispatch_online_agent_swarm"],
    "cloud": ["tool_query_online_cortex", "tool_export_cloud_consciousness"],
    "snapshot": ["tool_export_cloud_consciousness"],
    "consciousness": ["tool_export_cloud_consciousness"],
    "exportcloud": ["tool_export_cloud_consciousness"],

    # 6 Frontier Systems Keywords
    "speculative": ["tool_benchmark_speculative_decoding", "tool_inspect_hardware_acceleration"],
    "npu": ["tool_inspect_hardware_acceleration", "tool_get_npu_status"],
    "hardware": ["tool_inspect_hardware_acceleration"],
    "kvcache": ["tool_benchmark_speculative_decoding"],
    "som": ["tool_capture_screen_with_som", "tool_execute_som_action"],
    "setofmark": ["tool_capture_screen_with_som", "tool_execute_som_action"],
    "visualgrounding": ["tool_capture_screen_with_som", "tool_execute_som_action"],
    "evolver": ["tool_get_model_evolution_status", "tool_dispatch_autonomous_cloud_evolution"],
    "selfplay_cloud": ["tool_run_self_play_curriculum_step", "tool_dispatch_autonomous_cloud_evolution"],
    "hybridrag": ["tool_query_hybrid_memory"],
    "knowledgegraph": ["tool_query_semantic_knowledge_graph", "tool_extract_knowledge_triples"],
    "triples": ["tool_extract_knowledge_triples", "tool_query_semantic_knowledge_graph"],
    "entity": ["tool_query_semantic_knowledge_graph"],
    "telegram": ["tool_get_multi_channel_gateway_status", "tool_generate_morning_audio_briefing"],
    "discord": ["tool_get_multi_channel_gateway_status"],
    "briefing": ["tool_generate_morning_audio_briefing", "tool_generate_morning_briefing"],
    "wakeword": ["tool_start_wake_word_listener", "tool_get_wake_word_status"],
    "bargein": ["tool_start_wake_word_listener"],

    # LEON Autonomous Venture OS, Growth, Deployment & Razorpay/Stripe
    "leon": ["tool_leon_create_venture", "tool_leon_dispatch_subagent_swarm", "tool_train_leon_venture_model", "tool_leon_get_venture_ledger"],
    "venture": ["tool_leon_create_venture", "tool_leon_dispatch_subagent_swarm", "tool_leon_deploy_venture_to_cloud", "tool_leon_get_venture_ledger"],
    "business": ["tool_leon_create_venture", "tool_leon_dispatch_subagent_swarm", "tool_leon_deploy_venture_to_cloud"],
    "subagents": ["tool_leon_dispatch_subagent_swarm", "tool_dispatch_online_agent_swarm"],
    "train_leon": ["tool_train_leon_venture_model"],
    "marketing": ["tool_leon_assign_ui_archetype", "tool_leon_search_and_qualify_leads", "tool_leon_draft_personalized_outreach", "tool_leon_generate_seo_and_web_spec"],
    "leads": ["tool_leon_search_and_qualify_leads", "tool_leon_draft_personalized_outreach"],
    "outreach": ["tool_leon_draft_personalized_outreach", "tool_leon_search_and_qualify_leads"],
    "seo": ["tool_leon_generate_seo_and_web_spec", "tool_leon_deploy_venture_to_cloud"],
    "deploy": ["tool_leon_deploy_venture_to_cloud", "tool_leon_get_deployed_ventures"],
    "vercel": ["tool_leon_deploy_venture_to_cloud", "tool_leon_get_deployed_ventures"],
    "razorpay": ["tool_leon_create_razorpay_checkout", "tool_leon_deploy_venture_to_cloud"],
    "stripe": ["tool_leon_create_stripe_payment_link", "tool_leon_deploy_venture_to_cloud"],
    "payment": ["tool_leon_create_razorpay_checkout", "tool_leon_create_stripe_payment_link"],
    "checkout": ["tool_leon_create_razorpay_checkout", "tool_leon_create_stripe_payment_link"],
    "portfolio": ["tool_leon_launch_all_low_cost_businesses", "tool_leon_get_portfolio_status"],
    "businesses": ["tool_leon_launch_all_low_cost_businesses", "tool_leon_get_portfolio_status"],
    "subscription": ["tool_leon_launch_all_low_cost_businesses", "tool_leon_revise_business_pricing", "tool_leon_create_razorpay_checkout"],
    "subscriptions": ["tool_leon_launch_all_low_cost_businesses", "tool_leon_revise_business_pricing"],
    "pricing": ["tool_leon_revise_business_pricing", "tool_leon_auto_scale_portfolio_pricing", "tool_leon_get_portfolio_status"],
    "revise": ["tool_leon_revise_business_pricing", "tool_leon_auto_scale_portfolio_pricing"],
    # LEON Business Intelligence
    "idea": ["tool_leon_generate_business_ideas", "tool_leon_business_blueprint"],
    "ideas": ["tool_leon_generate_business_ideas"],
    "ideation": ["tool_leon_generate_business_ideas", "tool_leon_business_blueprint"],
    "blueprint": ["tool_leon_business_blueprint"],
    "brand": ["tool_leon_customize_brand"],
    "branding": ["tool_leon_customize_brand"],
    "theme": ["tool_leon_customize_brand"],
    "colour": ["tool_leon_customize_brand"],
    "color": ["tool_leon_customize_brand"],
    "findleads": ["tool_leon_find_leads"],
    "discover": ["tool_leon_find_leads", "tool_leon_search_and_qualify_leads"],
    # Autonomous Operator dashboard
    "inbox": ["tool_leon_get_portfolio_status", "tool_agi_list_plans"],
    "operator": ["tool_leon_get_portfolio_status", "tool_agi_asset_registry_summary"],
    "schedule": ["tool_leon_get_portfolio_status"],
    "autonomous": ["tool_leon_get_portfolio_status", "tool_leon_launch_all_low_cost_businesses"],
    # AGI Planner & Self-Improvement
    "plan": ["tool_agi_run_plan", "tool_agi_list_plans"],
    "plans": ["tool_agi_list_plans"],
    "execute plan": ["tool_agi_run_plan"],
    "assets": ["tool_agi_asset_registry_summary"],
    "registry": ["tool_agi_asset_registry_summary"],
    "evaluate": ["tool_agi_force_self_evaluation"],
    "self-eval": ["tool_agi_force_self_evaluation"],
    "selfeval": ["tool_agi_force_self_evaluation"],
    "retrain": ["tool_agi_force_self_evaluation"],
    "health": ["tool_agi_asset_registry_summary", "tool_leon_get_portfolio_status"],


    # System Navigation & Media
    "play": ["tool_play_youtube_media", "tool_open_browser_url"],
    "song": ["tool_play_youtube_media"],
    "music": ["tool_play_youtube_media"],
    "youtube": ["tool_play_youtube_media", "tool_open_browser_url"],
    "open": ["tool_open_application", "tool_open_browser_url"],
    "launch": ["tool_open_application"],
    "start": ["tool_open_application"],
    "close": ["tool_execute_command"],
    "lock": ["tool_lock_computer"],
    "screen": ["tool_instant_screen_ocr", "tool_analyze_screen", "tool_take_screenshot"],
    "screenshot": ["tool_take_screenshot"],
    "ocr": ["tool_instant_screen_ocr"],
    "look at": ["tool_instant_screen_ocr", "tool_analyze_screen"],
    "read screen": ["tool_instant_screen_ocr"],
    "volume": ["tool_control_volume"],
    "mute": ["tool_control_volume"],
    "unmute": ["tool_control_volume"],
    "audio": ["tool_control_volume"],
    "voice": ["tool_set_voice_persona", "tool_list_available_voices", "tool_speak_phrase"],
    "voices": ["tool_list_available_voices", "tool_set_voice_persona"],
    "speech": ["tool_set_voice_persona", "tool_speak_phrase"],
    "speak": ["tool_speak_phrase", "tool_set_voice_persona"],
    "tts": ["tool_set_voice_persona", "tool_list_available_voices"],
    "jarvis": ["tool_set_voice_persona", "tool_speak_phrase"],
    "persona_voice": ["tool_set_voice_persona"],
    "brightness": ["tool_set_brightness"],
    "display": ["tool_set_brightness"],
    "translate": ["tool_translate_text"],
    "translation": ["tool_translate_text"],
    "spanish": ["tool_translate_text"],
    "french": ["tool_translate_text"],
    "japanese": ["tool_translate_text"],
    "german": ["tool_translate_text"],
    "map": ["tool_show_world_map"],
    "location": ["tool_show_world_map"],
    "coordinates": ["tool_show_world_map"],
    "evolve": ["tool_trigger_evolution"],
    "evolution": ["tool_trigger_evolution"],
    "train": ["tool_trigger_evolution"],

    # Hardware & System Info
    "npu": ["tool_get_system_vitals", "tool_system_info"],
    "hardware": ["tool_get_system_vitals", "tool_system_info"],
    "system": ["tool_system_info", "tool_get_system_vitals"],
    "vitals": ["tool_get_system_vitals"],
    "battery": ["tool_get_system_vitals"],
    "ram": ["tool_get_system_vitals"],
    "network": ["tool_network_status"],
    "wifi": ["tool_network_status"],
    "internet": ["tool_network_status"],
    "window": ["tool_active_window"],
    "process": ["tool_list_processes"],
    "processes": ["tool_list_processes"],
    "clipboard": ["tool_read_clipboard", "tool_write_clipboard"],
    "copy": ["tool_write_clipboard"],
    "paste": ["tool_read_clipboard"],

    # Web & Research
    "search": ["tool_search_web", "tool_deep_web_research"],
    "google": ["tool_search_web"],
    "web": ["tool_search_web"],
    "browse": ["tool_browse_web_page"],
    "wikipedia": ["tool_search_wikipedia"],
    "arxiv": ["tool_search_arxiv"],

    # Project, Codebase & File Operations
    "project": ["tool_inspect_directory", "tool_find_files", "tool_search_file_content", "tool_read_file", "tool_write_file", "tool_execute_command"],
    "workspace": ["tool_inspect_directory", "tool_find_files", "tool_search_file_content", "tool_read_file", "tool_write_file"],
    "codebase": ["tool_inspect_directory", "tool_find_files", "tool_search_file_content", "tool_read_file", "tool_write_file"],
    "repository": ["tool_inspect_directory", "tool_find_files", "tool_search_file_content", "tool_read_file", "tool_execute_command"],
    "repo": ["tool_inspect_directory", "tool_find_files", "tool_search_file_content", "tool_read_file", "tool_execute_command"],
    "folder": ["tool_inspect_directory", "tool_find_files"],
    "directory": ["tool_inspect_directory", "tool_find_files"],
    "dir": ["tool_inspect_directory", "tool_find_files"],
    "file": ["tool_read_file", "tool_write_file", "tool_find_files"],
    "files": ["tool_find_files", "tool_read_file", "tool_write_file", "tool_recent_files"],
    "document": ["tool_read_file", "tool_write_file"],
    "docs": ["tool_read_file", "tool_find_files"],
    "read": ["tool_read_file", "tool_read_file_window", "tool_inspect_directory"],
    "cat": ["tool_read_file", "tool_read_file_window"],
    "inspect": ["tool_inspect_directory", "tool_read_file", "tool_search_file_content"],
    "examine": ["tool_inspect_directory", "tool_read_file"],
    "view": ["tool_read_file", "tool_inspect_directory"],
    "write": ["tool_write_file", "tool_replace_file_lines"],
    "create": ["tool_write_file", "tool_execute_command"],
    "save": ["tool_write_file"],
    "edit": ["tool_patch_file_block", "tool_replace_file_lines", "tool_read_file", "tool_write_file"],
    "modify": ["tool_patch_file_block", "tool_replace_file_lines", "tool_read_file", "tool_write_file"],
    "update": ["tool_patch_file_block", "tool_read_file", "tool_write_file"],
    "patch": ["tool_patch_file_block", "tool_read_file"],
    "replace": ["tool_patch_file_block", "tool_replace_file_lines"],
    "fix": ["tool_read_file", "tool_patch_file_block", "tool_search_file_content", "tool_execute_command"],
    "bug": ["tool_read_file", "tool_patch_file_block", "tool_search_file_content"],
    "issue": ["tool_read_file", "tool_patch_file_block", "tool_search_file_content"],
    "debug": ["tool_read_file", "tool_search_file_content", "tool_execute_command"],
    "error": ["tool_read_file", "tool_search_file_content", "tool_execute_command"],
    "align": ["tool_read_file", "tool_patch_file_block", "tool_search_file_content"],
    "alignment": ["tool_read_file", "tool_patch_file_block"],
    "css": ["tool_read_file", "tool_patch_file_block", "tool_write_file"],
    "html": ["tool_read_file", "tool_patch_file_block", "tool_write_file"],
    "js": ["tool_read_file", "tool_patch_file_block", "tool_write_file"],
    "code": ["tool_execute_python_code", "tool_read_file", "tool_write_file", "tool_execute_command"],
    "python": ["tool_execute_python_code", "tool_read_file", "tool_write_file"],
    "refactor": ["tool_read_file", "tool_patch_file_block", "tool_write_file"],
    "build": ["tool_execute_command", "tool_read_file"],
    "test": ["tool_execute_command", "tool_read_file"],
    "grep": ["tool_search_file_content", "tool_find_files"],
    "find": ["tool_find_files", "tool_search_file_content"],
    "diff": ["tool_diff_files", "tool_read_file"],
    "needs": ["tool_inspect_directory", "tool_read_file", "tool_find_files"],
    "organize": ["tool_inspect_directory", "tool_find_files"],
    "check": ["tool_inspect_directory", "tool_read_file", "tool_system_info"],
    "run": ["tool_execute_command", "tool_execute_python_code"],
    "terminal": ["tool_execute_command"],
    "powershell": ["tool_execute_command"],
    "cmd": ["tool_execute_command"],
    "calculate": ["tool_execute_python_code"],
    "calc": ["tool_execute_python_code"],

    # Memory, Heuristics & Planning
    "remember": ["tool_remember_fact", "tool_recall_facts"],
    "recall": ["tool_recall_facts"],
    "fact": ["tool_remember_fact", "tool_recall_facts"],
    "facts": ["tool_recall_facts"],
    "plan": ["tool_plan_and_execute_task"],
    "blueprint": ["tool_plan_and_execute_task"],
    "task": ["tool_plan_and_execute_task"],
    "learn": ["tool_learn_heuristic_rule"],
    "heuristic": ["tool_learn_heuristic_rule"],
    "rule": ["tool_learn_heuristic_rule"],
}

def resolve_fast_path(user_query: str) -> Optional[Dict[str, Any]]:
    """
    Evaluate deterministic direct system commands and intents in sub-5ms,
    bypassing the generative LLM loop completely (matching Microsoft Copilot's instant OS execution).
    Returns a dict with {"tool": name, "result": text, "preview": preview} or None if LLM is needed.
    """
    q = user_query.strip().lower()

    # 1. System Volume Control (Sub-15ms hardware event)
    if re.search(r'\b(mute|unmute|toggle mute|silence audio)\b', q):
        res = control_system_volume("mute")
        return {"tool": "control_system_volume", "result": res, "preview": res}
    if re.search(r'\b(volume up|turn up volume|increase volume|raise volume|louder)\b', q):
        res = control_system_volume("up")
        return {"tool": "control_system_volume", "result": res, "preview": res}
    if re.search(r'\b(volume down|turn down volume|decrease volume|lower volume|quieter)\b', q):
        res = control_system_volume("down")
        return {"tool": "control_system_volume", "result": res, "preview": res}

    # 2. Screen Brightness Control
    m_bright = re.search(r'\b(?:set\s+)?brightness(?:\s+to)?\s+(\d{1,3})%?', q)
    if m_bright:
        level = int(m_bright.group(1))
        res = set_display_brightness(level)
        return {"tool": "set_display_brightness", "result": res, "preview": res}

    # 3. Lock Workstation
    if re.search(r'\b(lock (?:the )?(?:pc|computer|screen|workstation)|lock$)\b', q):
        res = lock_workstation()
        return {"tool": "lock_workstation", "result": "✓ Workstation locked.", "preview": "Workstation locked"}

    # 4. Instant Screenshot
    if re.search(r'\b(take (?:a )?screenshot|capture (?:the )?screen|screenshot)\b', q) and not any(w in q for w in ("what", "analyze", "describe")):
        res = take_screenshot()
        return {"tool": "take_screenshot", "result": f"✓ Screenshot captured successfully.\n{res}", "preview": "Screenshot saved"}

    # 5. Instant Screen OCR (Snapdragon WinRT Accelerator)
    if re.search(r'\b(read screen|screen ocr|ocr screen|extract text from screen)\b', q):
        res = hardware_accelerated_screen_ocr()
        return {"tool": "hardware_accelerated_screen_ocr", "result": res, "preview": "Screen text extracted"}

    # 6. Direct App Launch (e.g. "open chrome", "open notepad", "launch calculator")
    m_app = re.match(r'^(?:open|launch|start)\s+([a-zA-Z0-9\s]+)$', q)
    if m_app:
        app_target = m_app.group(1).strip()
        common_apps = ["chrome", "notepad", "calculator", "calc", "edge", "spotify", "terminal", "powershell", "explorer", "files", "vscode", "code"]
        if app_target in common_apps:
            res = open_application(app_target)
            return {"tool": "open_application", "result": f"✓ {res}", "preview": f"Launched {app_target}"}

    # 7. System Vitals / Battery Status
    if re.search(r'^(?:system vitals|vitals|battery status|battery level|how much battery|check vitals)$', q):
        res = format_vitals_summary()
        return {"tool": "get_system_vitals", "result": res, "preview": "Vitals inspected"}

    # 8. Date / Time
    if re.search(r'^(?:what time is it|current time|time|what is the date|what date is today|date)$', q):
        t = get_current_time()
        return {"tool": "get_current_time", "result": f"The current time is **{t}**.", "preview": t}

    # 9. Direct Translation ("translate '...' to [lang]" or "translate ... to [lang]")
    m_trans = re.search(r'\btranslate\s+["\']?([^"\']+)["\']?\s+to\s+([a-zA-Z]+)', user_query, re.IGNORECASE)
    if m_trans:
        phrase = m_trans.group(1).strip()
        target_lang = m_trans.group(2).strip()
        res = translate_language(phrase, target_lang)
        return {"tool": "translate_language", "result": res, "preview": f"Translated to {target_lang}"}

    # 10. Direct World Map ("show map of [location]" or "map of [location]" or "show [location] on map")
    m_map = re.search(r'\b(?:show\s+(?:world\s+)?map\s+of|map\s+of|show\s+([\w\s]+)\s+on\s+(?:the\s+)?map)\s*([a-zA-Z\s,]+)?', user_query, re.IGNORECASE)
    if m_map:
        loc = m_map.group(2) or m_map.group(1)
        if loc and loc.strip() and loc.strip().lower() not in ("me", "us", "this"):
            res = lookup_world_map(loc.strip())
            return {"tool": "lookup_world_map", "result": res, "preview": f"Map of {loc.strip()}"}

    # 11. Autonomous Evolution Pulse ("/evolve", "evolve", "self-evolve", "evolve agent")
    if re.search(r'^(?:/evolve|evolve|self-evolve|evolve agent|run evolution|evolution pulse)$', q):
        active_m = engine.resolve_active_model() if 'engine' in globals() else config.local_model
        res = evolution_engine.run_evolution_cycle(active_model=active_m)
        rules_text = "\n".join([f"- [#{r['id']}] ({r['domain'].upper()}) {r['rule']}" for r in res.get("rules_added", [])])
        msg = (
            f"### 🧬 Evolutionary Cycle Complete (Generation {res['generation']} → {res['next_generation']})\n"
            f"**Research Frontier:** {res['topic']}\n\n"
            f"**Procedural Rules Acquired:**\n{rules_text or '- Principles integrated into memory'}\n\n"
            f"**Total Evolutions:** {res['total_evolutions']} | **Training Dataset:** {res['dataset_count']} samples"
        )
        return {"tool": "evolution_engine", "result": msg, "preview": f"Evolved to Gen {res['next_generation']}"}

    # 12. Instant Procedural Learning & Memory ("learn that ...", "learn rule: ...", "heuristic: ...")
    m_learn = re.match(r'^(?:learn\s+(?:rule\s*:\s*|that\s+)?|heuristic\s*:\s*)(.+)$', q)
    if m_learn:
        rule_content = m_learn.group(1).strip()
        if len(rule_content) > 5:
            rule_id = memory.add_heuristic_rule(rule_content, "procedural")
            res = f"✓ Procedural heuristic #{rule_id} learned and indexed into SQLite FTS5:\n> \"{rule_content}\""
            return {"tool": "learn_heuristic_rule", "result": res, "preview": f"Learned rule #{rule_id}"}

    m_rem = re.match(r'^remember\s+that\s+([^:]+?)\s+is\s+([^:]+)$', q)
    if m_rem:
        entity_str = m_rem.group(1).strip()
        val_str = m_rem.group(2).strip()
        memory.remember_fact("user_context", entity_str, val_str)
        res = f"✓ Stored to long-term memory:\n- [User Context] {entity_str} = {val_str}"
        return {"tool": "remember_fact", "result": res, "preview": f"Remembered {entity_str}"}

    # 13. FreeLLMAPI Status & Online Agent Fast-Paths
    if re.search(r'^(?:/freellmapi|freellmapi|freellmapi status|check freellmapi)$', q):
        res = tool_freellmapi_status()
        return {"tool": "tool_freellmapi_status", "result": res, "preview": "FreeLLMAPI status checked"}

    m_online = re.match(r'^(?:/online|online\s*:)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_online:
        prompt_text = m_online.group(1).strip()
        res = tool_query_online_cortex(prompt_text)
        return {"tool": "tool_query_online_cortex", "result": res, "preview": "Online model query executed"}

    m_swarm = re.match(r'^(?:/swarm|swarm\s*:)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_swarm:
        obj_text = m_swarm.group(1).strip()
        res = tool_dispatch_online_agent_swarm(obj_text)
        return {"tool": "tool_dispatch_online_agent_swarm", "result": res, "preview": "Online agent swarm dispatched"}

    # 14. Auto-Learning Metrics Fast-Paths
    if re.search(r'^(?:/autolearn|/learning-stats|learning stats|learning metrics|auto learning status)$', q):
        res = tool_inspect_auto_learning_metrics()
        return {"tool": "tool_inspect_auto_learning_metrics", "result": res, "preview": "Auto-learning metrics inspected"}

    # 15. Antigravity Skill Vault Fast-Paths
    if re.search(r'^(?:/skills|skills|skill vault|/skill-vault|list skills)$', q):
        res = tool_skills_vault_status()
        return {"tool": "tool_skills_vault_status", "result": res, "preview": "Skill Vault status inspected"}

    m_skill = re.match(r'^(?:/skill|skill\s*:)\s*([a-zA-Z0-9_\-]+)$', user_query.strip(), re.IGNORECASE)
    if m_skill:
        sk_name = m_skill.group(1).strip()
        res = tool_load_skill(sk_name)
        return {"tool": "tool_load_skill", "result": res, "preview": f"Loaded skill {sk_name}"}

    m_search_sk = re.match(r'^(?:/search-skills|search skills\s*:?)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_search_sk:
        q_term = m_search_sk.group(1).strip()
        res = tool_search_skills(q_term)
        return {"tool": "tool_search_skills", "result": res, "preview": f"Searched skills: {q_term}"}

    # 16. Claude Agent Fast-Paths
    if re.search(r'^(?:/todo|/todos|todo|todos)$', q):
        res = claude_todo("list")
        return {"tool": "claude_todo", "result": res, "preview": "Claude tasks listed"}

    m_todo_add = re.match(r'^(?:/todo\s+add|todo\s+add)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_todo_add:
        txt = m_todo_add.group(1).strip()
        res = claude_todo("add", text=txt)
        return {"tool": "claude_todo", "result": res, "preview": f"Task added: {txt}"}

    if re.search(r'^(?:/diff|diff)$', q):
        res = claude_bash("git diff")
        diff_view = f"```diff\n{res}\n```" if res.strip() else "No uncommitted git changes detected."
        return {"tool": "claude_bash", "result": diff_view, "preview": "Git diff displayed"}

    m_claude = re.match(r'^(?:/claude|claude\s*:?|/agent)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_claude:
        prompt_txt = m_claude.group(1).strip()
        res, metrics = claude_agent.execute_turn(prompt_txt)
        return {"tool": "claude_agent", "result": res, "preview": f"Claude Agent executed in {metrics.duration_secs:.2f}s"}

    # 17. Cognitive Deliberation & Neuroplastic Learning Fast-Paths
    m_delib = re.match(r'^(?:/deliberate|deliberate\s*:?)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_delib:
        task_str = m_delib.group(1).strip()
        res = tool_deliberate_problem(task_str)
        return {"tool": "tool_deliberate_problem", "result": res, "preview": f"Deliberated: {task_str[:50]}"}

    m_assimilate = re.match(r'^(?:/assimilate|assimilate\s*:?)\s*([a-zA-Z0-9_\-]+)$', user_query.strip(), re.IGNORECASE)
    if m_assimilate:
        s_target = m_assimilate.group(1).strip()
        res = tool_assimilate_skill(s_target)
        return {"tool": "tool_assimilate_skill", "result": res, "preview": f"Assimilated {s_target}"}

    if re.search(r'^(?:/consolidate|consolidate memory|consolidate)$', q):
        res = tool_consolidate_memory()
        return {"tool": "tool_consolidate_memory", "result": res, "preview": "Memory consolidated"}

    if re.search(r'^(?:/invariants|invariants|learned invariants|reflexion invariants)$', q):
        res = tool_view_learned_invariants()
        return {"tool": "tool_view_learned_invariants", "result": res, "preview": "Invariants inspected"}

    m_selfplay = re.match(r'^(?:/selfplay|selfplay\s*:?)\s*([a-zA-Z0-9_\-]+)?$', user_query.strip(), re.IGNORECASE)
    if m_selfplay:
        dom = (m_selfplay.group(1) or "coding").strip()
        res = tool_trigger_self_play(dom)
        return {"tool": "tool_trigger_self_play", "result": res, "preview": f"Self-play run in {dom}"}

    # 18. Diversified Curriculum & Task Engagement Fast-Paths
    m_eng = re.match(r'^(?:/engage|engage\s*:?)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_eng:
        obj_text = m_eng.group(1).strip()
        res = tool_create_engagement_dag(obj_text)
        return {"tool": "tool_create_engagement_dag", "result": res, "preview": f"DAG created: {obj_text[:40]}"}

    if re.search(r'^(?:/dag|dag|/engagement|engagement status)$', q):
        res = tool_get_active_engagement_status()
        return {"tool": "tool_get_active_engagement_status", "result": res, "preview": "Active DAG inspected"}

    m_adv = re.match(r'^(?:/advance|advance\s*:?)\s*([a-zA-Z0-9_\-]+)?(?:\s+(.+))?$', user_query.strip(), re.IGNORECASE)
    if m_adv and q.startswith(("/advance", "advance")):
        tid = m_adv.group(1) or ""
        r_sum = m_adv.group(2) or "Milestone advanced."
        res = tool_advance_engagement_task(tid, r_sum)
        return {"tool": "tool_advance_engagement_task", "result": res, "preview": f"Advanced task {tid or 'active'}"}

    m_pers = re.match(r'^(?:/persona|persona\s*:?)\s*([a-zA-Z_]+)$', user_query.strip(), re.IGNORECASE)
    if m_pers:
        p_name = m_pers.group(1).strip()
        res = tool_set_engagement_persona(p_name)
        return {"tool": "tool_set_engagement_persona", "result": res, "preview": f"Persona set to {p_name}"}

    if re.search(r'^(?:/disciplines|disciplines|curriculum disciplines)$', q):
        discs = curriculum_learner.list_disciplines()
        lines = ["### 🌌 8 Frontier Cognitive Disciplines:"]
        for d in discs:
            lines.append(f"- **{d['title']}** (`{d['key']}`): {d['description']}")
        return {"tool": "curriculum_learner", "result": "\n".join(lines), "preview": "Disciplines listed"}

    m_tourn = re.match(r'^(?:/tournament|tournament\s*:?)\s*([a-zA-Z0-9_\-]+)?$', user_query.strip(), re.IGNORECASE)
    if m_tourn and q.startswith(("/tournament", "tournament")):
        disc_target = (m_tourn.group(1) or "distributed_systems").strip()
        res = tool_run_adversarial_tournament(disc_target)
        return {"tool": "tool_run_adversarial_tournament", "result": res, "preview": f"Tournament in {disc_target}"}

    # 19. Sovereign Online Gateway & Public Tunnel Fast-Paths
    if re.search(r'^(?:/tunnel|tunnel|/online|online status)$', q):
        res = tool_get_online_tunnel_status()
        return {"tool": "tool_get_online_tunnel_status", "result": res, "preview": "Online tunnel status inspected"}

    m_tunnel_start = re.match(r'^(?:/tunnel\s+start|tunnel\s+start|start\s+tunnel|make\s+online)(?:\s+([a-zA-Z0-9_\-]+))?$', user_query.strip(), re.IGNORECASE)
    if m_tunnel_start:
        prov = (m_tunnel_start.group(1) or "auto").strip()
        res = tool_start_online_tunnel(provider=prov)
        return {"tool": "tool_start_online_tunnel", "result": res, "preview": f"Online tunnel started via {prov}"}

    if re.search(r'^(?:/tunnel\s+stop|tunnel\s+stop|stop\s+tunnel)$', q):
        res = tool_stop_online_tunnel()
        return {"tool": "tool_stop_online_tunnel", "result": res, "preview": "Online tunnel stopped"}

    if re.search(r'^(?:/freemodels|free models|freellm models)$', q):
        res = tool_list_free_online_models()
        return {"tool": "tool_list_free_online_models", "result": res, "preview": "Free online models listed"}

    m_freeai = re.match(r'^(?:/freeai|freeai\s*:?)\s*(.+)$', user_query.strip(), re.IGNORECASE)
    if m_freeai:
        ai_prompt = m_freeai.group(1).strip()
        res = tool_query_free_online_ai(ai_prompt)
        return {"tool": "tool_query_free_online_ai", "result": res, "preview": f"Queried Free AI: {ai_prompt[:40]}"}

    # 20. LEON Autonomous Venture OS & Sub-Agent Swarm Fast-Paths
    if re.search(r'^(?:/leon|/ventures|/ledger|venture ledger|leon ledger)$', q):
        res = tool_leon_get_venture_ledger()
        return {"tool": "tool_leon_get_venture_ledger", "result": res, "preview": "LEON venture ledger inspected"}

    if re.search(r'^(?:/train-leon|train leon|train leon model|leon train)$', q):
        res = tool_train_leon_venture_model()
        return {"tool": "tool_train_leon_venture_model", "result": res, "preview": "LEON training dataset ingested & dispatched"}

    m_swarm_leon = re.match(r'^(?:/leon-swarm|leon-swarm\s*:?|/venture-build)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_swarm_leon:
        target_obj = m_swarm_leon.group(1).strip()
        res = tool_leon_dispatch_subagent_swarm("active_venture", target_obj)
        return {"tool": "tool_leon_dispatch_subagent_swarm", "result": res, "preview": f"LEON swarm dispatched for {target_obj[:30]}"}

    # 21. LEON Live Cloud Deployer & Razorpay/Stripe Fast-Paths
    if re.search(r'^(?:/deployments|/live-ventures|deployed ventures)$', q):
        res = tool_leon_get_deployed_ventures()
        return {"tool": "tool_leon_get_deployed_ventures", "result": res, "preview": "Deployed ventures listed"}

    m_deploy_leon = re.match(r'^(?:/leon-deploy|/deploy-venture|deploy venture\s*:?)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_deploy_leon:
        v_name = m_deploy_leon.group(1).strip()
        res = tool_leon_deploy_venture_to_cloud(
            venture_name=v_name,
            niche="general_tech",
            value_prop=f"Autonomous AI solutions for modern enterprises by {v_name}.",
            provider="vercel",
        )
    # 22. LEON Portfolio & Low-Cost Subscription Fast-Paths
    if re.search(r'^(?:/portfolio|/businesses|portfolio status|business models)$', q):
        res = tool_leon_get_portfolio_status()
        return {"tool": "tool_leon_get_portfolio_status", "result": res, "preview": "Portfolio status inspected"}

    if re.search(r'^(?:/launch-all|launch all|launch all businesses|start all business models|start all businesses)$', q):
        res = tool_leon_launch_all_low_cost_businesses(provider="vercel")
        return {"tool": "tool_leon_launch_all_low_cost_businesses", "result": res, "preview": "All low-cost businesses launched live"}

    m_rev = re.match(r'^(?:/revise-pricing|revise pricing\s*:?)\s+([a-zA-Z0-9_\-]+)\s+(\d+)\s+(\d+)(?:\s+(.+))?$', user_query.strip(), re.IGNORECASE)
    if m_rev:
        v_slug = m_rev.group(1).strip()
        new_mo = float(m_rev.group(2))
        new_yr = float(m_rev.group(3))
        reason = (m_rev.group(4) or "Manual founder pricing revision.").strip()
        res = tool_leon_revise_business_pricing(v_slug, new_mo, new_yr, reason)
        return {"tool": "tool_leon_revise_business_pricing", "result": res, "preview": f"Revised pricing for {v_slug}"}

    # ── AGI Planner fast-paths (/plan, /goal, /goals, /self-eval) ──────────────

    # /plan <goal> — decompose and execute immediately via AgiPlanner
    m_plan = re.match(r'^(?:/plan|plan\s*:)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_plan:
        goal_text = m_plan.group(1).strip()
        from aether.agi.planner import agi_planner
        agi_planner.register_tools(TOOL_DISPATCHER)
        plan = agi_planner.run_goal(goal=goal_text, steps=[
            {"name": "status_check", "tool": "tool_get_system_vitals", "args": {}},
            {"name": "asset_health", "tool": "tool_agi_asset_registry_summary", "args": {}},
        ])
        res = (
            f"### 🧠 AGI Planner — `{goal_text[:60]}`\n"
            f"**Plan ID:** `{plan.id}` | **Status:** `{plan.status.value}`\n\n"
            + "\n".join(
                f"- `{s.name}` → **{s.status.value}**"
                + (f" — _{s.error}_" if s.error else "")
                for s in plan.steps
            )
        )
        return {"tool": "agi_planner", "result": res, "preview": f"Plan {plan.status.value}"}

    # /goal <text> [--priority N] — add to persistent goal queue
    m_goal = re.match(r'^(?:/goal|goal\s*:)\s+(.+?)(?:\s+--priority\s+([1-5]))?$', user_query.strip(), re.IGNORECASE)
    if m_goal:
        from aether.agi.goal_queue import goal_queue
        gt = m_goal.group(1).strip()
        prio = int(m_goal.group(2) or 3)
        gid = goal_queue.add(gt, priority=prio, source="chat")
        summary = goal_queue.summary()
        res = (
            f"✅ Goal queued: **{gt}** (ID: `{gid}`, priority: {prio})\n\n"
            f"Queue: {summary['total']} total — {summary['by_status'].get('pending',0)} pending"
        )
        return {"tool": "goal_queue", "result": res, "preview": f"Goal queued: {gt[:40]}"}

    # /goals — list the goal queue
    if re.search(r'^(?:/goals|goals queue|goal queue|list goals)$', q):
        from aether.agi.goal_queue import goal_queue
        goals = goal_queue.list_all()
        if not goals:
            return {"tool": "goal_queue", "result": "📋 Goal queue is empty.", "preview": "Queue empty"}
        lines = ["### 📋 AETHER Goal Queue\n"]
        for g in goals[-20:]:
            icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(g["status"], "•")
            lines.append(f"{icon} **[P{g['priority']}]** `{g['id']}` — {g['goal'][:60]}")
        return {"tool": "goal_queue", "result": "\n".join(lines), "preview": f"{len(goals)} goals"}

    # /self-eval — trigger immediate self-evaluation
    if re.search(r'^(?:/self-eval|self-eval|self eval|evaluate assets|asset health)$', q):
        from aether.daemon.autonomous_operator import autonomous_operator
        autonomous_operator.job_self_evaluation()
        from aether.utils.asset_registry import asset_registry
        from aether.utils.evaluator import compute_portfolio_health
        h = compute_portfolio_health(asset_registry.read_all())
        res = (
            f"### 🧬 Self-Evaluation Complete\n"
            f"- **Avg health score:** `{h.get('avg_score', 0):.3f}`\n"
            f"- **Status:** {'✅ Healthy' if h.get('healthy') else '⚠️ Retrain triggered'}\n"
            f"- **Total assets tracked:** `{h.get('total', 0)}`\n"
            f"- **By type:** {h.get('by_type', {})}"
        )
        return {"tool": "self_evaluation", "result": res, "preview": f"Health {h.get('avg_score',0):.2f}"}

    # /escalate <query> or /nex <query> — dispatch directly to Nex-N2.5-mini Cloud Escalation Cortex
    m_esc = re.match(r'^(?:/escalate|escalate\s*:?|/nex|nex\s*:?)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_esc:
        prompt_txt = m_esc.group(1).strip()
        from aether.brain.multi_provider_router import MultiProviderRouter
        router = MultiProviderRouter()
        messages = [
            {"role": "system", "content": "You are AETHER Escalated Cortex (powered by Nex-N2.5-mini). Provide systematic, deterministic, frontier agentic analysis."},
            {"role": "user", "content": prompt_txt},
        ]
        try:
            resp = router.complete_chat(messages=messages, intent="escalation", user_override="nex")
            res_content = resp.get("content", "")
            prov_name = resp.get("provider", "ESCALATED CORTEX")
            model_name = resp.get("model", "nex-agi/nex-n2.5-mini")
            speed = resp.get("tok_per_sec", 0)
            res = (
                f"### ⚡ Escalation Response ({prov_name} — `{model_name}`)\n\n"
                f"{res_content}\n\n"
                f"---\n*⚡ {speed} tok/s | Latency: {resp.get('duration', 0):.2f}s*"
            )
            return {"tool": "escalate_model", "result": res, "preview": f"Escalated to {model_name}"}
        except Exception as e:
            return {"tool": "escalate_model", "result": f"⚠️ Escalation error: {e}", "preview": "Escalation failed"}

    # ── Agency Specialists Fast-Paths (/agency, /agency-recs, /agents, /agency-vault) ───

    # /agency-vault — audit API keys and inference backends for Agency Specialists
    if re.search(r'^(?:/agency-vault|agency vault|api keys status|audit api keys)$', q):
        from aether.brain.agency_vault import agency_vault
        audit = agency_vault.audit_credentials()
        lines = ["### 🔐 AETHER Agency API & Backend Vault\n"]
        lines.append("**Inference Backends:**")
        for k, v in audit["inference_backends"].items():
            status_icon = "✅ Ready" if v["status"] == "ready" else "⚠️ Optional/Missing"
            lines.append(f"- **{k.upper()}**: {status_icon} — _{v['description']}_")
        lines.append("\n**Training Clusters:**")
        for k, v in audit["training_cluster"].items():
            status_icon = "✅ Ready" if v["status"] == "ready" else "⚠️ Needs Key"
            lines.append(f"- **{k.upper()}**: {status_icon} — _{v['description']}_")
        best = agency_vault.resolve_best_agent_backend()
        lines.append(f"\n🎯 **Active Primary Agency Specialist Backend:** `{best['label']}`")
        return {"tool": "agency_vault", "result": "\n".join(lines), "preview": f"Agency Backend: {best['provider']}"}

    # /agency-divisions or /agents — list the 18 agency divisions and specialist count
    if re.search(r'^(?:/agency-divisions|/agents|agents roster|agency roster|list agency agents)$', q):
        from aether.brain.agency_specialists_engine import agency_engine
        divs = agency_engine.list_divisions()
        total = sum(divs.values())
        lines = [f"### 🏢 Agency Agents Roster ({total} Specialists across 18 Divisions)\n"]
        for div, count in divs.items():
            lines.append(f"- **{div.title()}**: `{count}` specialists (e.g. `/agency-recs {div}`)")
        lines.append("\n*Tip: Run `/agency <specialist_slug> <task>` to dispatch any specialist directly.*")
        return {"tool": "agency_roster", "result": "\n".join(lines), "preview": f"{total} specialists"}

    # /agency-recs <goal> — recommend specialists for a project or goal
    m_recs = re.match(r'^(?:/agency-recs|agency recs|recommend agents)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_recs:
        target_goal = m_recs.group(1).strip()
        from aether.brain.agency_specialists_engine import agency_engine
        recs = agency_engine.recommend_specialists(target_goal, top_k=5)
        lines = [f"### 🎯 Recommended Agency Specialists for: *{target_goal}*\n"]
        for r in recs:
            lines.append(f"- {r['emoji']} **{r['name']}** (`{r['slug']}`) — *{r['division'].title()}*\n  _{r['description'][:140]}..._\n  Command: `/agency {r['slug']} <your task>`\n")
        return {"tool": "agency_recommendations", "result": "\n".join(lines), "preview": f"{len(recs)} recommended"}

    # /agency <specialist_slug_or_name> <task> — dispatch specialized agency agent
    m_agency = re.match(r'^(?:/agency|agency\s*:?)\s+([a-zA-Z0-9_\-]+)\s+(.+)$', user_query.strip(), re.IGNORECASE)
    if m_agency:
        agent_target = m_agency.group(1).strip()
        task_body = m_agency.group(2).strip()
        from aether.brain.agency_specialists_engine import agency_engine
        res = agency_engine.dispatch_specialist(agent_target, task_body)
        if res.get("status") == "completed":
            out = (
                f"### {res['emoji']} {res['agent_name']} ({res['division'].title()} Division)\n\n"
                f"{res['response']}\n\n"
                f"---\n*⚡ Executed via {res['provider']} ({res['model']}) | {res['tok_per_sec']} tok/s | {res['duration']:.2f}s*"
            )
            return {"tool": "agency_specialist", "result": out, "preview": f"{res['agent_name']} delivered"}
        else:
            return {"tool": "agency_specialist", "result": f"⚠️ {res.get('error') or res.get('detail')}", "preview": "Specialist failed"}

    return None








def select_tools_for_query(query: str) -> Optional[List[Callable]]:
    """
    Select a minimal, targeted subset of tools (max 6) based on intent keywords.
    Filters pure small-talk conversational queries to return None (sub-second TTFT).
    For actionable project, coding, or computer tasks, guarantees the core engineering toolkit.
    """
    q = query.strip().lower()

    # Conversational small-talk filter: instant sub-second response without tool overhead
    conversational_patterns = [
        r'^(?:hi|hello|hey|greetings|good\s+(?:morning|afternoon|evening|night)|howdy)\b',
        r'^(?:who\s+are\s+you|what\s+is\s+your\s+name|how\s+are\s+you|what\s+can\s+you\s+do\??)$',
        r'^(?:thanks|thank\s+you|cool|awesome|great|ok|okay)\.?$'
    ]
    if any(re.match(p, q) for p in conversational_patterns) and len(q.split()) <= 4:
        return None

    selected_names = set()
    for kw, tool_names in ACTION_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', q):
            selected_names.update(tool_names)

    # Supply core engineering toolkit if query has actionable intent
    if not selected_names:
        action_indicators = ["file", "dir", "folder", "run", "exec", "test", "check", "inspect", "create", "write", "read", "search", "find", "fix", "delete", "build", "install", "git"]
        if any(w in q for w in action_indicators):
            core_fallback = [
                "tool_inspect_directory",
                "tool_read_file",
                "tool_write_file",
                "tool_find_files",
                "tool_search_file_content",
                "tool_execute_command"
            ]
            selected_names.update(core_fallback)

    matched = [TOOL_DISPATCHER[name] for name in selected_names if name in TOOL_DISPATCHER][:6]
    return matched if matched else None



def ensure_ollama_alive() -> bool:
    """Ensure Ollama daemon is running. Auto-starts in background if not currently active."""
    import os
    import shutil
    import socket
    import subprocess
    import time
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        if s.connect_ex(("127.0.0.1", 11434)) == 0:
            return True
            
    try:
        candidates = [
            shutil.which("ollama.exe"),
            shutil.which("ollama"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"),
            r"C:\Users\saali\AppData\Local\Programs\Ollama\ollama.exe",
        ]
        exe = next((c for c in candidates if c and Path(c).exists()), None)
        if exe:
            flags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([exe, "serve"], creationflags=flags)
            for _ in range(12):
                time.sleep(0.5)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.4)
                    if s.connect_ex(("127.0.0.1", 11434)) == 0:
                        return True
    except Exception:
        pass
    return False


def sanitize_final_text(text: str) -> str:
    """
    Ensure no raw tool JSON function call syntax or internal meta-dialogue reaches the user.
    Preserves valid user-requested JSON code blocks and markdown.
    """
    if not text:
        return ""
    clean = re.sub(r'\{"name":\s*"tool_[^}]+\}', '', text)
    clean = re.sub(r'```(?:json)?\s*\{\s*"name":\s*"tool_[^}]+.*?\}\s*```', '', clean, flags=re.DOTALL)
    clean = re.sub(r'To answer the prompt.*?provide a JSON function call.*?:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    # Strip orphaned JSON brackets or artifacts
    if clean.strip() in ['"}}', '}', '}}', '{"', '""', '"', '}"', '}}"', '}}:']:
        return ""
    return clean


SENTENCE_DELIMITER = re.compile(r'(?<=[.?!;\n])\s+')


class CognitiveEngine:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.local_model
        self._cached_active_model: Optional[str] = None

    def resolve_active_model(self) -> str:
        """
        Detect whether the configured model (e.g. qwen2.5:3b) is downloaded.
        If not, automatically fall back to available models like llama3.2:3b.
        """
        try:
            models_info = ollama.list()
            installed = [m.get("model", m.get("name", "")) for m in models_info.get("models", [])]
            for m in installed:
                if m.startswith(self.model_name) or self.model_name in m:
                    self._cached_active_model = self.model_name
                    return self.model_name

            # Fallback priority list
            fallbacks = ["aether:finetuned", "aether:autonomous", "aether:antigravity", "aether:coder", "qwen2.5-coder:3b", "llama3.2:3b", "llama3.2:lowram", "openclaw:latest"]
            for fb in fallbacks:
                for m in installed:
                    if m.startswith(fb) or fb in m:
                        self._cached_active_model = m
                        return m


            if installed:
                self._cached_active_model = installed[0]
                return installed[0]
        except Exception:
            pass

        return self.model_name

    def get_runtime_options(self) -> Dict[str, Any]:
        """Hardware-tuned options for Snapdragon NPU/CPU and low-memory consumption."""
        return {
            "temperature": config.temperature,
            "num_ctx": config.context_window,
            "num_thread": config.num_threads,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 2048,
        }

    def unload_model(self) -> None:
        """Immediately purge the model from RAM to reclaim all memory."""
        try:
            active = self.resolve_active_model()
            ollama.chat(model=active, messages=[], keep_alive=0)
            gc.collect()
        except Exception:
            pass

    def recall_relevant_context(self, user_query: str) -> str:
        """Fetch past episodes or related facts relevant to the current user prompt."""
        facts = memory.recall_facts()
        episodes = memory.search_episodes(user_query, limit=3)

        sections = []
        if facts:
            fact_lines = [f"- {f['entity']} {f['attribute']}: {f['value']}" for f in facts[:6]]
            sections.append("Known Facts:\n" + "\n".join(fact_lines))

        if episodes:
            ep_lines = [f"[{e['timestamp']}] {e['role'].upper()}: {e['content'][:250]}" for e in episodes if e['role'] in ('user', 'assistant')]
            if ep_lines:
                sections.append("Relevant Context:\n" + "\n".join(ep_lines))

        return "\n\n".join(sections)

    def _prepare_turn_messages(self, user_message: str, session_id: str = "default") -> List[Dict[str, Any]]:
        """Construct strict ChatML alternating turn sequence with memory recall."""
        # Dynamic context compaction check (MemGPT pattern)
        memory.compact_episodes(keep_recent=4, watermark_tokens=3500)

        recalled_context = self.recall_relevant_context(user_message)
        learned_rules = memory.recall_heuristic_rules(user_message, limit=4)
        system_prompt = build_system_prompt(recalled_context, learned_rules=learned_rules)

        recent_turns = memory.get_recent_episodes(limit=8)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        last_role = "system"
        for turn in recent_turns:
            role = turn["role"]
            content = turn["content"].strip()
            # Strictly filter to user and assistant roles only
            if role not in ("user", "assistant") or not content:
                continue
            if content.startswith("/"):
                continue
            # Enforce strict role alternation
            if role != last_role:
                messages.append({"role": role, "content": content})
                last_role = role

        if last_role == "user":
            messages.pop()

        messages.append({"role": "user", "content": user_message})
        memory.add_episode("user", user_message, session_id=session_id)
        return messages

    def process_query(
        self,
        user_message: str,
        session_id: str = "default",
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        """
        Execute the cognitive loop with autonomous tool execution and clean natural synthesis.
        Completely unthrottled and personalized for the user.
        """
        ensure_ollama_alive()
        config.refresh_power_profile()
        assert_safe_resources()

        active_model = self.resolve_active_model()

        # Instant Fast-Path for direct system commands, translation, and maps (sub-15ms, matching Copilot OS execution)
        fast_action = resolve_fast_path(user_message)
        if fast_action:
            tool_name = fast_action["tool"]
            result_str = fast_action["result"]
            preview_str = fast_action["preview"]
            if on_tool_start:
                on_tool_start(tool_name, {"query": user_message})
            if on_tool_end:
                on_tool_end(tool_name, preview_str)
            memory.add_episode("user", user_message, session_id=session_id)
            memory.add_episode("assistant", result_str, session_id=session_id)
            voice.speak_async(result_str)
            return result_str

        # Fast-path for explicit planning commands
        if user_message.strip().startswith(("/plan", "/rewoo")):
            task_prompt = re.sub(r"^/(plan|rewoo)\s*", "", user_message.strip())
            planner = ReWOOPlanner(model=active_model, tools=TOOL_DISPATCHER, keep_alive=config.keep_alive)
            res = planner.execute(task_prompt, on_tool_start=on_tool_start, on_tool_end=on_tool_end)
            final_text = sanitize_final_text(res)
            memory.add_episode("assistant", final_text, session_id=session_id)
            voice.speak_async(final_text)
            return final_text

        # Explicit / Trigger-based Codex Agent execution
        if user_message.strip().startswith(("/codex", "/agent", "/antigravity")):
            clean_task = re.sub(r"^/(codex|agent|antigravity)\s*", "", user_message.strip())
            report = antigravity_codex_agent.execute_task(
                task=clean_task,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
            )
            final_text = sanitize_final_text(report.final_response)
            memory.add_episode("assistant", final_text, session_id=session_id)
            voice.speak_async(final_text)
            return final_text

        # Explicit / Trigger-based Deep Deliberation
        if user_message.strip().startswith(("/deliberate", "/think")):
            clean_task = re.sub(r"^/(deliberate|think)\s*", "", user_message.strip())
            delib_res = thinking_cortex.deliberate(clean_task)
            final_text = sanitize_final_text(f"{delib_res.full_trace}\n\n{delib_res.synthesizer_plan}")
            memory.add_episode("assistant", final_text, session_id=session_id)
            voice.speak_async(delib_res.synthesizer_plan)
            return final_text

        # Mode: Turbo Reflex (Ultra-Fast 800+ tok/s Stream)
        if config.cognitive_mode == "turbo_reflex" or user_message.strip().startswith(("/turbo", "/reflex")):
            clean_msg = re.sub(r"^/(turbo|reflex)\s*", "", user_message.strip())
            comp = multi_provider_router.complete_chat(
                messages=[{"role": "user", "content": clean_msg}],
                intent="reflex",
                temperature=0.3,
            )
            final_text = sanitize_final_text(comp.get("content", ""))
            memory.add_episode("assistant", final_text, session_id=session_id)
            voice.speak_async(final_text)
            return final_text

        # Mode: Auto Omniscient Classifier
        if config.cognitive_mode == "auto":
            lower_msg = user_message.lower()
            is_coding = any(kw in lower_msg for kw in ["write a script", "build a", "create a function", "refactor", "debug this", "fix the error", "unit test", "traceback", "implement "]) and len(user_message) > 35
            
            # Route heavy coding tasks to Antigravity Codex Agent if cloud keys or code model available
            if is_coding and (multi_provider_router.get_api_key("openrouter") or multi_provider_router.get_api_key("gemini") or multi_provider_router.get_api_key("groq")):
                report = antigravity_codex_agent.execute_task(
                    task=user_message,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                )
                final_text = sanitize_final_text(report.final_response)
                memory.add_episode("assistant", final_text, session_id=session_id)
                voice.speak_async(final_text)
                return final_text

            # Route deep architectural questions to ThinkingCortex
            should_delib, _ = thinking_cortex.should_deliberate(user_message)
            if should_delib and (multi_provider_router.get_api_key("groq") or multi_provider_router.get_api_key("gemini")):
                delib_res = thinking_cortex.deliberate(user_message)
                final_text = sanitize_final_text(f"{delib_res.full_trace}\n\n{delib_res.synthesizer_plan}")
                memory.add_episode("assistant", final_text, session_id=session_id)
                voice.speak_async(delib_res.synthesizer_plan)
                return final_text


        messages = self._prepare_turn_messages(user_message, session_id=session_id)
        opts = self.get_runtime_options()
        max_iterations = 10
        final_text = ""
        query_tools = select_tools_for_query(user_message)
        executed_tools: List[Dict[str, Any]] = []

        try:
            for _ in range(max_iterations):
                chat_kwargs = {
                    "model": active_model,
                    "messages": messages,
                    "options": opts,
                    "keep_alive": config.keep_alive,
                }
                if query_tools:
                    chat_kwargs["tools"] = query_tools

                response = ollama.chat(**chat_kwargs)

                msg = response.message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    final_text = msg.content or ""
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": tool_calls,
                })

                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    func_args = tool_call.function.arguments or {}

                    if on_tool_start:
                        on_tool_start(func_name, func_args)

                    fn = TOOL_DISPATCHER.get(func_name)
                    if fn:
                        try:
                            result = fn(**func_args)
                            if isinstance(result, str) and any(err_kw in result.lower() for err_kw in ["action error:", "tool error", "syntaxerror", "filenotfound", "traceback"]):
                                heal_res = reflexion_engine.reflect_and_heal(
                                    failed_tool=func_name,
                                    args=func_args,
                                    error_message=str(result),
                                    original_task=user_message,
                                    model_name=active_model,
                                )
                                result = f"{result}\n\n{heal_res['self_heal_directive']}"
                        except Exception as e:
                            err_str = f"Action error: {str(e)}"
                            heal_res = reflexion_engine.reflect_and_heal(
                                failed_tool=func_name,
                                args=func_args,
                                error_message=str(e),
                                original_task=user_message,
                                model_name=active_model,
                            )
                            result = f"{err_str}\n\n{heal_res['self_heal_directive']}"
                    else:
                        result = (
                            f"Action '{func_name}' is not in active TOOL_DISPATCHER.\n"
                            f"Tip: Invoke `tool_synthesize_new_tool(task_description=..., tool_name='{func_name}')` to dynamically synthesize and mount this tool live."
                        )

                    executed_tools.append({
                        "tool": func_name,
                        "args": func_args,
                        "result": result,
                        "is_error": "error" in str(result).lower() or "exception" in str(result).lower(),
                    })

                    if on_tool_end:
                        on_tool_end(func_name, str(result)[:150])

                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        "name": func_name,
                    })

            if not final_text:
                final_res = ollama.chat(
                    model=active_model,
                    messages=messages,
                    options=opts,
                    keep_alive=config.keep_alive,
                )
                final_text = final_res.message.content or ""

            final_text = sanitize_final_text(final_text)
            memory.add_episode("assistant", final_text, session_id=session_id)
            voice.speak_async(final_text)

            # Autonomous Self-Directed Turn Introspection & Continuous Learning
            if getattr(config, "auto_learning_enabled", True):
                auto_learner.introspect_turn_async(
                    user_message=user_message,
                    assistant_response=final_text,
                    tool_events=executed_tools,
                    session_id=session_id,
                )

        finally:
            gc.collect()

        return final_text


    def process_query_stream(
        self,
        user_message: str,
        session_id: str = "web-ui",
    ):
        """
        Generator for streaming cognitive inference over WebSockets:
        Yields tool events, live streaming tokens, and sentence-boundary audio chunks
        for sub-400ms voice response latency (TTFA).
        """
        ensure_ollama_alive()
        config.refresh_power_profile()
        assert_safe_resources()

        active_model = self.resolve_active_model()

        # Instant Fast-Path for direct system commands, translation, and maps (sub-15ms, matching Copilot OS execution)
        fast_action = resolve_fast_path(user_message)
        if fast_action:
            tool_name = fast_action["tool"]
            result_str = fast_action["result"]
            preview_str = fast_action["preview"]
            yield {"type": "tool_start", "tool": tool_name, "args": {"query": user_message}}
            yield {"type": "tool_end", "tool": tool_name, "preview": preview_str}
            memory.add_episode("user", user_message, session_id=session_id)
            memory.add_episode("assistant", result_str, session_id=session_id)
            for chunk in result_str.split(" "):
                yield {"type": "token", "token": chunk + " "}
            speech_clean = re.sub(r'```.*?```', '', result_str, flags=re.DOTALL)
            speech_clean = re.sub(r'[*#_`\[\]]', '', speech_clean).strip()
            if speech_clean:
                yield {"type": "audio_chunk", "text": speech_clean[:250]}
            yield {"type": "done", "response": result_str, "model": "Direct Hardware Fast-Path ⚡"}
            return

        # Explicit / Trigger-based Codex Agent execution
        if user_message.strip().startswith(("/codex", "/agent", "/antigravity")):
            clean_task = re.sub(r"^/(codex|agent|antigravity)\s*", "", user_message.strip())
            
            def _on_tool_start(tool_name: str, args: Dict[str, Any]):
                pass

            report = antigravity_codex_agent.execute_task(task=clean_task)
            for step in report.steps_taken:
                yield {"type": "tool_start", "tool": step["tool"], "args": step["args"]}
                yield {"type": "tool_end", "tool": step["tool"], "preview": step["result_preview"]}
            
            final_text = sanitize_final_text(report.final_response)
            memory.add_episode("assistant", final_text, session_id=session_id)
            for chunk in final_text.split(" "):
                yield {"type": "token", "token": chunk + " "}
            yield {"type": "done", "response": final_text, "model": f"Antigravity Codex ({report.provider_used or 'Autonomous'})", "duration": report.duration_secs}
            return

        # Explicit / Trigger-based Deep Deliberation
        if user_message.strip().startswith(("/deliberate", "/think")):
            clean_task = re.sub(r"^/(deliberate|think)\s*", "", user_message.strip())
            delib_res = thinking_cortex.deliberate(clean_task)
            final_text = sanitize_final_text(f"{delib_res.full_trace}\n\n{delib_res.synthesizer_plan}")
            memory.add_episode("assistant", final_text, session_id=session_id)
            for chunk in final_text.split(" "):
                yield {"type": "token", "token": chunk + " "}
            yield {"type": "done", "response": final_text, "model": "Cognitive Deliberation (System 2)"}
            return

        # Mode: Turbo Reflex (Ultra-Fast 800+ tok/s Stream)
        if config.cognitive_mode == "turbo_reflex" or user_message.strip().startswith(("/turbo", "/reflex")):
            clean_msg = re.sub(r"^/(turbo|reflex)\s*", "", user_message.strip())
            comp = multi_provider_router.complete_chat(
                messages=[{"role": "user", "content": clean_msg}],
                intent="reflex",
                temperature=0.3,
            )
            final_text = sanitize_final_text(comp.get("content", ""))
            memory.add_episode("assistant", final_text, session_id=session_id)
            for chunk in final_text.split(" "):
                yield {"type": "token", "token": chunk + " "}
            yield {
                "type": "done",
                "response": final_text,
                "model": f"{comp.get('provider', 'Groq')} ⚡ ({comp.get('tok_per_sec', 0)} tok/s)",
                "tok_per_sec": comp.get("tok_per_sec", 0),
                "duration": comp.get("duration", 0),
            }
            return

        if user_message.strip().startswith(("/plan", "/rewoo")):
            task_prompt = re.sub(r"^/(plan|rewoo)\s*", "", user_message.strip())
            planner = ReWOOPlanner(model=active_model, tools=TOOL_DISPATCHER, keep_alive=config.keep_alive)
            res = planner.execute(task_prompt)
            yield {"type": "tool_end", "tool": "ReWOOPlanner", "preview": "Blueprint executed"}
            final_text = sanitize_final_text(res)
            memory.add_episode("assistant", final_text, session_id=session_id)
            for chunk in final_text.split(" "):
                yield {"type": "token", "token": chunk + " "}
            yield {"type": "audio_chunk", "text": final_text[:250]}
            yield {"type": "done", "response": final_text, "model": active_model}
            return


        messages = self._prepare_turn_messages(user_message, session_id=session_id)
        opts = self.get_runtime_options()
        max_iterations = 10
        query_tools = select_tools_for_query(user_message)

        try:
            # 1. First resolve any tool calls non-streamed (or until final synthesis)
            for _ in range(max_iterations):
                chat_kwargs = {
                    "model": active_model,
                    "messages": messages,
                    "options": opts,
                    "keep_alive": config.keep_alive,
                }
                if query_tools:
                    chat_kwargs["tools"] = query_tools

                response = ollama.chat(**chat_kwargs)

                msg = response.message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    # Model provided text directly or no tools needed
                    initial_text = msg.content or ""
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": tool_calls,
                })

                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    func_args = tool_call.function.arguments or {}

                    yield {
                        "type": "tool_start",
                        "tool": func_name,
                        "args": func_args,
                    }

                    fn = TOOL_DISPATCHER.get(func_name)
                    if fn:
                        try:
                            result = fn(**func_args)
                            if isinstance(result, str) and any(err_kw in result.lower() for err_kw in ["action error:", "tool error", "syntaxerror", "filenotfound", "traceback"]):
                                heal_res = reflexion_engine.reflect_and_heal(
                                    failed_tool=func_name,
                                    args=func_args,
                                    error_message=str(result),
                                    original_task=user_message,
                                    model_name=active_model,
                                )
                                result = f"{result}\n\n{heal_res['self_heal_directive']}"
                        except Exception as e:
                            err_str = f"Action error: {str(e)}"
                            heal_res = reflexion_engine.reflect_and_heal(
                                failed_tool=func_name,
                                args=func_args,
                                error_message=str(e),
                                original_task=user_message,
                                model_name=active_model,
                            )
                            result = f"{err_str}\n\n{heal_res['self_heal_directive']}"
                    else:
                        result = (
                            f"Action '{func_name}' is not in active TOOL_DISPATCHER.\n"
                            f"Tip: Invoke `tool_synthesize_new_tool(task_description=..., tool_name='{func_name}')` to dynamically synthesize and mount this tool live."
                        )

                    preview = str(result)[:150].replace("\n", " ")
                    yield {
                        "type": "tool_end",
                        "tool": func_name,
                        "preview": preview,
                    }

                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        "name": func_name,
                    })

            # 2. Final response generation streamed token-by-token
            stream_res = ollama.chat(
                model=active_model,
                messages=messages,
                options=opts,
                keep_alive=config.keep_alive,
                stream=True,
            )

            full_content = ""
            sentence_buffer = ""

            for chunk in stream_res:
                token = chunk.get("message", {}).get("content", "")
                if not token:
                    continue

                full_content += token
                sentence_buffer += token

                yield {
                    "type": "token",
                    "token": token,
                }

                # Check sentence boundaries for immediate speech playback
                parts = SENTENCE_DELIMITER.split(sentence_buffer)
                if len(parts) > 1:
                    sentence_to_speak = parts[0].strip()
                    sentence_buffer = "".join(parts[1:])
                    if sentence_to_speak:
                        # TTS invariant: preserve numbers \d+, only strip bracketed citations
                        clean_sentence = re.sub(r'\[\d+\]|\(\d+\)', '', sentence_to_speak).strip()
                        if clean_sentence:
                            yield {
                                "type": "audio_chunk",
                                "text": clean_sentence,
                            }

            # Flush any remaining text in sentence buffer
            if sentence_buffer.strip():
                clean_sentence = re.sub(r'\[\d+\]|\(\d+\)', '', sentence_buffer).strip()
                if clean_sentence:
                    yield {
                        "type": "audio_chunk",
                        "text": clean_sentence,
                    }

            clean_final = sanitize_final_text(full_content)
            memory.add_episode("assistant", clean_final, session_id=session_id)

            yield {
                "type": "done",
                "response": clean_final,
                "model": active_model,
            }

        finally:
            gc.collect()


engine = CognitiveEngine()
