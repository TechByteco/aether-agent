"""
AETHER Interactive Terminal Interface
Rich, modern, visually polished CLI with real-time hardware indicators, memory stats, and voice output.
Fully Windows cp1252 / UTF-8 safe with instant RAM unload controls.
"""

import sys

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from aether.brain.claude_agent import claude_agent
from aether.brain.cognitive_learner import cognitive_learner
from aether.brain.curriculum_learner import curriculum_learner
from aether.brain.engine import engine
from aether.brain.task_engagement import EngagementPersona, task_engagement
from aether.brain.thinking_cortex import thinking_cortex
from aether.config import config
from aether.daemon.heartbeat import heartbeat
from aether.memory.persona import persona
from aether.memory.store import memory
from aether.tools.ambient_listener import ambient_listener
from aether.tools.claude_tools import claude_bash, claude_todos
from aether.tools.guardrails import format_vitals_summary, get_system_vitals
from aether.tools.vision import analyze_image, analyze_live_screen
from aether.tools.voice import voice

console = Console(legacy_windows=False)


def print_banner() -> None:
    v = get_system_vitals()
    m = memory.get_memory_stats()
    voice_status = "[bold green]ON[/bold green]" if voice.enabled else "[dim]OFF[/dim]"
    
    banner_text = (
        f"[bold cyan]AETHER[/bold cyan] [dim]v0.9.0[/dim] - [bold white]Conscious Personal AI Companion & Cognitive Agent[/bold white]\n"
        f"[green]* Local Brain[/green]: [yellow]{config.local_model}[/yellow] (Auto-unloads in {config.keep_alive} | {config.num_threads} Threads)\n"
        f"[blue]* Conscious Memory[/blue]: {m['facts']} facts | {m['episodes']} episodes | {m['heuristics']} rules ({m['disk_size_kb']} KB)\n"
        f"[magenta]* Hardware Guard[/magenta]: RAM {v['ram_used_gb']}G/{v['ram_total_gb']}G ({v['ram_percent']}%) | Voice: {voice_status}\n"
        f"[dim]Commands: /claude, /deliberate, /assimilate, /consolidate, /invariants, /selfplay, /todo, /diff, /memory, /exit[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", expand=False))


def print_claude_banner() -> None:
    v = get_system_vitals()
    todos = claude_todos.list_all()
    pending = sum(1 for t in todos if t["status"] == "pending")
    in_prog = sum(1 for t in todos if t["status"] == "in_progress")
    done = sum(1 for t in todos if t["status"] == "completed")

    banner_text = (
        f"[bold cyan]Claude Code Agent[/bold cyan] [bold white]Architecture[/bold white] | [dim]AETHER v0.9.0[/dim]\n"
        f"[green]* Active Agent Core[/green]: [bold yellow]{claude_agent.resolve_active_model()}[/bold yellow] (Deliberative Thinking & Neuroplastic Learning)\n"
        f"[blue]* Tool Contracts[/blue]: Bash, View, Edit (str_replace), Write, Grep, Find, Todo, Subagents\n"
        f"[magenta]* Task Tracker[/magenta]: {done} completed | {in_prog} in-progress | {pending} pending\n"
        f"[dim]Commands: /deliberate, /assimilate, /consolidate, /invariants, /selfplay, /todo, /diff, /skills, /normal, /exit[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", expand=False))


def display_facts() -> None:
    facts = memory.recall_facts()
    if not facts:
        console.print("[yellow]No facts stored in long-term memory yet.[/yellow]")
        return
    table = Table(title="Conscious Memory - Stored Facts", border_style="cyan")
    table.add_column("Entity", style="cyan bold")
    table.add_column("Attribute", style="yellow")
    table.add_column("Value", style="white")
    table.add_column("Updated", style="dim")
    for f in facts:
        table.add_row(f["entity"], f["attribute"], f["value"], str(f["updated_at"]))
    console.print(table)


