"""Build local tree catalogue from read-only Blender inventories and native previews."""
import collections
import html
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

R=Path('C:/GrandTour'); O=R/'Art/Export/TreeInventory'
PACKS={
    'flora-main':'Flora Paint / main',
    'flora-update':'Flora Paint / tree update',
    'trees-library':'Trees Assets Library',
    'lazy-assets':'Lazy Forest',
    'stylized-assets':'Stylized Forest Generator',
    'grasspaint-assets':'GrassPaint companion library',
}


def sheet(rows,path,title,columns=6):
    cw,ch=220,280
    canvas=Image.new('RGB',(columns*cw,70+math.ceil(len(rows)/columns)*ch),'#1c292d')
    draw=ImageDraw.Draw(canvas); font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    draw.text((12,10),title,font=font,fill='white')
    draw.text((12,36),'Supplied asset previews; not Unreal renders. Triangle counts are base mesh, before modifiers.',font=font,fill='#b8c9c1')
    for i,row in enumerate(rows):
        x,y=i%columns*cw,70+i//columns*ch
        if row.get('preview'):
            im=Image.open(row['preview']).convert('RGBA'); im.thumbnail((208,200),Image.Resampling.LANCZOS)
            canvas.paste(im,(x+(cw-im.width)//2,y),im)
        draw.text((x+5,y+203),row['name'].replace('FP_Tree_','FP_'),font=font,fill='white')
        draw.text((x+5,y+226),f"{row['base_triangles']:,} tris"+(' / CURRENT' if row.get('current') else ''),font=font,fill='#cfbd87')
        draw.text((x+5,y+249),row.get('pack_label',''),font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13),fill='#b8c9c1')
    canvas.save(path,quality=94)


def main():
    reports={p.parent.name:json.loads(p.read_text()) for p in O.glob('*/inventory.json')}
    rows=[]; summaries=[]
    for key,label in PACKS.items():
        if key not in reports: continue
        data=reports[key]
        assets=[o for o in data['objects'] if o['tree_candidate'] and o['type']=='MESH' and o['asset_marked']]
        # Tree collection membership can include ground objects; canonical asset names/catalogs
        # are retained here, with source scene objects listed separately in raw reports.
        for obj in assets:
            obj=dict(obj,pack=key,pack_label=label,source=data['source'],
                     current=key=='flora-main' and obj['name'] in ('FP_Tree_B_001','FP_Tree_D_001'))
            obj['kind']='log' if key=='stylized-assets' and obj['name'] in [f'Trees_Assets_{i:03d}' for i in range(34,40)] else 'standing tree'
            rows.append(obj)
        unique=len({o['geometry_hash'] for o in assets})
        summaries.append({'pack':label,'key':key,'asset_entries':len(assets),'distinct_base_meshes':unique,
                          'standing_tree_entries':sum(o['kind']=='standing tree' for o in rows if o['pack']==key),
                          'log_entries':sum(o['kind']=='log' for o in rows if o['pack']==key),
                          'base_triangle_range':[min(o['base_triangles'] for o in assets),max(o['base_triangles'] for o in assets)] if assets else [],
                          'file_version':data['file_version'],'source':data['source']})
        for page,start in enumerate(range(0,len(assets),42),1):
            sheet([o for o in rows if o['pack']==key][start:start+42],O/f'{key}-{page}.jpg',f'{label} / page {page}')
    groups=collections.defaultdict(list)
    for obj in rows: groups[obj['geometry_hash']].append(obj['pack']+'/'+obj['name'])
    result={'packs':summaries,'assets':rows,'same_base_mesh_groups':[v for v in groups.values() if len(v)>1],
            'sources':[{'key':k,'path':v['source'],'sha256':v['sha256'],'unchanged':v['source_unchanged'],
                        'objects':len(v['objects'])} for k,v in reports.items()],
            'limits':'Asset entries include moss/snow/material variants. Base geometry hashes exclude modifiers, materials and transforms; not a count of final unique silhouettes. Preview colours are source thumbnails, not an Unreal transfer guarantee.'}
    (O/'tree-inventory.json').write_text(json.dumps(result,indent=2))
    (R/'Docs/validation/downloaded-tree-inventory.json').write_text(json.dumps({
        'status':'read-only source inventory complete','source_files_inspected':len(reports),
        'source_files_unchanged':all(v['source_unchanged'] for v in reports.values()),
        'packs':summaries,'standing_tree_asset_entries':sum(s['standing_tree_entries'] for s in summaries),
        'log_asset_entries':sum(s['log_entries'] for s in summaries),
        'current_flora_trail_sources':{'FP_Tree_B_001':147,'FP_Tree_D_001':193},
        'unreal_appearance_validated':False,'catalogue':'Art/Export/TreeInventory/index.html',
        'limits':result['limits']},indent=2)+'\n')
    cards=[]
    for obj in rows:
        preview=Path(obj['preview']).relative_to(O).as_posix() if obj.get('preview') else ''
        label=obj['pack_label']+' / '+obj['name']+' / '+obj['kind']
        mods=', '.join(m['type'] for m in obj['modifiers']) or 'none'
        cards.append(f'<article data-search="{html.escape(label.lower())}"><img loading="lazy" src="{html.escape(preview)}"><h3>{html.escape(obj["name"])}</h3><p>{html.escape(obj["pack_label"])} / {obj["kind"]}</p><p>{obj["base_triangles"]:,} base triangles · '+('CURRENT SOURCE NAME' if obj['current'] else 'not selected in FloraTrail')+f'</p><details><summary>Source details</summary><p>Modifiers: {html.escape(mods)}</p><p>Materials: {html.escape(", ".join(m for m in obj["materials"] if m))}</p><p>{html.escape(obj["source"])}</p></details></article>')
    table=''.join(f'<tr><td>{s["pack"]}</td><td>{s["asset_entries"]}</td><td>{s["distinct_base_meshes"]}</td><td>{s["base_triangle_range"]}</td></tr>' for s in summaries)
    page='''<!doctype html><meta charset="utf-8"><title>Downloaded tree inventory</title><style>
body{font:16px system-ui;background:#172326;color:#e7eee9;margin:30px}h1{font-size:30px}p{line-height:1.5}table{border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #45544f;text-align:left}input{font:inherit;padding:12px;width:440px;max-width:90%;margin:20px 0}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:18px}article{background:#263638;padding:14px;border-radius:8px}article img{display:block;width:100%;height:220px;object-fit:contain;background:#101719}article p{font-size:13px}details{overflow-wrap:anywhere}h3{margin-bottom:5px}</style>
<h1>Downloaded tree inventory</h1><p>Original embedded asset previews, extracted read-only. No Unreal scene changes. These show source appearance, not a promise of identical Unreal output.</p>
<p>FloraTrail currently uses FP_Tree_B_001 (147 placements) and FP_Tree_D_001 (193 placements), from the bonus-scene conversion. The matching library names are marked below; file revisions may differ.</p>
<table><tr><th>Library</th><th>Tree asset entries</th><th>Distinct base meshes</th><th>Base triangle range</th></tr>'''+table+'''</table><p>Counts include material, moss and snow variants. Base meshes exclude modifiers and do not establish distinct final silhouettes, LOD cost or frame rate.</p><input id="filter" placeholder="Filter by pack or tree name"><span id="count"></span><div class="grid">'''+''.join(cards)+'''</div><script>const input=document.querySelector('#filter'),cards=[...document.querySelectorAll('article')];function filter(){let n=0;for(const card of cards){card.hidden=!card.dataset.search.includes(input.value.toLowerCase());if(!card.hidden)n++;}document.querySelector('#count').textContent=n+' entries';}input.addEventListener('input',filter);filter();</script>'''
    (O/'index.html').write_text(page,encoding='utf-8')
    choices=[('flora-main','FP_Tree_F_001'),('flora-main','FP_Tree_F_002'),
             ('flora-main','FP_Tree_F_003'),('flora-main','FP_Tree_F_004'),
             ('flora-update','FP_Tree_K_003'),('flora-update','FP_Tree_K_005'),
             ('flora-main','FP_Tree_A_moss_002'),('flora-main','FP_Tree_E_001'),
             ('trees-library','Tree_012'),('trees-library','Tree_021'),
             ('lazy-assets','Tree_04'),('lazy-assets','Tree_05')]
    selected=[next(o for o in rows if o['pack']==pack and o['name']==name) for pack,name in choices]
    sheet(selected,O/'woodland-shortlist.jpg','Woodland candidates / silhouettes to test; preserve their source appearance first')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
