"""CCM Comparison Script — Retroactively apply CCM rules to a real conversation.

Reads a Claude Code conversation JSONL, segments it into effort phases,
generates summaries for each, and produces comparison metrics.

Usage:
    python scripts/ccm_comparison.py [--no-llm] [--config CONFIG_FILE]

    --no-llm:  Skip LLM summary generation, use placeholder summaries
    --config:  Path to JSON config file with conversation_file and effort_phases
               If not provided, uses the default (d7623174) conversation.
"""

import json
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Default conversation and phases (original analysis)
DEFAULT_CONVERSATION_FILE = Path(
    "C:/Users/Lex/.claude/projects/D--Dev-knowledge-network/"
    "d7623174-b82f-45c9-b73b-8c878ff9d7a9.jsonl"
)

DEFAULT_EFFORT_PHASES = [
    {"id": "dev-agent-context", "start": 1, "end": 15,
     "topic": "Targeted context for dev-agent, model selection, director role"},
    {"id": "session-continuation-tests", "start": 16, "end": 27,
     "topic": "Dev-agent passing tests, QA verification, workflow gap discovery"},
    {"id": "scenario-agent-fix", "start": 28, "end": 40,
     "topic": "Scenario vs story confusion, effort detection problems"},
    {"id": "acceptance-test-mocking", "start": 41, "end": 56,
     "topic": "Real LLM vs mocking debate, technical spec docs"},
    {"id": "worktree-merge-monitor", "start": 57, "end": 77,
     "topic": "Merging worktree branches, monitor server, pipeline observability"},
    {"id": "test-arch-story-review", "start": 78, "end": 118,
     "topic": "Test architect flaws, story reviewer, red-phase fixes"},
    {"id": "ccm-e2e-detection", "start": 119, "end": 132,
     "topic": "Claude Code comparison, headless mode, e2e effort detection"},
    {"id": "stub-problem-detection", "start": 133, "end": 146,
     "topic": "Stub validator gap, explicit vs implicit detection"},
    {"id": "ccm-slice-redesign", "start": 147, "end": 165,
     "topic": "CCM architecture, whitepaper goals, working context tiers"},
    {"id": "cli-implementation", "start": 166, "end": 183,
     "topic": "CLI implementation, effort detection via tools, testing"},
    {"id": "results-planning", "start": 184, "end": 188,
     "topic": "Compaction savings, infinite context vision, slice planning"},
]


def load_config(config_path: str) -> tuple[Path, list[dict]]:
    """Load conversation file and effort phases from a JSON config."""
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    return Path(cfg["conversation_file"]), cfg["effort_phases"]

# CCM constants (from our implementation)
SUMMARY_EVICTION_THRESHOLD = 20
AMBIENT_WINDOW = 10


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def read_conversation(filepath: Path) -> list[dict]:
    """Read all messages from a JSONL conversation file."""
    messages = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                messages.append(obj)
            except json.JSONDecodeError:
                continue
    return messages


def extract_content(msg: dict) -> str:
    """Extract text content from a message object."""
    if "message" in msg:
        c = msg["message"].get("content", "")
    else:
        c = msg.get("content", "")

    if isinstance(c, list):
        parts = []
        for p in c:
            if isinstance(p, dict):
                parts.append(p.get("text", ""))
        return " ".join(parts)
    elif isinstance(c, str):
        return c
    return ""


def get_role(msg: dict) -> str:
    """Extract role from a message object."""
    # Claude Code JSONL uses 'type' at top level for role
    top_type = msg.get("type", "")
    if top_type in ("user", "assistant"):
        return top_type
    # Also check nested message.role
    if "message" in msg:
        return msg["message"].get("role", top_type)
    return msg.get("role", top_type)


def is_user_message(msg: dict) -> bool:
    """Check if message is from a human user."""
    role = get_role(msg)
    content = extract_content(msg)
    return role == "user" and len(content) > 10


