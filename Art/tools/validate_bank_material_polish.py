"""Offline integrity checks; does not claim a new in-engine visual pass."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/'Saved/LidarAuthoringQA/VP2Materials'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
backup=read(QA/'backup.json');installed=read(QA/'final-install.json')
expected=set(installed['changed_packages']);changed=[]
for relative,original in backup['sha256'].items():
    assert (ROOT/relative).is_file(),relative
    if sha(ROOT/relative)!=original:changed.append(relative)
assert set(changed)==expected,(changed,expected)
for name,info in installed['graphs'].items():
    path=ROOT/'Content/GrandTour/ArtTests/LidarStudy/FirstSection'/(name+'.uasset')
    assert sha(path)==info['sha256'],name+' changed after install'
sources=['Art/Unreal/lidar_bank_material_polish.py','Art/Unreal/run_bank_material_polish.py',
         'Art/Unreal/lidar_bank_ground_material.py','Art/Unreal/lidar_first_section.py',
         'Art/Unreal/perceived_detail_materials.py','Art/Unreal/fern_floor.py',
         'Art/tools/bank_material_review.py','Art/tools/package_bank_material_review.py',
         'Art/tools/validate_bank_material_polish.py']
for source in sources:ast.parse((ROOT/source).read_text(encoding='utf-8-sig'),filename=source)
log=ROOT/'Saved/Logs/LidarSection-vp2-b1.log'
errors=[line for line in log.read_text(errors='replace').splitlines() if any(s in line for s in ['Failed to compile Material','Default Material will be used','missing usage flag','Fatal error'])]
assert not errors,errors
validity_path=QA/'vp2-b1-validity.json'
validity=read(validity_path) if validity_path.exists() else {}
capture_status=('COMPLETED: inspect screenshots and timing evidence separately' if validity.get('completed')
                else 'INCOMPLETE: '+validity.get('reason','No completed final capture recorded'))
record=dict(ok=True,kind='Offline package integrity and Python syntax; not a completed final visual capture',
            changed_packages=changed,protected_files_checked=len(backup['sha256'])-len(changed),
            unchanged_map_meshes_textures_collision_config=True,
            installed_local_plant_hash=installed['local'],installed_outside_plant_hash=installed['outside'],
            source_sha256={p:sha(ROOT/p) for p in sources},
            final_runtime_material_fallbacks=errors,
            final_runtime_capture=capture_status,
            visual_acceptance='PENDING',performance_acceptance='PENDING',
            limitations='Installation snapshot checks passed in Unreal. Log checks alone do not establish visual quality or performance acceptance; inspect completed capture evidence separately.')
(QA/'file-validation.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
