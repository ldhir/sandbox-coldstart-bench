"""Modal cold-start harness (reference point).

Modal's native model is create-fresh: each sandbox is a new gVisor container.
The comparable cold-start is create + first exec. We also take a warm sample
(second exec on the same live sandbox) so the number is subtracted the same way
as Blaxel's.

Fair-framing caveat, stated loudly in the writeup: Blaxel's cold path is
resume-from-snapshot, Modal's is create-fresh. These are different lifecycle
operations. We compare each platform under its own native model, which is what a
developer actually experiences, and isolate the network with warm subtraction.

SDK surface used (verify against current docs before a real run):
  app = modal.App.lookup(name, create_if_missing=True)
  sb  = modal.Sandbox.create(app=app, image=modal.Image.debian_slim())
  p   = sb.exec("bash", "-c", "echo ok", timeout=N); p.stdout.read(); p.wait()
  sb.terminate()
Auth comes from `modal token new` / MODAL_TOKEN_ID + MODAL_TOKEN_SECRET.
"""

import time

TRIVIAL = ("bash", "-c", "echo ok")


def _exec(sb, exec_timeout):
    p = sb.exec(*TRIVIAL, timeout=exec_timeout)
    p.stdout.read()
    p.wait()


def run(n, exec_timeout=30, app_name="coldstart-bench", log=print):
    """Blocking entry point. Returns {'cold': [ms...], 'warm': [ms...]}."""
    import modal

    app = modal.App.lookup(app_name, create_if_missing=True)
    image = modal.Image.debian_slim()

    cold, warm = [], []
    for i in range(n):
        # cold: create a fresh sandbox + first exec
        t0 = time.perf_counter()
        sb = modal.Sandbox.create(app=app, image=image)
        _exec(sb, exec_timeout)
        cold.append((time.perf_counter() - t0) * 1000)

        # warm: second exec on the same live sandbox
        t0 = time.perf_counter()
        _exec(sb, exec_timeout)
        warm.append((time.perf_counter() - t0) * 1000)

        sb.terminate()
        log(f"  modal trial {i + 1}/{n}: cold={cold[-1]:.0f}ms warm={warm[-1]:.0f}ms")

    return {"cold": cold, "warm": warm}
