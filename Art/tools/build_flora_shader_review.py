"""Assemble unretouched Unreal captures and creator thumbnails for visual review."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/LidarStudy/FloraShader'
PILOT = OUT.parent / 'FloraPilot'
BG = '#14211f'
FG = '#edf0e3'
MUTED = '#b6c5b9'

def font(size):
    for name in ['arial.ttf', 'segoeui.ttf', 'calibri.ttf']:
        p = Path('C:/Windows/Fonts') / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)

def picture(canvas, path, box, crop=None):
    im = Image.open(path).convert('RGBA')
    if crop:
        im = im.crop(crop)
    im = ImageOps.contain(im, (box[2]-box[0], box[3]-box[1]), Image.Resampling.LANCZOS)
    canvas.paste(im, (box[0]+(box[2]-box[0]-im.width)//2, box[1]+(box[3]-box[1]-im.height)//2), im)

def sheet(name, before, after, crop, refs, title):
    canvas = Image.new('RGB', (1920, 850), BG)
    d = ImageDraw.Draw(canvas)
    d.text((28, 18), title, fill=FG, font=font(34))
    d.text((28, 65), 'Actual Unreal captures: same camera, scene, geometry, sun and exposure.', fill=MUTED, font=font(22))
    for x, label in [(28, 'FLORA PAINT REFERENCE'), (400, 'BEFORE'), (1160, 'REFINED SHADER')]:
        d.text((x, 113), label, fill=FG, font=font(21))
    if len(refs) == 1:
        picture(canvas, OUT / before, (400, 154, 1136, 790), crop)
        picture(canvas, OUT / after, (1160, 154, 1896, 790), crop)
    else:
        for x, path in [(400, OUT / before), (1160, OUT / after)]:
            picture(canvas, path, (x, 154, x+736, 430), crop)
            d.text((x, 449), 'MATCHED DETAIL / SHRUB AND GRASS', fill=MUTED, font=font(20))
            picture(canvas, path, (x, 490, x+350, 780), (320, 335, 510, 510))
            picture(canvas, path, (x+374, 490, x+736, 780), (25, 425, 175, 570))
    if len(refs) == 1:
        picture(canvas, PILOT / refs[0], (28, 180, 370, 530))
    else:
        for i, ref in enumerate(refs):
            picture(canvas, PILOT / ref, (80, 157+i*200, 310, 350+i*200))
    y = 565 if len(refs) == 1 else 765
    d.text((28, y), 'Creator previews / Casey Sheep', fill=MUTED, font=font(18))
    if len(refs) == 1:
        d.text((28, y+29), 'Different camera and lighting.', fill=MUTED, font=font(18))
        d.text((28, y+58), 'Original 256 px thumbnail.', fill=MUTED, font=font(18))
    d.text((400, 810), 'Identical crops. No image colour correction. Woodland unchanged. GPU timings unverified.', fill=MUTED, font=font(19))
    canvas.save(OUT / name)

def slider(label, key):
    return f'''<section><h2>{label}</h2><p>Drag to compare. Before is on the left; refined shader is on the right.</p>
    <div class="compare" id="{key}"><img src="after-{key}.png" alt="Refined {label.lower()}">
    <img class="before" src="before-unreal-{key}.png" alt="Before {label.lower()}"><i></i>
    <span class="tag left">Before</span><span class="tag right">Refined</span></div>
    <input aria-label="{label} comparison position" type="range" min="0" max="100" value="50" data-target="{key}">
    <p class="links"><a href="before-unreal-{key}.png">Full-resolution before</a> · <a href="after-{key}.png">Full-resolution after</a></p></section>'''

def main():
    build = json.loads((OUT/'shader-report.json').read_text())
    capture = json.loads((OUT/'capture-report.json').read_text(encoding='utf-8-sig'))
    assert build['ok'] and capture['ok']
    protected = json.loads((OUT/'protected-before.json').read_text())
    for row in protected:
        with Path(row['file']).open('rb') as f:
            row['unchanged'] = hashlib.file_digest(f, 'sha256').hexdigest() == row['sha256']
        assert row['unchanged'], row['file']
    sheet('tree-comparison.png', 'before-unreal-tree.png', 'after-tree.png',
          (430, 55, 1230, 745), ['FP_Tree_E_001-source.png'], 'FLORA PAINT / foliage shader study')
    sheet('understory-comparison.png', 'before-unreal-understory.png', 'after-understory.png',
          (0, 285, 1600, 885), ['FP_Shrubbery_003-source.png', 'FP_Grass_003-source.png', 'FP_Small_Plants_002-source.png'],
          'FLORA PAINT / shrubs, grass and ground cover')
    refs = ''.join(f'<figure><img src="../FloraPilot/{file}"><figcaption>{label}</figcaption></figure>' for file, label in [
        ('FP_Tree_E_001-source.png', 'Tree E 001'), ('FP_Shrubbery_003-source.png', 'Shrubbery 003'),
        ('FP_Grass_003-source.png', 'Grass 003'), ('FP_Small_Plants_002-source.png', 'Small Plants 002')])
    stats = ''.join('<tr><td>'+r['material'].split('/')[-1].split('.')[0]+'</td>'+''.join('<td>'+str(r.get('compiled_statistics',{}).get(k,'unavailable'))+'</td>' for k in ['num_pixel_shader_instructions','num_vertex_shader_instructions','num_pixel_texture_samples'])+'</tr>' for r in build['materials'])
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>Flora Paint / foliage shader comparison</title><style>
    *{box-sizing:border-box}body{max-width:1500px;margin:auto;padding:32px;background:#14211f;color:#edf0e3;font:16px/1.6 system-ui}
    h1{font-size:38px;line-height:1.2;font-weight:500}h2{font-weight:500;margin:30px 0 8px}p{max-width:1000px;color:#b6c5b9}
    a{color:#cfdfa6}.eyebrow{font-size:12px;letter-spacing:.15em;color:#cfdfa6}.refs{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
    figure{margin:0;background:#1b2b27;border:1px solid #354b42;border-radius:8px;padding:14px}.refs img{width:100%;height:220px;object-fit:contain}
    figcaption{color:#c7d1c6}.compare{position:relative;overflow:hidden;--split:50%;border:1px solid #354b42}.compare img{display:block;width:100%}
    .compare .before{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--split)) 0 0)}.compare i{position:absolute;top:0;bottom:0;left:var(--split);border-left:2px solid white}
    .tag{position:absolute;top:14px;background:#14211fe6;padding:5px 12px;border-radius:5px;font-size:14px}.left{left:14px}.right{right:14px}
    input[type=range]{width:100%;accent-color:#bfd391;margin:14px 0}.links{margin-top:0}.note{padding:18px 24px;border-left:3px solid #bfd391;background:#1e3029}
    table{border-collapse:collapse;max-width:100%;font-size:14px}td,th{padding:8px 16px;text-align:left;border-bottom:1px solid #354b42}
    code{font-size:13px;overflow-wrap:anywhere}.controls td:first-child{white-space:nowrap}details{margin:22px 0}summary{cursor:pointer;color:#cfdfa6}
    @media(max-width:720px){body{padding:18px}.refs{grid-template-columns:1fr 1fr}.refs img{height:160px}h1{font-size:29px}table{font-size:12px}td,th{padding:7px}}
    </style><p class="eyebrow">GRAND TOUR · ISOLATED MATERIAL STUDY</p><h1>Bringing back the painted foliage</h1>
    <p>The revised shader restores soft mask coverage and the original upward-biased leaf lighting, then adds restrained brush detail, canopy colour variation and light-driven shadow fill. These are actual Unreal game captures, with the original meshes and test lighting.</p>
    <h2>Creator references</h2><div class="refs">'''+refs+'''</div>
    <p>Flora Paint by Casey Sheep. These are the purchased library's original 256 px previews, shown unretouched. Their camera, background and lighting differ from the Unreal test.</p>
    '''+slider('Tree canopy','tree')+slider('Understory','understory')+'''
    <p><a href="after-tree-pan.png">Additional settled camera angle</a> · <a href="tree-comparison.png">Tree comparison sheet</a> · <a href="understory-comparison.png">Understory comparison sheet</a></p>
    <h2>Editable material controls</h2><p>Use the five <code>MI_Flora_*_Trial</code> material instances in <code>/Game/GrandTour/ArtTests/FloraPilot</code>. Duplicate instances for each map; each can retain its own palette, softness and fill.</p>
    <table class="controls"><tr><th>Control</th><th>Effect</th></tr>
    <tr><td>FoliageTint / PaletteSoftness</td><td>Base colour and saturation restraint.</td></tr>
    <tr><td>LeafDetail / ClusterVariation / ClusterSizeCm</td><td>Painted detail and larger patches of colour within the canopy.</td></tr>
    <tr><td>LeafDensity / EdgeSoftness / GrazingCoverage</td><td>Silhouette coverage and how angled leaf cards fade.</td></tr>
    <tr><td>NormalSoftness / ShadowDensity</td><td>Reduce flat-card lighting and control the shadow cutout.</td></tr>
    <tr><td>SkySoftFill / SunBounce</td><td>Lift foliage interiors using scene light intensity. SunBounce is an artistic fill, capped at 0.25; it ignores local occlusion and needs dusk/night and enclosed-area checks.</td></tr>
    <tr><td>Backlight / TransmissionThickness</td><td>Light transmitted through leaves.</td></tr>
    <tr><td>WindStrengthCm / WindSpeed</td><td>Wind controls; strength is zero in this still-image review.</td></tr></table>
    <h2>Verification and remaining gates</h2>
    <p class="note">The woodland map, test map and all four meshes are byte-for-byte unchanged. The five test foliage materials compile and all three captures pass the capture checks. Visual approval is still open; this is a review pass, not a woodland rollout.</p>
    <p>No extra foliage textures or triangles were added. Each material still has one authored mask sample, but softer coverage, lighting fill and colour variation add shader work. Compiled statistics below are diagnostic counts, not a measured GPU performance result. Runtime timings remain unverified.</p>
    <details><summary>Compiled DX12 material statistics</summary><table><tr><th>Material</th><th>Pixel instructions</th><th>Vertex instructions</th><th>Estimated pixel texture samples</th></tr>'''+stats+'''</table><p>Engine statistics may include shared lighting resources. They should not be confused with the one authored foliage texture. There is no matched pre-change instruction-count baseline.</p></details>
    <p>Before woodland integration: check wind and moving-camera stability, dusk/night lighting, forest-density overdraw and distant LODs. The source tree remains 41,481 triangles; no geometry optimisation is claimed here. Softer edges are closer to the preview, while the reference's broader canopy shading and bark appearance are not an exact match.</p>
    <p>TSR quality 3, 1600 × 900 captures, fixed exposure and identical cameras. Before frames used 45 settling frames; after frames use 75. Images have only been cropped/resized for the sheets, with no colour edits.</p>
    <p><a href="shader-report.json">Material build and protected asset hashes</a> · <a href="capture-report.json">Capture checks</a> · <a href="review-validation.json">Review validation</a> · <a href="Tuning-and-validation.txt">Tuning notes and source provenance</a></p>
    <script>document.querySelectorAll('input[data-target]').forEach(el=>el.addEventListener('input',()=>document.getElementById(el.dataset.target).style.setProperty('--split',el.value+'%')))</script></html>'''
    (OUT/'index.html').write_text(html, encoding='utf-8')
    validation = {'build_passed':True,'capture_passed':True,'protected_assets':protected,'woodland_modified':False,
                  'visual_approval':'pending user review','performance_verified':False,'wind_motion_verified':False,
                  'night_lighting_verified':False,'reference_attribution':'Casey Sheep / Flora Paint purchased library thumbnails',
                  'reference_lighting_matches_test':False,'image_processing':'identical crops and resizing only; no colour correction'}
    (OUT/'review-validation.json').write_text(json.dumps(validation,indent=2))
    original = PILOT/'index.html'
    previous = original.read_text(encoding='utf-8')
    link = '<p class="note"><a href="../FloraShader/index.html"><strong>Open the new foliage shader before/after review</strong></a></p>'
    if '../FloraShader/index.html' not in previous:
        previous=previous.replace('<h2>Creator-supplied previews</h2>',link+'<h2>Creator-supplied previews</h2>')
        original.write_text(previous,encoding='utf-8')
    print('Review built; protected assets unchanged:',len(protected))

if __name__ == '__main__':
    main()
