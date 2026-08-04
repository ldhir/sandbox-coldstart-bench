"""Percentile stats. No numpy dependency so the harness runs with just an SDK installed."""


def percentile(data, q):
    """Linear-interpolation percentile (matches numpy's default 'linear' method)."""
    if not data:
        return float("nan")
    s = sorted(data)
    if len(s) == 1:
        return float(s[0])
    rank = (q / 100.0) * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def summarize(samples):
    """Return the distribution summary for a list of latency samples (ms)."""
    samples = [x for x in samples if x is not None]
    if not samples:
        return {"n": 0, "min": None, "p50": None, "p95": None,
                "p99": None, "max": None, "mean": None}
    return {
        "n": len(samples),
        "min": round(min(samples), 1),
        "p50": round(percentile(samples, 50), 1),
        "p95": round(percentile(samples, 95), 1),
        "p99": round(percentile(samples, 99), 1),
        "max": round(max(samples), 1),
        "mean": round(sum(samples) / len(samples), 1),
    }


def overhead(cold_summary, warm_summary):
    """Cold-start overhead = cold - warm at each percentile. Isolates platform
    cost from the network round-trip the warm path also pays."""
    out = {}
    for k in ("p50", "p95", "p99"):
        c, w = cold_summary.get(k), warm_summary.get(k)
        out[k] = round(c - w, 1) if (c is not None and w is not None) else None
    return out
