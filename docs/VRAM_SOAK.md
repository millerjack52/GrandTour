# VRAM soak: "out of video memory" in offscreen checks (not a leak)

2026-10-09. A memory investigation only: no frame-time, cost or timing measurement (the owner measures performance).
Tools: `Art/soak_vram.ps1` (the wrapper) and `Art/Unreal/soak_vram.py` (the PIE driver and logger).

## Symptom

`check_mud_variants.py` runs ended "out of video memory" on the 6 GB card, usually after its ~25 HighResShots and 6 buffer
dumps (MUDRUNNER_LESSONS_PLAN MRP follow-ups 2 and 3). At the crash D3D12 reported 26.7 GB of UAV buffers. A bigger texture
pool (`-PoolSize 1500`) did not help.

## Mechanism

- **Residency-set slots, not memory.** Every D3D12 command list alive holds a residency set. The D3DX12 residency library has
  `MAX_NUM_CONCURRENT_CMD_LISTS 1024` (`d3dx12residency.h:34`); when they are all taken, `ResidencySet::Open` returns
  `E_OUTOFMEMORY` (`:240-242`), and `D3D12Residency.h:151` (`VERIFYD3D12RESULT(pSet->Open())`) reports it as out of video memory.
- **Nothing paces the CPU to the GPU offscreen.** `-RenderOffScreen` has no swap chain, and D3D12's end-of-frame wait for the
  previous frame's GPU work only follows a native present. So the CPU can run frames ahead and the command lists stay alive.
- **The camera jumps pile them up.** A camera jump to a new view makes a few very slow frames (streaming, shadow pages,
  shaders); in those frames the command lists alive climb into the thousands (see soak B below: about 3,000 with the jumps
  alone, about 115 with the same captures from one camera). The game in normal play has a swap chain and is not at risk.
- **The 26.7 GB is reserved address space.** The UAV buffer figure counts the GPU-scene's 2 GB reserved buffers; the RHI's own
  split says 18.4 GB of them uncommitted and only 16-33 MB committed. Textures, render targets and the render target pool stay
  flat.

## Soak results (first / peak / last per run)

Counters from `stat dumpnonframe D3D12RHI / D3D12Resources` and `rhi.DumpMemory`, logged every 15-30 s (`Saved/Logs/soak_vram_<tag>.csv`);
"GPU committed" is Windows' GPU Process Memory for the editor (the wrapper's `.external.csv`). MB unless named.

**Soak A**: L_MudVariants, the strip's drive repeated, 10 min, no screenshots, no pacing (3 laps).

| Counter | First | Peak | Last |
|---|---:|---:|---:|
| D3D12 command lists alive | 193 | 197 | 197 |
| Command allocators | 249 | 295 | 295 |
| Reserved buffers committed | 16.3 | 32.7 | 32.7 |
| Reserved buffers uncommitted | 18,416 | 18,416 | 18,399 |
| Render targets | 673 | 705 | 705 |
| Textures | 238 | 240 | 240 |
| GPU committed (Windows) | 304 (loading) | 4,701 | 4,701 |
| Private bytes | 1,271 (loading) | 8,407 | 8,407 |

Flat.

**Soak B**: L_MudVariants, the car parked, the check's 25 HighResShots and 6 buffer dumps, then a 60 s hold. Split runs: `move`
(the 25 camera jumps, no capture), `still` (25 HighResShots from one camera), and `move` with `-Pace`.

| Run | Command lists | Allocators | Reserved committed | GPU committed (Windows) |
|---|---:|---:|---:|---:|
| B (captures + dumps) | 147 / 1,417 / 1,417 | 299 / 4,755 / 4,755 | 32.7 flat | 2,500 / 9,826 / 9,725 |
| B move (jumps only) | 134 / 3,196 / 3,196 | 300 / 6,519 / 6,519 | 32.7 flat | 304 / 10,010 / - |
| B move, rain capture off | 117 / 2,977 / 2,977 | 306 / 6,069 / 6,069 | 32.7 flat | 2,564 / 10,355 / 5,330 |
| B move, virtual shadow maps off | 116 / 3,275 / 3,275 | 364 / 7,583 / 7,583 | 32.7 flat | 304 / 9,229 / 9,222 |
| B still (shots, one camera) | 112 / 115 / 115 | 303 / 303 / 303 | 32.7 flat | 805 / 4,718 / 4,554 |
| B move, `-Pace` | 162 / 162 / 162 | 169 / 169 / 169 | 16.3 flat | 2,454 / 4,472 / 4,462 |

The jumps, not the captures, pile up the command lists; neither the rain capture nor virtual shadow maps is the cause. The paced
run was confounded (a game closed mid-run), hence the K proof below. A run with `D3D12.ResidencyManagement=0` hit a GPU crash at load (exit 3): no workaround there.

