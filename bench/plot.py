"""Charts. Optional — imported only when matplotlib is installed and --no-plot
is not set. Produces a cold-start CDF and a p50/p95/p99 bar chart."""

import os

COLORS = {"blaxel": "#FF6B4A", "modal": "#7B61FF"}


def _cdf(ax, samples, label, color):
    s = sorted(samples)
    n = len(s)
    ys = [(i + 1) / n for i in range(n)]
    ax.step(s, ys, where="post", label=label, color=color, linewidth=2)


def render(results, out_dir):
    """results: {platform: {'cold': [...], 'warm': [...]}}. Writes two PNGs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    platforms = list(results.keys())

    # 1. CDF of cold-start latency
    fig, ax = plt.subplots(figsize=(8, 5))
    for p in platforms:
        _cdf(ax, results[p]["cold"], p, COLORS.get(p, None))
    ax.set_xlabel("cold-start latency (ms)")
    ax.set_ylabel("fraction of trials")
    ax.set_title("Cold-start latency CDF")
    ax.legend()
    ax.grid(True, alpha=0.3)
    cdf_path = os.path.join(out_dir, "cdf.png")
    fig.tight_layout()
    fig.savefig(cdf_path, dpi=150)
    plt.close(fig)

    # 2. Percentile bars (p50/p95/p99 of cold-start)
    from .stats import percentile
    pcts = [50, 95, 99]
    fig, ax = plt.subplots(figsize=(8, 5))
    width = 0.8 / max(len(platforms), 1)
    for i, p in enumerate(platforms):
        vals = [percentile(results[p]["cold"], q) for q in pcts]
        xs = [j + i * width for j in range(len(pcts))]
        ax.bar(xs, vals, width=width, label=p, color=COLORS.get(p, None))
    ax.set_xticks([j + width * (len(platforms) - 1) / 2 for j in range(len(pcts))])
    ax.set_xticklabels([f"p{q}" for q in pcts])
    ax.set_ylabel("cold-start latency (ms)")
    ax.set_title("Cold-start tail latency")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    bar_path = os.path.join(out_dir, "percentiles.png")
    fig.tight_layout()
    fig.savefig(bar_path, dpi=150)
    plt.close(fig)

    paths = [cdf_path, bar_path]

    # 3. Decomposition — only when the Blaxel run recorded reconnect/cold_exec.
    # Breaks the developer-visible cold start into network vs real resume cost.
    for p in platforms:
        r = results[p]
        if "reconnect" in r and "cold_exec" in r:
            paths.append(_decompose(plt, r, p, out_dir))
    return paths


def _decompose(plt, r, platform, out_dir):
    """Horizontal stacked bar: reconnect RTT + exec baseline + resume penalty."""
    from .stats import percentile
    reconnect = percentile(r["reconnect"], 50)
    warm = percentile(r["warm"], 50)
    resume = max(percentile(r["cold_exec"], 50) - warm, 0)

    segs = [
        ("reconnect (network round trip)", reconnect, "#9aa0a6"),
        ("exec baseline (network + exec)", warm, "#c8ccd0"),
        ("resume penalty (isolated)", resume, "#FF6B4A"),
    ]
    fig, ax = plt.subplots(figsize=(9, 2.6))
    left = 0
    for label, val, color in segs:
        ax.barh(0, val, left=left, color=color, edgecolor="white", label=label)
        if val > 12:
            ax.text(left + val / 2, 0, f"{val:.0f}ms", ha="center", va="center",
                    fontsize=10, color="#222")
        left += val
    total = left
    ax.set_xlim(0, total * 1.02)
    ax.set_yticks([])
    ax.set_xlabel("developer-visible cold-start latency (ms), p50")
    ax.set_title(f"{platform}: where the cold start goes  (total {total:.0f}ms)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=3, frameon=False)
    path = os.path.join(out_dir, "decomposition.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
