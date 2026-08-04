"""Blaxel cold-start harness.

Blaxel's model is resume-from-standby: a sandbox scales to standby after a
short idle, then resumes from a snapshot when you reconnect. That resume is the
operation Blaxel markets at ~25ms. We measure the developer-visible thing:
time from reconnect to a completed exec.

  cold  = SandboxInstance.get(name)  ->  first exec completes   (resume path)
  warm  = exec on an already-live sandbox                        (network + exec only)

cold - warm isolates the resume cost from the laptop-to-cloud round trip.

SDK surface used (verify against current docs before a real run — SDKs drift):
  from blaxel.core import SandboxInstance
  await SandboxInstance.create_if_not_exists({name, image, memory, region})
  await SandboxInstance.get(name)                 # reconnect = resume from standby
  await sandbox.process.exec({command, wait_for_completion, timeout})
Auth is read from env: BL_WORKSPACE, BL_API_KEY.
"""

import asyncio
import time

TRIVIAL = "echo ok"


async def _exec(sandbox, timeout):
    return await sandbox.process.exec({
        "command": TRIVIAL,
        "wait_for_completion": True,
        "timeout": timeout,
    })


async def _run_async(n, region, memory, standby_wait, exec_timeout, name, log):
    from blaxel.core import SandboxInstance

    sandbox = await SandboxInstance.create_if_not_exists({
        "name": name,
        "image": "blaxel/base-image:latest",
        "memory": memory,
        "region": region,
    })
    await _exec(sandbox, exec_timeout)  # ensure it's provisioned before timing

    # Series captured per trial:
    #   warm       exec on the live sandbox            (1 network RTT + exec)
    #   reconnect  SandboxInstance.get() on its own    (1 RTT + resume trigger/wait)
    #   cold_exec  first exec right after reconnect    (1 RTT + exec, post-resume)
    #   cold       reconnect + cold_exec               (total developer-visible resume)
    # Decomposing cold answers the obvious objection: is the overhead real resume
    # cost, or just the extra round trip the reconnect adds over the warm path?
    cold, warm, reconnect, cold_exec = [], [], [], []
    for i in range(n):
        # warm: sandbox is live, exec immediately -> network + exec baseline
        t0 = time.perf_counter()
        await _exec(sandbox, exec_timeout)
        warm.append((time.perf_counter() - t0) * 1000)

        # let it fall to standby so the next reconnect is a real resume
        await asyncio.sleep(standby_wait)

        # cold, decomposed: time the reconnect and the first exec separately
        t0 = time.perf_counter()
        resumed = await SandboxInstance.get(name)
        t_get = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        await _exec(resumed, exec_timeout)
        t_exec = (time.perf_counter() - t1) * 1000

        reconnect.append(t_get)
        cold_exec.append(t_exec)
        cold.append(t_get + t_exec)
        sandbox = resumed

        log(f"  blaxel trial {i + 1}/{n}: cold={cold[-1]:.0f}ms "
            f"(reconnect={t_get:.0f} + exec={t_exec:.0f}) warm={warm[-1]:.0f}ms")

    return {"cold": cold, "warm": warm,
            "reconnect": reconnect, "cold_exec": cold_exec}


def run(n, region="us-pdx-1", memory=2048, standby_wait=5.0,
        exec_timeout=30, name="coldstart-bench", log=print):
    """Blocking entry point. Returns {'cold': [ms...], 'warm': [ms...]}."""
    return asyncio.run(
        _run_async(n, region, memory, standby_wait, exec_timeout, name, log)
    )