**K proof**: `check_mud_variants.py` verbatim through `-Mode K`, pacing from the check itself (GT_CHECK_PACE default), the
logger every 15 s, no game open. Ran to its end (editor exit 0 after 428 s, 27 marks, no device-lost or out-of-memory line),
the drive reached 200 m without the scripted pass, 34 PNG + 21 EXR written, and all 32 of the report's gates (every boolean:
ok, the drive, the slices, MR1-MRP) equal the committed `Art/Export/MudVariants/drive-report.json`.

| Counter | First | Peak | Last | Unpaced B / B move peak |
|---|---:|---:|---:|---:|
| D3D12 command lists alive | 77 | 143 | 143 | 1,417 / 3,196 |
| Command allocators | 74 | 179 | 179 | 4,755 / 6,519 |
| Reserved buffers committed | 32.7 | 32.7 | 32.7 | 32.7 / 32.7 |
| Reserved buffers uncommitted | 18,399 | 18,416 | 18,399 | 18,399 / 18,399 |
| Render targets | 657 | 714 | 714 | 720 / 707 |
| Textures | 235 | 254 | 254 | 241 / 247 |
| GPU committed (Windows) | 4,331 | 4,531 | 4,531 | 9,826 / 10,010 |
| Private bytes | 7,802 | 8,120 | 8,100 | 17,802 / 18,222 |

Flat: the command lists stay a tenth of the slots with all the check's camera jumps and captures (textures +19 MB as the
check's later views stream in). The unpaced check runs before this ended out of video memory (MRP follow-ups 2 and 3).

**Soak C**: L_SnowDrive, its drive (5 m -> 120 m) repeated, 5 min, no screenshots, no pacing, soak A's settings (16 laps,
editor exit 0, no game open).

| Counter | First | Peak | Last |
|---|---:|---:|---:|
| D3D12 command lists alive | 141 | 238 | 238 |
| Command allocators | 205 | 224 | 224 |
| Reserved buffers committed | 32.6 | 32.6 | 32.6 |
| Reserved buffers uncommitted | 18,399 | 18,399 | 18,399 |
| Render targets | 694 | 726 | 726 |
| Textures | 236 | 238 | 238 |
| GPU committed (Windows) | 4,421 | 4,589 | 4,589 |
| Private bytes | 8,055 | 8,240 | 8,226 |

Flat: the command lists reach 238 by 60 s (warm-up) and stay there to the end; allocators settle by 150 s; GPU committed
4,575 at 100 s, 4,589 at the end.

## The fix and its switch

`check_mud_variants.py` waits for the GPU at the top of every tick: `gpu_pace()` reads one pixel of a 1x1 `RTF_RGBA8` render
target on the game world (recreated when its outer is gone, nothing without a game world), and the RHI's read waits for the GPU
to finish everything submitted so far. On by default; `GT_CHECK_PACE=0` turns it off. `soak_vram.py` keeps the same
`gpu_pace()` behind `-Pace` for modes A, B and C; in mode K the check paces and the logger does not pace again.

## Running the soak

`Art/soak_vram.ps1 -Mode A|B|C|K [-Minutes N] [-Tag name]` (it refuses with an editor running, and with GoW, GoWR or FarCry6
open unless `-AllowGame`). PIE 1440x900, `-RenderOffScreen -dx12`, the background throttle off, as the mud and snow checks.

| Mode | What runs |
|---|---|
| A | L_MudVariants, the strip's drive repeated (`-Minutes`, default 10) |
| B | L_MudVariants, the car parked, 25 HighResShots + 6 buffer dumps, then a 60 s hold (`-BKind move` / `still` split it) |
| C | L_SnowDrive, its drive repeated (`-Minutes`, default 5) |
| K | `check_mud_variants.py` itself, pictures and report into `Saved/SoakVRAM/K`, the logger every 15 s |

Switches: `-Pace` (A, B, C: the GPU wait per tick; a no-op in K), `-Off 'gt.Mud.Settle,...'` (console switches at 0, the
bisect), `-Cmds 'a;b'` (run once play starts), `-NoRainCapture`, `-ExtraArgs`, `-ParseOnly` (re-parse a log). For an unpaced
K run, set `$env:GT_CHECK_PACE='0'` first. Output: `Saved/Logs/soak_vram_<tag>.log / .csv / .external.csv` and
`Saved/SoakVRAM/soak-<mode>-report.json` (K: `Saved/SoakVRAM/K/drive-report.json`).

## What it does not measure

- No timing of any kind: no frame times, no stat unit, no CSV profile. Memory and object counters only.
- The GPU wait exists only in the offscreen check (and the soak's `-Pace`); the game itself never paces this way.

## Open

- The ~53 MiB of unreferenced bog arrays (`TA_MS_BogOR`, `TA_MS_BogHeightPOM`, `TA_MS_BogHeightPOM8`, no longer built or read
  since MRP follow-up 3) are still on disk for the owner to delete.
