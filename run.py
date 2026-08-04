#!/usr/bin/env python3
"""Cold-start benchmark runner.

  python run.py                       # both platforms, 30 trials each
  python run.py --n 100               # more trials, tighter tails
  python run.py --platforms blaxel    # one platform only
  python run.py --no-plot             # skip charts (no matplotlib needed)

Results are written to results/results.json and printed as a table. Numbers are
raw wall-clock from this machine; the overhead column subtracts the warm
baseline to isolate platform cost from your network round trip.
"""

import argparse
import json
import os

from bench import stats

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _load_env():
    """Load a local .env if python-dotenv is present. Optional."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _fmt(v):
    return f"{v:.0f}" if isinstance(v, (int, float)) else "-"


# series print order; only those present in the results are shown
SERIES_ORDER = ["cold", "reconnect", "cold_exec", "warm"]


def _row(label, s):
    return (f"{label:11}{_fmt(s['p50']):>8}{_fmt(s['p95']):>8}{_fmt(s['p99']):>8}"
            f"{_fmt(s['min']):>8}{_fmt(s['max']):>8}")


def print_table(platform, summ, ovh):
    n = summ["cold"]["n"]
    print(f"\n=== {platform} (n={n}) ===")
    print(f"{'':11}{'p50':>8}{'p95':>8}{'p99':>8}{'min':>8}{'max':>8}  (ms)")
    for key in SERIES_ORDER:
        if key in summ:
            print(_row(key, summ[key]))
    print(f"{'overhead':11}{_fmt(ovh['p50']):>8}{_fmt(ovh['p95']):>8}"
          f"{_fmt(ovh['p99']):>8}   (cold - warm, network subtracted)")


def main():
    ap = argparse.ArgumentParser(description="Sandbox cold-start benchmark")
    ap.add_argument("--n", type=int, default=30, help="trials per platform")
    ap.add_argument("--platforms", default="blaxel",
                    help="comma-separated: blaxel,modal (default: blaxel)")
    ap.add_argument("--region", default="us-pdx-1", help="Blaxel region")
    ap.add_argument("--memory", type=int, default=2048, help="Blaxel sandbox MB")
    ap.add_argument("--standby-wait", type=float, default=5.0,
                    help="seconds idle before a Blaxel resume trial")
    ap.add_argument("--timeout", type=int, default=30, help="exec timeout (s)")
    ap.add_argument("--no-plot", action="store_true", help="skip charts")
    args = ap.parse_args()

    _load_env()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    wanted = [p.strip() for p in args.platforms.split(",") if p.strip()]

    results = {}
    summaries = {"config": vars(args), "platforms": {}}

    for platform in wanted:
        print(f"\nrunning {platform}...")
        if platform == "blaxel":
            from bench.blaxel_bench import run as blaxel_run
            raw = blaxel_run(args.n, region=args.region, memory=args.memory,
                             standby_wait=args.standby_wait, exec_timeout=args.timeout)
        elif platform == "modal":
            from bench.modal_bench import run as modal_run
            raw = modal_run(args.n, exec_timeout=args.timeout)
        else:
            print(f"  unknown platform '{platform}', skipping")
            continue

        summ = {k: stats.summarize(v) for k, v in raw.items()}
        ovh = stats.overhead(summ["cold"], summ["warm"])
        results[platform] = raw
        summaries["platforms"][platform] = {**summ, "overhead": ovh, "raw": raw}
        print_table(platform, summ, ovh)

    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(summaries, f, indent=2)
    print(f"\nwrote {os.path.join(RESULTS_DIR, 'results.json')}")

    if not args.no_plot and results:
        try:
            from bench.plot import render
            paths = render(results, RESULTS_DIR)
            print("wrote " + ", ".join(paths))
        except ImportError:
            print("matplotlib not installed, skipping charts (--no-plot to silence)")


if __name__ == "__main__":
    main()
