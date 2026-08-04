# sandbox-coldstart-bench

A runnable cold-start benchmark for AI agent sandboxes. Measures Blaxel's
resume-from-standby latency against Modal's create-fresh sandbox, and reports
the full distribution (p50/p95/p99), not just a median.

Most sandbox "comparisons" online are tables someone typed, citing a single
number from a vendor blog. This one you clone and run. If the numbers don't
reproduce on your machine, that's a bug you can open.

## Why this exists

Blaxel markets ~25ms resume-from-standby. That number shows up in half the
sandbox comparison posts on the internet, and every one of them traces back to
the same Blaxel blog post. Nobody re-measured it, and nobody reports what the
tail looks like. Cold-start reputations live in p95/p99, not the median, so
that's the gap this fills.

## Run it (about 5 minutes)

Needs Python 3.11+ (the SDKs don't ship 3.8 wheels).

```bash
git clone <this-repo> && cd sandbox-coldstart-bench
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# on x86_64 macOS without Rust, if cbor2 fails to build:
#   pip install --only-binary=:all: cbor2   # then rerun the line above

cp .env.example .env      # add your Blaxel key (free tier: $200, no card)
python run.py             # 30 Blaxel trials, prints a table + writes charts
```

Longer run, or add Modal as a create-fresh reference point:

```bash
python run.py --n 100                    # tighter tails
python run.py --platforms blaxel,modal   # also benchmark Modal (needs a Modal token)
python run.py --no-plot                  # skip charts (no matplotlib needed)
```

## What it measures

Blaxel's model is resume-from-standby, so the harness decomposes the
developer-visible cold start into parts you can actually reason about:

- **`reconnect`** = the `SandboxInstance.get()` call to reattach to a standby
  sandbox. Basically one network round trip.
- **`cold_exec`** = the first exec right after reconnecting.
- **`cold`** = reconnect + cold_exec, the full thing a developer waits on.
- **`warm`** = an exec on an already-live sandbox. One round trip plus a trivial
  exec, no cold-start in it. This is the network baseline.
- **resume penalty** = `cold_exec − warm`, the standby-resume cost with the
  network subtracted out. This is the number the marketing 25ms can't show you.

Modal is supported as a create-fresh reference point (`--platforms blaxel,modal`),
timed under its own native model. Blaxel resumes a snapshot and Modal builds a
container, so read a comparison as "time until I can run code," not "same thing,
who wins." The default run is Blaxel only.

## Output

- `results/results.json` — full summary plus raw samples
- `results/decomposition.png` — where the cold start goes (network vs resume)
- `results/cdf.png` — cold-start latency CDF
- `results/percentiles.png` — p50/p95/p99 bars

## Caveats

- Raw numbers include your network RTT to each region. Run from a cloud box in
  the platform's region if you want the machine-independent version; the
  `overhead` column already subtracts most of it.
- SDK APIs drift. The exact calls are documented at the top of each file in
  `bench/`. Check them against current docs before trusting a run.
- Default region is Blaxel `us-pdx-1`. Set `--region` to match where you are.

See [WRITEUP.md](WRITEUP.md) for the full method, results, and what they mean.

## Layout

```
run.py               CLI entry point
bench/blaxel_bench.py  Blaxel resume-from-standby harness (async)
bench/modal_bench.py   Modal create-fresh harness
bench/stats.py         percentiles, no numpy needed
bench/plot.py          CDF + percentile charts
```