def display_memory_stats() -> None:
    stats = memory.get_memory_stats()
    table = Table(title="Conscious Memory Overview", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")
    table.add_row("Total Conversation Episodes", str(stats["episodes"]))
    table.add_row("Structured Knowledge Facts", str(stats["facts"]))
    table.add_row("Higher-Order Insights", str(stats["insights"]))
    table.add_row("Disk Footprint", f"{stats['disk_size_kb']} KB")
    table.add_row("Database Location", str(config.data_dir / "conscious_memory.db"))
    console.print(table)


def on_tool_start(tool_name: str, args: dict) -> None:
    # Clean up tool name for natural display
    clean_name = tool_name.replace("tool_", "").replace("_", " ").title()
    console.print(f"  [dim cyan]>> Researching:[/] [dim yellow]{clean_name}...[/]")


def on_tool_end(tool_name: str, preview: str) -> None:
    pass


def run_cli() -> None:
    is_claude_mode = "--claude" in sys.argv or "--agent" in sys.argv
    if is_claude_mode:
        print_claude_banner()
    else:
        print_banner()

    # Initiate autonomous heartbeat daemon in background
    heartbeat.on_notification = lambda msg: console.print(f"\n[bold magenta]{msg}[/bold magenta]")
    heartbeat.start()

    while True:
        try:
            v = get_system_vitals()
            ram_badge = f"[dim]({v['ram_percent']}% RAM)[/dim]"
            
            prompt_label = "[bold cyan]Claude Agent[/bold cyan]" if is_claude_mode else "[bold green]You[/bold green]"
            user_input = Prompt.ask(f"\n{prompt_label} {ram_badge}")
            clean_input = user_input.strip()

            if not clean_input:
                continue

            # Command dispatcher
            if clean_input.lower() in ("exit", "quit", "/exit"):
                console.print("\n[cyan]AETHER powering down. Memory synced to disk. Goodbye.[/cyan]")
                heartbeat.stop()
                engine.unload_model()
                break
            elif clean_input.lower() in ("/claude", "mode claude"):
                is_claude_mode = True
                print_claude_banner()
                continue
            elif clean_input.lower() in ("/normal", "mode normal", "/aether"):
                is_claude_mode = False
                print_banner()
                continue
            elif clean_input.lower() == "/todo":
                console.print(Panel(Markdown(claude_todos.format_markdown()), title="Claude Task Tracker", border_style="cyan"))
                continue
            elif clean_input.lower().startswith("/todo add"):
                t_text = re.sub(r"^/todo\s+add\s*", "", clean_input, flags=re.IGNORECASE)
                item = claude_todos.add(t_text)
                console.print(f"[green]✓ Added task #{item['id']}:[/green] {item['text']}")
                continue
            elif clean_input.lower() in ("/diff", "diff"):
                d = claude_bash("git diff")
                console.print(Panel(d if d.strip() else "No uncommitted git changes.", title="Git Diff", border_style="cyan"))
                continue
            elif clean_input.lower().startswith("/deliberate"):
                task_p = re.sub(r"^/deliberate\s*", "", clean_input, flags=re.IGNORECASE).strip()
                with console.status("[bold cyan]Executing System 2 Multi-Perspective Deliberation...[/bold cyan]", spinner="dots"):
                    d_res = thinking_cortex.deliberate(task_p)
                console.print(Panel(Markdown(d_res.full_trace), title="[bold cyan]Tree-of-Thought Deliberation[/bold cyan]", border_style="cyan"))
                console.print(Panel(Markdown(d_res.synthesizer_plan), title="[bold green]Synthesized Execution Blueprint[/bold green]", border_style="green"))
                continue
            elif clean_input.lower().startswith("/assimilate"):
                s_name = re.sub(r"^/assimilate\s*", "", clean_input, flags=re.IGNORECASE).strip()
                with console.status(f"[bold cyan]Assimilating skill '{s_name}' into permanent memory...[/bold cyan]", spinner="dots"):
                    a_res = cognitive_learner.assimilate_skill(s_name)
                if a_res.get("success"):
                    console.print(f"[bold green]✓ {a_res.get('summary')}[/bold green]")
                    for r in a_res.get("rules_assimilated", []):
                        console.print(f"  [dim cyan]• Rule #{r['id']}:[/] [white]{r['rule']}[/]")
                else:
                    console.print(f"[bold red]✗ Failed to assimilate:[/] {a_res.get('error')}")
                continue
            elif clean_input.lower() in ("/consolidate", "consolidate"):
                with console.status("[bold cyan]Consolidating episodic memory...[/bold cyan]", spinner="dots"):
                    c_res = cognitive_learner.consolidate_episodes()
                console.print(f"[bold green]✓ {c_res.get('status')}[/bold green] (Facts: {c_res.get('facts_added', 0)}, Insights: {c_res.get('insights_consolidated', 0)})")
                continue
            elif clean_input.lower() in ("/invariants", "invariants"):
                invs = cognitive_learner.get_learned_invariants(limit=15)
                if not invs:
                    console.print("[yellow]No Reflexion error invariants recorded yet.[/yellow]")
                else:
                    table = Table(title="Learned Reflexion Invariants", border_style="red")
                    table.add_column("#", style="cyan bold", width=4)
                    table.add_column("Operational Error Avoidance Rule", style="white")
                    for idx, inv in enumerate(invs, 1):
                        table.add_row(str(idx), inv)
                    console.print(table)
                continue
            elif clean_input.lower().startswith("/selfplay"):
                dom = re.sub(r"^/selfplay\s*", "", clean_input, flags=re.IGNORECASE).strip() or "coding"
                with console.status(f"[bold cyan]Generating autonomous self-play challenge in '{dom}'...[/bold cyan]", spinner="dots"):
                    sp_res = cognitive_learner.run_self_play(dom)
                if sp_res.get("success"):
                    console.print(f"[bold green]✓ Self-Play turn complete![/bold green] Total curated pairs: {sp_res['total_dataset_samples']}")
                    console.print(Panel(sp_res["problem"], title=f"Generated Challenge [{dom}]", border_style="cyan"))
                else:
                    console.print(f"[bold red]✗ Self-play generation failed:[/] {sp_res.get('error')}")
                continue
            elif clean_input.lower().startswith("/engage"):
                obj_text = re.sub(r"^/engage\s*", "", clean_input, flags=re.IGNORECASE).strip()
                if not obj_text:
                    console.print(Panel(Markdown(task_engagement.format_dag_markdown()), title="Active Task Engagement", border_style="cyan"))
                else:
                    dag_md = task_engagement.create_engagement_dag(obj_text)
                    console.print(Panel(Markdown(dag_md), title="[bold green]New Task Engagement DAG Initialized[/bold green]", border_style="green"))
                continue
            elif clean_input.lower() in ("/dag", "dag", "/engagement"):
                console.print(Panel(Markdown(task_engagement.format_dag_markdown()), title="Task Engagement DAG", border_style="cyan"))
                continue
            elif clean_input.lower().startswith("/advance"):
                parts = re.sub(r"^/advance\s*", "", clean_input, flags=re.IGNORECASE).strip().split(maxsplit=1)
                t_id = parts[0] if parts and parts[0] else ""
                r_text = parts[1] if len(parts) > 1 else "Milestone advanced."
                adv_res = task_engagement.advance_task(t_id, result_summary=r_text)
                console.print(f"[bold green]{adv_res}[/bold green]")
                console.print(Panel(Markdown(task_engagement.format_dag_markdown()), title="Updated DAG", border_style="cyan"))
                continue
            elif clean_input.lower().startswith("/persona"):
                p_arg = re.sub(r"^/persona\s*", "", clean_input, flags=re.IGNORECASE).strip().upper()
                if p_arg in EngagementPersona._value2member_map_:
                    msg = task_engagement.set_persona(EngagementPersona(p_arg))
                    console.print(f"[bold green]✓ {msg}[/bold green]")
                else:
                    v_list = ", ".join(list(EngagementPersona._value2member_map_.keys()))
                    console.print(f"Current cognitive posture: **{task_engagement.active_persona.value}**\nUsage: `/persona <{v_list}>`")
                continue
            elif clean_input.lower() in ("/disciplines", "disciplines"):
                discs = curriculum_learner.list_disciplines()
                table = Table(title="8 Frontier Cognitive Disciplines", border_style="cyan")
                table.add_column("Discipline Key", style="cyan bold")
                table.add_column("Title", style="yellow")
                table.add_column("Core Focus", style="white")
                for d in discs:
                    table.add_row(d["key"], d["title"], d["description"][:65] + "...")
                console.print(table)
                continue
            elif clean_input.lower().startswith("/tournament"):
                d_choice = re.sub(r"^/tournament\s*", "", clean_input, flags=re.IGNORECASE).strip() or "distributed_systems"
                with console.status(f"[bold cyan]Running 4-Role Adversarial Tournament in '{d_choice}'...[/bold cyan]", spinner="dots"):
                    t_res = curriculum_learner.run_adversarial_tournament(d_choice)
                console.print(Panel(t_res.problem, title=f"[bold yellow]Challenge: {d_choice}[/bold yellow]", border_style="yellow"))
                console.print(Panel(Markdown(t_res.judge_verdict), title="[bold green]Supreme Judge Verdict & Invariants[/bold green]", border_style="green"))
                continue
            elif clean_input.lower() == "/listen":
                spoken = ambient_listener.listen_and_transcribe()
                if spoken:
                    console.print(f"[bold green]You (Voice):[/] {spoken}")
                    with console.status("[bold cyan]AETHER is thinking...[/bold cyan]", spinner="dots"):
                        reply = engine.process_query(spoken, on_tool_start=on_tool_start, on_tool_end=on_tool_end)
                    console.print()
                    console.print(Panel(Markdown(reply), title="[bold cyan]AETHER[/bold cyan]", border_style="cyan", expand=False))
                continue
            elif clean_input.lower() == "/mic":
                console.print(Panel(ambient_listener.test_microphone(), title="Audio Input Devices", border_style="cyan"))
                continue
            elif clean_input.lower().startswith("/mic "):
                try:
                    chosen_idx = int(clean_input.split()[1])
                    ambient_listener.selected_device_index = chosen_idx
                    console.print(f"[green]Microphone switched to index [{chosen_idx}].[/green]")
                except ValueError:
                    console.print("[red]Invalid index. Usage: /mic <number>[/red]")
                continue
            elif clean_input.lower() == "/voice":
                voice.set_enabled(not voice.enabled)
                status_str = "[green]ENABLED (I will speak out loud)[/green]" if voice.enabled else "[yellow]DISABLED (silent mode)[/yellow]"
                console.print(f"[bold cyan]Voice Speech:[/] {status_str}")
                if voice.enabled:
                    voice.speak_async("Voice speech enabled.")
                continue
            elif clean_input.lower() == "/memory":
                display_memory_stats()
                continue
            elif clean_input.lower() == "/facts":
                display_facts()
                continue
            elif clean_input.lower() == "/profile":
                console.print(Panel(persona.get_user_profile(), title="User Profile (Disk)", border_style="magenta"))
                continue
            elif clean_input.lower() == "/goals":
                console.print(Panel(persona.get_active_goals(), title="Active Goals (Disk)", border_style="yellow"))
                continue
            elif clean_input.lower() == "/vitals":
                console.print(f"[bold green]System Vitals:[/] {format_vitals_summary()}")
                continue
            elif clean_input.lower() == "/unload":
                engine.unload_model()
                console.print("[green][+] Model instantly unloaded from RAM. Memory freed back to Windows.[/green]")
                continue
            elif clean_input.lower().startswith("/screen") or clean_input.lower().startswith("/see"):
                prompt = "What is currently visible on my screen? Summarize the active application, window, and key content."
                parts = clean_input.split(maxsplit=1)
                if len(parts) > 1 and parts[1].strip():
                    prompt = parts[1].strip()
                console.print("[cyan]Capturing screen and analyzing visuals...[/cyan]")
                with console.status("[bold cyan]AETHER Vision Engine analyzing...[/bold cyan]", spinner="dots"):
                    analysis = analyze_live_screen(prompt=prompt)
                console.print(Panel(Markdown(analysis), title="[bold cyan]AETHER Vision[/bold cyan]", border_style="cyan"))
                voice.speak_async(analysis[:250])
                continue
            elif clean_input.lower().startswith("/heartbeat"):
                res = heartbeat.pulse_check()
                console.print(f"[bold magenta]Heartbeat Pulse:[/] {res}")
                continue
            elif clean_input.lower() == "/help":
                if is_claude_mode:
                    print_claude_banner()
                else:
                    print_banner()
                continue

            # Execution block: Claude Mode vs Standard AETHER Mode
            if is_claude_mode:
                def on_thinking(thought_text: str) -> None:
                    console.print()
                    console.print(Panel(
                        Markdown(thought_text),
                        title="[dim cyan]Claude Thinking Process[/dim cyan]",
                        border_style="dim cyan",
                        expand=False
                    ))

                def on_claude_tool_start(tname: str, args: dict) -> None:
                    cname = tname.replace("claude_", "").replace("tool_", "").replace("_", " ").title()
                    console.print(f"  [cyan]● Tool:[/] [yellow]{cname}[/] [dim]({', '.join(f'{k}={repr(v)[:25]}' for k, v in args.items())})[/dim]")

                with console.status("[bold cyan]Claude Agent reasoning...[/bold cyan]", spinner="dots"):
                    response_text, metrics = claude_agent.execute_turn(
                        clean_input,
                        on_thinking=on_thinking,
                        on_tool_start=on_claude_tool_start,
                    )

                console.print()
                title_badge = f"[bold cyan]Claude Code Agent[/bold cyan] [dim]({metrics.duration_secs:.2f}s | {len(metrics.tools_executed)} tools)[/dim]"
                console.print(Panel(
                    Markdown(response_text),
                    title=title_badge,
                    border_style="cyan",
                    expand=False,
                ))
            else:
                # Standard AETHER Mode
                with console.status("[bold cyan]AETHER is thinking...[/bold cyan]", spinner="dots"):
                    response_text = engine.process_query(
                        clean_input,
                        on_tool_start=on_tool_start,
                        on_tool_end=on_tool_end,
                    )

                console.print()
                console.print(Panel(
                    Markdown(response_text),
                    title="[bold cyan]AETHER[/bold cyan]",
                    border_style="cyan",
                    expand=False,
                ))

        except KeyboardInterrupt:
            console.print("\n[yellow]Session paused. Type /exit to quit or continue chatting.[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]Error in agent loop:[/] {str(e)}")


if __name__ == "__main__":
    run_cli()
