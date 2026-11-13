"""Read installed MudRunner editor authoring sources into a neutral research catalog.

Never writes to the installation or Unreal Content. Coordinates remain native X/Y/Z
(Y up), in metres. This is an inspector/export foundation, not an STG importer.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = Path(r'C:/Program Files (x86)/Steam/steamapps/common/MudRunner - Editor')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_xml(path):
    # Native brushes.xml repeats Divergence attributes. Preserve EVERY value and
    # flag the ambiguity; do not pretend to know which native parser value wins.
    duplicates = []
    def repair_tag(match):
        seen = {}
        def attribute(m):
            name, value = m.group(1), m.group(2)
            seen[name] = seen.get(name, 0) + 1
            if seen[name] > 1:
                duplicates.append(dict(tag=match.group(0), attribute=name, value=value))
                return f'__duplicate{seen[name]}_{name}="{value}"'
            return m.group(0)
        return re.sub(r'([\w:.-]+)\s*=\s*"([^"]*)"', attribute, match.group(0))
    text = re.sub(r'<[^>]+>', repair_tag, path.read_text(encoding='utf-8-sig'))
    return ET.fromstring(text), duplicates


def node_data(node):
    return dict(tag=node.tag, attributes=dict(node.attrib),
                children=[node_data(child) for child in node])


def height_data(path):
    raw = path.read_bytes()
    if raw[:4] != b'DDS ' or struct.unpack_from('<I', raw, 84)[0] != 111:
        raise ValueError(f'Expected legacy R16F DDS: {path}')
    height, width = struct.unpack_from('<II', raw, 12)
    if len(raw) != 128 + width * height * 2:
        raise ValueError(f'Unexpected payload size (mips or other format): {path}')
    values = np.frombuffer(raw, '<f2', offset=128).reshape(height, width).astype(np.float32) * 64.0
    if not np.isfinite(values).all():
        raise ValueError(f'Nonfinite height: {path}')
    return values


def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', size)


def preview_sheet(source, output):
    names = ['ref_road_muddy', 'ref_road_dirt', 'ref_forest_firs',
             'ref_swamp', 'ref_lake', 'ref_ditch_bridge']
    available = {p.stem: p for p in (source / 'Media/levels').glob('*.dds')}
    # Explicitly record selection; do not substitute an unrelated picture silently.
    selected = [(name, available[name]) for name in names if name in available]
    canvas = Image.new('RGB', (1260, 130 + 395 * ((len(selected) + 2) // 3)), '#18211f')
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 20), 'MudRunner editor: reusable terrain sections', font=font(29), fill='#f1efe7')
    draw.text((28, 65), 'Native bundled previews, individually fitted. Roads, vegetation and water arrive together.',
              font=font(18), fill='#b5c6b7')
    for i, (name, path) in enumerate(selected):
        x, y = 25 + i % 3 * 415, 120 + i // 3 * 395
        im = Image.open(path).convert('RGB')
        im = ImageOps.contain(im, (390, 340))
        canvas.paste(im, (x + (390-im.width)//2, y))
        draw.text((x, y+345), name, font=font(19), fill='white')
    canvas.save(output / 'native-reference-library.png')
    return [dict(name=n, source=str(p), sha256=digest(p)) for n, p in selected]


def mask_sheet(source, output):
    directory = source / 'Media/prebuild/ref_road_muddy'
    height = height_data(directory / '_height.dds')
    height_preview = Image.fromarray(np.uint8((height-height.min()) / (height.max()-height.min())*255)).convert('RGB')
    tiles = [('Height: 19.0 to 22.63 m', height_preview)]
    for name in ['trees', 'bushes', 'dirt', 'twigs']:
        p = directory / f'dstr_{name}.tga'
        a = np.asarray(Image.open(p).convert('RGB'))
        tiles.append((name + ': density (red channel)', Image.fromarray(a[:,:,0]).convert('RGB')))
    p = directory / 'dstr_bushes.tga'
    a = np.asarray(Image.open(p).convert('RGB'))
    tiles.append(('bushes: scale (green channel)', Image.fromarray(a[:,:,1]).convert('RGB')))
    canvas = Image.new('RGB', (1260, 950), '#18211f'); draw = ImageDraw.Draw(canvas)
    draw.text((28, 20), 'One muddy road section: separate authoring layers', font=font(29), fill='white')
    draw.text((28, 66), 'Actual source masks. Bright = more density / larger scale. Height display is contrast-normalized.', font=font(18), fill='#b5c6b7')
    for i, (name, im) in enumerate(tiles):
        x, y = 25 + i % 3 * 415, 120 + i // 3 * 405
        im = ImageOps.contain(im, (360, 345), Image.Resampling.NEAREST)
        canvas.paste(im, (x + (390-im.width)//2, y))
        draw.text((x, y+350), name, font=font(18), fill='white')
    canvas.save(output / 'muddy-road-authoring-layers.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=ROOT/'Art/Export/MudRunnerEditorResearch/Authoring')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output == source or source in output.parents:
        parser.error('Output must be outside the installed editor')
    output.mkdir(parents=True, exist_ok=True)
    brushes_path = source/'Media/prebuild/common/brushes.xml'
    brushes, duplicate_attrs = read_xml(brushes_path)
    catalog = dict(schema=1, source=str(source), coordinate_system='Native metres, X/Z horizontal, Y up; no Unreal axis conversion applied',
                   height_normalization_m=64, block_size_m=16,
                   brush_source=dict(path=str(brushes_path), sha256=digest(brushes_path),
                                     duplicate_attributes=duplicate_attrs, tree=node_data(brushes)),
                   terrains=[], road_height_profiles=[], preview_sources=[])
    files = sorted((source/'Media/prebuild').glob('*.xml')) + sorted((source/'Samples/mod_level/prebuild').glob('*.xml'))
    errors = []
    for path in files:
        terrain, duplicates = read_xml(path)
        bx, bz = int(terrain.attrib['NumBlocksX']), int(terrain.attrib['NumBlocksZ'])
        directory = path.with_suffix('')
        record = dict(name=path.stem, source=str(path), sha256=digest(path), blocks=[bx,bz], size_m=[bx*16,bz*16],
                      child_counts={n.tag:len(n) for n in terrain}, authoring=node_data(terrain),
                      duplicate_attributes=duplicates, layers=[])
        for layer in sorted(directory.glob('*')):
            if not layer.is_file(): continue
            item = dict(file=layer.name, bytes=layer.stat().st_size, sha256=digest(layer))
            if layer.name == '_height.dds':
                h = height_data(layer)
                item.update(format='R16F DDS', shape=list(h.shape), min_m=float(h.min()), max_m=float(h.max()),
                            expected_shape=[bz*24+1,bx*24+1])
                if list(h.shape) != item['expected_shape']:
                    errors.append(f'{path.stem}: unexpected height grid {h.shape}')
                if path.stem in ['ref_road_muddy','ref_forest_firs','ref_swamp','level_volcano_imported2016']:
                    np.save(output/(path.stem+'-height-metres.npy'), h)
            elif layer.suffix.lower() == '.tga':
                a = np.asarray(Image.open(layer).convert('RGBA'))
                item.update(shape=list(a.shape), channel_min=a.min(axis=(0,1)).tolist(), channel_max=a.max(axis=(0,1)).tolist())
                if layer.name.startswith('dstr_'):
                    item.update(red_density_nonzero_fraction=float(np.mean(a[:,:,0]>0)),
                                red_density_mean=float(a[:,:,0].mean()/255), green_scale_mean=float(a[:,:,1].mean()/255))
            else:
                item['format']='Undecoded; retained as source inventory only'
            record['layers'].append(item)
        catalog['terrains'].append(record)
    for path in sorted((source/'Media/prebuild/common').glob('hmoffset*.tga')):
        a = np.asarray(Image.open(path).convert('RGB'))[:,:,0]
        catalog['road_height_profiles'].append(dict(source=str(path), sha256=digest(path), shape=list(a.shape),
            red_min=int(a.min()), red_max=int(a.max()), full_alpha_offset_cm=[float((v/255-.5)*.06*64*100) for v in [int(a.min()),int(a.max())]],
            caveat='Full vertex alpha only; CPU ribbon taper and resampling not reconstructed'))
    catalog['preview_sources'] = preview_sheet(source, output)
    mask_sheet(source, output)
    sample_preview = source/'Samples/mod_level/levels/level_volcano_imported2016.dds'
    if sample_preview.exists():
        Image.open(sample_preview).convert('RGB').save(output/'native-volcano-sample.png')
        catalog['preview_sources'].append(dict(name=sample_preview.stem, source=str(sample_preview), sha256=digest(sample_preview)))
    (output/'authoring-catalog.json').write_text(json.dumps(catalog, indent=2), encoding='utf-8')
    checked = 0
    for record in catalog['terrains']:
        path = Path(record['source'])
        pairs = [(path,record['sha256'])] + [(path.with_suffix('')/layer['file'],layer['sha256']) for layer in record['layers']]
        for path, expected in pairs:
            checked += 1
            if digest(path) != expected: errors.append(f'Source changed during inspection: {path}')
    for record in [catalog['brush_source']] + catalog['road_height_profiles'] + catalog['preview_sources']:
        checked += 1
        if digest(Path(record.get('source',record.get('path')))) != record['sha256']:
            errors.append('Source changed during inspection: '+str(record.get('source',record.get('path'))))
    result = dict(ok=not errors, terrains=len(catalog['terrains']), builtin_references=len(list((source/'Media/prebuild').glob('ref_*.xml'))),
                  brushes=sum(len(group) for group in brushes), duplicate_attributes=len(duplicate_attrs),
                  errors=errors, source_files_verified_unchanged=checked)
    (output/'inspection-check.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if errors: raise SystemExit(1)


if __name__ == '__main__': main()
