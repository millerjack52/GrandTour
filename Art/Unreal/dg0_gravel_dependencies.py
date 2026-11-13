"""Deformable gravel DG0 item 1 (docs/DEFORMABLE_GRAVEL_PLAN.md): the study's asset dependency list, from the asset
registry (not guessed). Every package under the study's two folders, followed recursively through their hard and soft
package dependencies; /Script and /Engine packages are listed by name only (code and engine content), /Game packages are
classified as the study's own, shared (outside the two folders) or Benmore-named. Writes
Art/Export/DeformableGravel/dg0-dependencies.json. Run with the pythonscript commandlet (-NullRHI)."""
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DeformableGravel/dg0-dependencies.json'
ROOTS = ['/Game/GrandTour/ArtTests/DeformableGravel', '/Game/GrandTour/ArtTests/GravelRoad']
reg = u.AssetRegistryHelpers.get_asset_registry()
report = {'ok': False}
try:
    reg.scan_paths_synchronous(ROOTS + ['/Game/GrandTour'], True)
    opts = u.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
                                            include_searchable_names=False, include_soft_management_references=False,
                                            include_hard_management_references=False)
    seeds = []
    for r in ROOTS:
        seeds += sorted({str(a.package_name) for a in reg.get_assets_by_path(r, recursive=True)})
    seen, edges, queue = set(), {}, list(seeds)
    while queue:
        pkg = queue.pop()
        if pkg in seen:
            continue
        seen.add(pkg)
        deps = sorted({str(d) for d in (reg.get_dependencies(pkg, opts) or [])})
        edges[pkg] = deps
        for d in deps:
            if d.startswith('/Game/') and d not in seen:
                queue.append(d)
    every = set(seen)
    for deps in edges.values():
        every.update(deps)

    def kind(p):
        if p.startswith('/Script/'):
            return 'code'
        if p.startswith('/Engine/') or not p.startswith('/Game/'):
            return 'engine'
        if 'benmore' in p.lower():
            return 'benmore'
        if any(p == r or p.startswith(r + '/') for r in ROOTS):
            return 'study'
        return 'shared'
    groups = {}
    for p in sorted(every):
        groups.setdefault(kind(p), []).append(p)
    referenced_by = {}
    for src, deps in edges.items():
        for d in deps:
            if kind(d) in ('shared', 'benmore'):
                referenced_by.setdefault(d, []).append(src)
    report.update(ok=True, roots=ROOTS, seeds=seeds, counts={k: len(v) for k, v in groups.items()}, groups=groups,
                  shared_referenced_by={k: sorted(v) for k, v in sorted(referenced_by.items())},
                  edges={k: [d for d in v if not d.startswith('/Script/')] for k, v in sorted(edges.items()) if k.startswith('/Game/')})
except Exception as e:
    import traceback
    report['error'] = traceback.format_exc()
OUT.write_text(json.dumps(report, indent=2))
print('DG0_DEPS_DONE ok=%s' % report['ok'])