def segment_conversation(all_messages: list[dict], effort_phases: list[dict]) -> dict[str, list[dict]]:
    """Segment conversation into effort phases based on user message indices."""
    # First, identify user message positions
    user_msg_positions = []
    for i, msg in enumerate(all_messages):
        if is_user_message(msg):
            user_msg_positions.append(i)

    print(f"Total messages: {len(all_messages)}")
    print(f"User messages: {len(user_msg_positions)}")

    segments = {}
    for phase in effort_phases:
        # Convert 1-based user msg index to 0-based position in user_msg_positions
        start_idx = phase["start"] - 1
        end_idx = phase["end"] - 1

        if start_idx >= len(user_msg_positions):
            print(f"  Warning: Phase {phase['id']} start ({phase['start']}) "
                  f"exceeds user messages ({len(user_msg_positions)})")
            continue

        # Get JSONL line range for this phase
        jsonl_start = user_msg_positions[start_idx]
        jsonl_end = (user_msg_positions[end_idx] if end_idx < len(user_msg_positions)
                     else len(all_messages) - 1)

        # Include all messages (user + assistant) up to the next phase start
        next_phase_start = (user_msg_positions[end_idx + 1]
                           if end_idx + 1 < len(user_msg_positions)
                           else len(all_messages))

        phase_messages = all_messages[jsonl_start:next_phase_start]
        segments[phase["id"]] = phase_messages

    return segments


