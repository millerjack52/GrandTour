"""Read-only source inventory; never evaluates exporters or saves purchased files.

Use Blender with --factory-startup --disable-autoexec. Existing asset previews
are extracted as evidence; no new Blender 5.x beauty render is implied.
"""
import array
import bpy
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

source, destination = map(Path, sys.argv[sys.argv.index('--')+1:])
destination.mkdir(parents=True, exist_ok=True)
with source.open('rb') as stream:
    before = hashlib.file_digest(stream, 'sha256').hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
catalogs = {}
for folder in [source.parent, *list(source.parents)[:3]]:
    path = folder/'blender_assets.cats.txt'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line and not line.startswith(('#', 'VERSION')):
                fields = line.split(':', 2)
                if len(fields) == 3: catalogs[fields[0]] = fields[1]


def png(preview, name):
    if not preview: return None
    w, h = preview.image_size
    if not w or not h: return None
    data = array.array('I', (value & 0xffffffff for value in preview.image_pixels)).tobytes()
    raw = b''.join(b'\0'+data[y*w*4:(y+1)*w*4] for y in reversed(range(h)))
    def chunk(kind, body):
        return struct.pack('>I', len(body))+kind+body+struct.pack('>I', zlib.crc32(kind+body)&0xffffffff)
    path = destination/'previews'/(re.sub(r'[^A-Za-z0-9_.-]', '_', name)+'.png')
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+
                     chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    return str(path)


mesh_cache = {}
objects = []
tree_pattern = re.compile(r'tree|pine|spruce|birch|oak|willow|palm|conifer', re.I)
for obj in bpy.data.objects:
    if obj.type not in ('MESH', 'CURVE', 'EMPTY'): continue
    catalog = catalogs.get(str(obj.asset_data.catalog_id), '') if obj.asset_data else ''
    collections = [c.name for c in obj.users_collection]
    candidate = bool(tree_pattern.search(obj.name+' '+catalog+' '+' '.join(collections)))
    row = {'name':obj.name, 'type':obj.type, 'asset_marked':bool(obj.asset_data),
           'catalog':catalog, 'collections':collections, 'tree_candidate':candidate,
           'data_name':obj.data.name if obj.data else None,
           'dimensions':list(obj.dimensions), 'scale':list(obj.scale),
           'materials':[s.material.name if s.material else None for s in obj.material_slots],
           'modifiers':[{'name':m.name, 'type':m.type,
                         'node_group':m.node_group.name if m.type=='NODES' and m.node_group else None,
                         'viewport':m.show_viewport, 'render':m.show_render} for m in obj.modifiers],
           'animation_data':bool(obj.animation_data)}
    if obj.type == 'MESH':
        key = obj.data.name
        if key not in mesh_cache:
            mesh = obj.data; mesh.calc_loop_triangles()
            coords = array.array('f', [0.]*(len(mesh.vertices)*3)); mesh.vertices.foreach_get('co', coords)
            indices = array.array('i', [0]*len(mesh.loops)); mesh.loops.foreach_get('vertex_index', indices)
            sizes = array.array('i', [0]*len(mesh.polygons)); mesh.polygons.foreach_get('loop_total', sizes)
            mesh_cache[key] = {'vertices':len(mesh.vertices), 'polygons':len(mesh.polygons),
                              'base_triangles':len(mesh.loop_triangles), 'uvs':[uv.name for uv in mesh.uv_layers],
                              'geometry_hash':hashlib.sha256(coords.tobytes()+indices.tobytes()+sizes.tobytes()).hexdigest()}
        row.update(mesh_cache[key])
    if candidate: row['preview'] = png(obj.preview, obj.name)
    objects.append(row)

collections = []
for collection in bpy.data.collections:
    catalog = catalogs.get(str(collection.asset_data.catalog_id), '') if collection.asset_data else ''
    collections.append({'name':collection.name,'asset_marked':bool(collection.asset_data),
                        'catalog':catalog,'objects':[obj.name for obj in collection.objects],
                        'children':[c.name for c in collection.children]})

materials = []
for mat in bpy.data.materials:
    materials.append({'name':mat.name,'nodes':sorted({n.bl_idname for n in mat.node_tree.nodes}) if mat.node_tree else [],
                      'images':[n.image.name for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if mat.node_tree else []})
images = [{'name':im.name,'path':im.filepath,'packed':bool(im.packed_file),'size':list(im.size)} for im in bpy.data.images]
with source.open('rb') as stream:
    after = hashlib.file_digest(stream, 'sha256').hexdigest()
assert before == after
report = {'source':str(source),'sha256':before,'source_unchanged':True,'file_version':list(bpy.data.version),
          'reader_version':bpy.app.version_string,'objects':objects,'collections':collections,
          'materials':materials,'images':images,'limits':'Base meshes only; procedural modifiers not applied. Embedded previews are source thumbnails, not new Unreal renders.'}
(destination/'inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TREE_INVENTORY_OK',source.name,len(objects),sum(o['tree_candidate'] for o in objects),flush=True)
