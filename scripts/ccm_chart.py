"""Generate CCM comparison chart from results data.

Produces a growth curve chart showing Traditional vs CCM working memory
size as conversation progresses.

Usage:
    python scripts/ccm_chart.py
"""

import json
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not installed. Install with: pip install matplotlib")
    print("Generating text-based chart instead.\n")


def load_results() -> dict:
    results_path = Path(__file__).parent.parent / "docs" / "research" / "ccm-comparison-results.json"
    with open(results_path, encoding="utf-8") as f:
        return json.load(f)


def text_chart(results: dict):
    """ASCII art growth curve."""
    efforts = results["efforts"]
    phases = [
        {"end": 15}, {"end": 27}, {"end": 40}, {"end": 56}, {"end": 77},
        {"end": 118}, {"end": 132}, {"end": 146}, {"end": 165}, {"end": 183}, {"end": 188},
    ]

    # CCM constants
    EVICTION_THRESHOLD = 20
    ambient = 2000
    sys_prompt = 1500

    cumulative = 0
    concluded = []
    rows = []

    for i, effort in enumerate(efforts):
        cumulative += effort["raw_tokens"]
        concluded.append(effort)
        turn = phases[i]["end"]
        trad = min(cumulative, 200_000)

        active = [e for j, e in enumerate(concluded)
                  if turn - phases[j]["end"] < EVICTION_THRESHOLD]
        active_tok = sum(e["summary_tokens"] for e in active)
        ccm = active_tok + ambient + sys_prompt
        rows.append((turn, trad, ccm, effort["id"]))

    # Extrapolate to 500K and 2M
    for extra_tokens, label in [(500_000, "500K extrapolated"), (2_000_000, "2M extrapolated")]:
        turn = int(188 * (extra_tokens / 138_000))
        trad = min(extra_tokens, 200_000)
        # CCM stays bounded: ~2 active summaries at any time
        ccm = 400 + ambient + sys_prompt
        rows.append((turn, trad, ccm, label))

    print("=" * 70)
    print("GROWTH CURVE: Working Memory Size vs Conversation Progress")
    print("=" * 70)
    print(f"{'Turn':>6} {'Traditional':>12} {'CCM':>8} {'Ratio':>8}  Effort")
    print("-" * 70)
    for turn, trad, ccm, name in rows:
        ratio = f"{trad/ccm:.0f}x"
        bar_trad = "#" * min(int(trad / 3000), 50)
        bar_ccm = "=" * min(int(ccm / 3000), 50)
        print(f"{turn:>6} {trad:>12,} {ccm:>8,} {ratio:>8}  {name}")
        print(f"       Trad: {bar_trad}")
        print(f"       CCM:  {bar_ccm}")
    print()

    comp = results["comparison"]
    print(f"Final savings: {comp['savings_percent']}%")
    print(f"Traditional at end: {comp['traditional_wm_at_end']:,} tokens")
    print(f"CCM at end: {comp['ccm_wm_at_end']:,} tokens")


def matplotlib_chart(results: dict):
    """Generate publication-quality chart."""
    efforts = results["efforts"]
    phases = [
        {"end": 15}, {"end": 27}, {"end": 40}, {"end": 56}, {"end": 77},
        {"end": 118}, {"end": 132}, {"end": 146}, {"end": 165}, {"end": 183}, {"end": 188},
    ]

    EVICTION_THRESHOLD = 20
    ambient = 2000
    sys_prompt = 1500

    turns = [0]
    trad_vals = [0]
    ccm_vals = [0]

    cumulative = 0
    concluded = []

    for i, effort in enumerate(efforts):
        cumulative += effort["raw_tokens"]
        concluded.append(effort)
        turn = phases[i]["end"]
        trad = min(cumulative, 200_000)

        active = [e for j, e in enumerate(concluded)
                  if turn - phases[j]["end"] < EVICTION_THRESHOLD]
        active_tok = sum(e["summary_tokens"] for e in active)
        ccm = active_tok + ambient + sys_prompt

        turns.append(turn)
        trad_vals.append(trad)
        ccm_vals.append(ccm)

    # Extrapolate
    for extra_tokens in [200_000, 500_000, 1_000_000, 2_000_000]:
        turn = int(188 * (extra_tokens / 138_000))
        trad = min(extra_tokens, 200_000)
        ccm = 400 + ambient + sys_prompt
        turns.append(turn)
        trad_vals.append(trad)
        ccm_vals.append(ccm)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(turns, trad_vals, 'r-o', linewidth=2, markersize=6,
            label='Traditional (full context)', color='#e74c3c')
    ax.plot(turns, ccm_vals, 'b-s', linewidth=2, markersize=6,
            label='CCM (bounded working memory)', color='#2ecc71')

    # Fill area between
    ax.fill_between(turns, ccm_vals, trad_vals, alpha=0.15, color='#e74c3c')

    # 200K limit line
    ax.axhline(y=200_000, color='#e74c3c', linestyle='--', alpha=0.5,
               label='200K context limit (hard cap)')

    # Annotations
    ax.annotate('97.1% savings\nat 138K tokens',
                xy=(188, 4076), xytext=(220, 30000),
                arrowprops=dict(arrowstyle='->', color='#2ecc71'),
                fontsize=10, color='#2ecc71', fontweight='bold')

    ax.annotate('Context overflow\n(lossy compaction)',
                xy=(turns[-2], 200_000), xytext=(turns[-2]-200, 170000),
                fontsize=9, color='#e74c3c', alpha=0.7)

    ax.set_xlabel('Conversation Turn (user messages)', fontsize=12)
    ax.set_ylabel('Working Memory Size (tokens)', fontsize=12)
    ax.set_title('Conclusion-Triggered Compaction: Working Memory Growth',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()

    output_path = Path(__file__).parent.parent / "docs" / "research" / "ccm-growth-curve.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    plt.close()


if __name__ == "__main__":
    results = load_results()
    text_chart(results)
    if HAS_MPL:
        matplotlib_chart(results)
