# X thread draft

Real numbers from the run. Plain, no hype, no emoji. The hook is that it's
runnable and independent, and that I isolated the resume cost from the network,
which nobody else does.

---

**1/**
Every "best AI sandbox" post lists Blaxel at ~25ms cold-start.

I went looking for where that number came from. It's from Blaxel's own blog, and
nobody re-measured it or reported the tail.

So I did. Runnable benchmark, full distribution, network isolated. https://github.com/ldhir/sandbox-coldstart-bench

**2/**
The problem with most sandbox benchmarks: they measure your wifi.

Laptop to a cloud region is a round trip that can dwarf the cold-start itself. A
raw number is half ISP.

Fix: measure a warm request too and subtract it. What's left is the platform.

**3/**
I broke the cold start into three parts per trial:

reconnect = the get() call to reattach
cold_exec = first exec after reconnect
warm = exec on a live sandbox (pure network baseline)

Then resume cost = cold_exec − warm. Network gone.

**4/**
Result, 30 trials, from a laptop to us-pdx-1:

developer-visible cold start p50 = 307ms
of which:
- 106ms reconnect round trip
- 114ms network baseline
- 85ms actual resume penalty

[decomposition chart]

**5/**
So does 25ms hold up?

The 25ms is the server-side resume. Believable. My isolated penalty is ~85ms and
includes connection setup, so the real engine number could be that low.

But no developer sees 25ms. You talk to the box over a network. You see ~300ms.

**6/**
The 25ms is the engine, not the trip.

In-region you'd see maybe 100ms, not 25, because you still pay a full reconnect
call and the resume lands on the first exec. That's not a knock. It's the gap
between a spec number and what your users feel.

**7/**
Credit where due: the tail is tight. p99 is 349ms, only 14% over the median. No
ugly two-second outliers. Whatever they do for resume is consistent.

**8/**
It's all runnable. Clone, add a key (free tier, no card), `python run.py`. If
your numbers don't match mine, open an issue.

That's the point of shipping code instead of a screenshot. https://github.com/ldhir/sandbox-coldstart-bench