def generate_summary_llm(effort_id: str, content: str) -> str:
    """Generate a summary using real LLM (like CCM would)."""
    from oi.llm import summarize_effort
    # Truncate to avoid token limits on the summarization call
    max_chars = 12000  # ~3K tokens of context for summarization
    if len(content) > max_chars:
        content = content[:max_chars // 2] + "\n...\n" + content[-max_chars // 2:]
    return summarize_effort(content)


def generate_summary_placeholder(effort_id: str, topic: str) -> str:
    """Generate a placeholder summary (no LLM needed)."""
    return f"Worked on {topic}. Key decisions and outcomes documented."


def run_comparison(use_llm: bool = True, conversation_file: Path = None,
                   effort_phases: list[dict] = None, output_name: str = None):
    """Run the full CCM comparison analysis."""
    conv_file = conversation_file or DEFAULT_CONVERSATION_FILE
    phases = effort_phases or DEFAULT_EFFORT_PHASES
    out_name = output_name or "ccm-comparison-results.json"

    print(f"Reading conversation: {conv_file}")
    all_messages = read_conversation(conv_file)

    total_content = ""
    for msg in all_messages:
        total_content += extract_content(msg) + "\n"
    total_tokens = estimate_tokens(total_content)
    print(f"Total conversation tokens: {total_tokens:,}")
    print()

    # Segment into efforts
    segments = segment_conversation(all_messages, phases)

    # Generate summaries and collect metrics
    print("\n=== Effort Phases ===\n")
    effort_data = []
    for phase in phases:
        eid = phase["id"]
        if eid not in segments:
            continue

        phase_msgs = segments[eid]
        phase_content = "\n".join(extract_content(m) for m in phase_msgs)
        phase_tokens = estimate_tokens(phase_content)

        if use_llm:
            summary = generate_summary_llm(eid, phase_content)
        else:
            summary = generate_summary_placeholder(eid, phase["topic"])

        summary_tokens = estimate_tokens(summary)

        effort_data.append({
            "id": eid,
            "topic": phase["topic"],
            "raw_tokens": phase_tokens,
            "summary": summary,
            "summary_tokens": summary_tokens,
            "msg_count": len(phase_msgs),
        })

        savings = (1 - summary_tokens / phase_tokens) * 100 if phase_tokens > 0 else 0
        print(f"  {eid}:")
        print(f"    Raw: {phase_tokens:,} tokens ({len(phase_msgs)} msgs)")
        print(f"    Summary: {summary_tokens} tokens ({savings:.0f}% savings)")
        print(f"    \"{summary[:120]}...\"")
        print()

    # === Comparison metrics ===
    print("\n" + "=" * 60)
    print("COMPARISON: Traditional vs CCM")
    print("=" * 60)

    total_raw = sum(e["raw_tokens"] for e in effort_data)
    total_summaries = sum(e["summary_tokens"] for e in effort_data)
    avg_summary = total_summaries / len(effort_data) if effort_data else 0

    print(f"\nRaw conversation: {total_tokens:,} tokens")
    print(f"Effort phases: {len(effort_data)}")
    print(f"Total raw (segmented): {total_raw:,} tokens")
    print(f"Total summaries: {total_summaries} tokens")
    print(f"Average summary: {avg_summary:.0f} tokens")

    # Traditional: everything in context (up to 200K)
    traditional_wm = min(total_tokens, 200_000)

    # CCM working memory at conversation end (turn ~188)
    # Simulate eviction: efforts not referenced in last 20 user msgs
    # Phases 1-8 would be evicted (messages 1-146, >20 msgs ago)
    # Phases 9-11 would be active (messages 147-188, within last 41 msgs)
    active_summaries = effort_data[-3:]  # last 3 efforts (within threshold)
    evicted_summaries = effort_data[:-3]

    active_summary_tokens = sum(e["summary_tokens"] for e in active_summaries)
    ambient_tokens = 2000  # ~10 exchanges * ~200 tokens each
    system_prompt_tokens = 1500  # system prompt + tools

    ccm_wm = active_summary_tokens + ambient_tokens + system_prompt_tokens

    print(f"\n--- At conversation end (turn ~188) ---")
    print(f"Traditional working memory: {traditional_wm:,} tokens")
    print(f"CCM working memory: {ccm_wm:,} tokens")
    print(f"  Active summaries ({len(active_summaries)}): {active_summary_tokens} tokens")
    print(f"  Ambient window: {ambient_tokens} tokens")
    print(f"  System prompt + tools: {system_prompt_tokens} tokens")
    print(f"  Evicted (retrievable): {len(evicted_summaries)} efforts")
    print(f"Savings: {(1 - ccm_wm / traditional_wm) * 100:.1f}%")

    # Growth curve data points
    print(f"\n--- Growth Curve (working memory size vs turn) ---")
    print(f"{'Turn':>6} {'Traditional':>12} {'CCM':>8} {'CCM Detail':}")

    cumulative_tokens = 0
    concluded_efforts = []

    for i, phase in enumerate(effort_data):
        cumulative_tokens += phase["raw_tokens"]
        concluded_efforts.append(phase)

        # Simulate turn number at end of this phase
        turn = phases[i]["end"]

        # Traditional: all tokens so far (up to 200K)
        trad = min(cumulative_tokens, 200_000)

        # CCM: active summaries + ambient + system
        # Active = efforts referenced within last 20 turns
        active = [e for j, e in enumerate(concluded_efforts)
                  if turn - phases[j]["end"] < SUMMARY_EVICTION_THRESHOLD]
        evicted = len(concluded_efforts) - len(active)
        active_tok = sum(e["summary_tokens"] for e in active)
        ccm = active_tok + ambient_tokens + system_prompt_tokens

        detail = f"({len(active)} active, {evicted} evicted)"
        print(f"{turn:>6} {trad:>12,} {ccm:>8,} {detail}")

    # Save results
    results = {
        "conversation_file": str(conv_file),
        "total_tokens": total_tokens,
        "effort_count": len(effort_data),
        "efforts": effort_data,
        "comparison": {
            "traditional_wm_at_end": traditional_wm,
            "ccm_wm_at_end": ccm_wm,
            "savings_percent": round((1 - ccm_wm / traditional_wm) * 100, 1),
        },
    }
    output_path = Path(__file__).parent.parent / "docs" / "research" / out_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    return results


if __name__ == "__main__":
    use_llm = "--no-llm" not in sys.argv
    if not use_llm:
        print("Running without LLM (placeholder summaries)\n")

    # Check for --config argument
    config_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]

    if config_path:
        conv_file, phases = load_config(config_path)
        # Derive output name from config filename
        out_name = Path(config_path).stem + "-results.json"
        run_comparison(use_llm=use_llm, conversation_file=conv_file,
                       effort_phases=phases, output_name=out_name)
    else:
        run_comparison(use_llm=use_llm)
