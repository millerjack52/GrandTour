"""Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md items 1, 3 and 4), shared by the rendered drive checks
(check_mud_variants.py, check_deformable_gravel.py, check_live_mud_drive.py, check_wheel_spray.py).

- The fixed time step comes from the wrappers' command line (-UseFixedTimeStep -FPS=60: FEngineLoop::PreInit sets FApp's fixed delta,
  UEngine::UpdateTimeAndHandleMaxTickRate steps every frame by it, the editor's Play In Editor included). Gate.tick records the play
  world's delta seconds; Gate.report() says whether the first 300 after start_dt() were all 1/60 +- 1e-4.
- Scene rendering is off unless a capture needs it: Gate.set() drives the ShowFlag.Rendering console variable for every viewport; a
  check asks Gate.ready() before a picture or a GPU read (rendering on, then true after `warm` frames) and Gate.expect() after its
  HighResShot, and calls Gate.idle() once a tick, which turns rendering off when no capture is waiting for its file.
  GT_CHECK_RENDER_ALWAYS=1 keeps rendering on throughout (the owner's switch, for watching a drive).
- Gate.on is also when the per-tick GPU wait (docs/VRAM_SOAK.md) runs: with no scene rendered there is nothing to pile up.
Wall-clock duration and frame rate are reported as a pipeline measure only.
"""
import os
import time
from pathlib import Path

import unreal as u

ALWAYS = os.environ.get('GT_CHECK_RENDER_ALWAYS', '0').strip() == '1'
FIXED_DT = 1.0 / 60.0


class Gate:
    def __init__(self, warm=30):
        self.warm = warm
        self.on = None
        self.on_frame = 0
        self.frame = 0
        self.frames_on = 0
        self.windows = 0
        self.pending = []          # (path, request time, give-up frame)
        self.wall0 = time.monotonic()
        self.dts = []
        self.dt_on = False
        self.dt_frames = 300
        self.want = -10

    def tick(self, world):
        """Once a tick: the frame count, the rendered frames and (after start_dt) the world's delta seconds."""
        self.frame += 1
        if self.on:
            self.frames_on += 1
        if self.dt_on and world is not None and len(self.dts) < self.dt_frames:
            try:
                self.dts.append(float(u.GameplayStatics.get_world_delta_seconds(world)))
            except Exception:      # noqa: BLE001 - a world being torn down
                pass

    def start_dt(self):
        self.dt_on = True

    def set(self, world, pc, on):
        on = bool(on) or ALWAYS
        if world is None or on == self.on:
            return
        try:
            u.SystemLibrary.execute_console_command(world, 'ShowFlag.Rendering %d' % (1 if on else 0), pc)
        except Exception:      # noqa: BLE001 - a world being torn down (a Play In Editor restart)
            return
        self.on = on
        self.on_frame = self.frame
        if on:
            self.windows += 1

    def ready(self, world, pc, warm=None):
        """Rendering on (turned on now if it was off); true once it has been on for `warm` frames (30 by default)."""
        self.set(world, pc, True)
        self.want = self.frame
        return self.frame - self.on_frame >= (self.warm if warm is None else warm)

    def expect(self, path, frames=600):
        """A capture just issued: rendering stays on until a file named after it (its stem, any suffix) is newer than now."""
        self.pending.append((Path(path), time.time(), self.frame + frames))

    def capturing(self):
        keep = []
        for p, t, f in self.pending:
            done = p.parent.exists() and any(q.stat().st_mtime >= t - 1.0 for q in p.parent.glob(p.stem + '*'))
            if not done and self.frame < f:
                keep.append((p, t, f))
        self.pending = keep
        return bool(keep)

    def idle(self, world, pc, keep=False):
        """Once a tick: rendering off when nothing needs it - no capture waiting for its file, no ready() asked this tick or the last,
        and the caller's keep (its capture window) false."""
        if not keep and not self.capturing() and self.frame - self.want > 1:
            self.set(world, pc, False)

    def report(self):
        dts = list(self.dts)
        ok = bool(dts) and all(abs(d - FIXED_DT) <= 1e-4 for d in dts)
        wall = time.monotonic() - self.wall0
        return dict(fixed_dt=dict(ok=ok, frames=len(dts), asked=round(FIXED_DT, 6), min=round(min(dts), 6) if dts else None,
                                  max=round(max(dts), 6) if dts else None),
                    render=dict(always=ALWAYS, windows=self.windows, frames=self.frame, frames_rendered=self.frames_on),
                    pipeline=dict(wall_s=round(wall, 1), frames=self.frame, fps=round(self.frame / max(wall, 1e-3), 2),
                                  note='the check run\'s own wall clock and frame rate (tooling), not game performance'))
