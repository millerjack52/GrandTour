"""Validate a Gaea return and write a separate Unreal candidate; never edit the map.

The untouched export is mandatory. Apply its difference from the edited export
to the exact original Unreal samples, avoiding cumulative resampling drift.
"""
import argparse
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.errors import NotGeoreferencedWarning

from prepare_benmore_gaea import OUT, RANGE, resample


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_height(path, shape=(2048, 2048)):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', NotGeoreferencedWarning)
        with rasterio.open(path) as src:
            if src.count != 1:
                raise ValueError(f'{path.name}: expected one height channel, got {src.count}')
            a = src.read(1)
    if a.shape != shape:
        raise ValueError(f'{path.name}: expected {shape}, got {a.shape}; build at 2048')
    if a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535
    elif a.dtype in (np.float32, np.float64):
        a = a.astype(np.float64)
    else:
        raise ValueError(f'{path.name}: unsupported {a.dtype}; use TIFF32 or 16-bit PNG')
    if not np.isfinite(a).all() or a.min() < 0 or a.max() > 1:
        raise ValueError(f'{path.name}: height must be finite and normalized to the original 0..1 encoding')
    return a


def make_candidate(edited, reference, package=OUT, max_change_m=12.):
    manifest = json.loads((package / 'package-manifest.json').read_text())
    source = package / 'source/H_Current_Unreal_2017.r16'
    if sha(source) != manifest['source_height_sha256']:
        raise ValueError('Original Unreal height no longer matches the package manifest')
    expected = np.load(package / 'source/input_reference_normalized.npy')
    if reference.shape != expected.shape or edited.shape != expected.shape:
        raise ValueError('Returned data dimensions do not match the package')
    error = float(np.max(np.abs(reference - expected)) * RANGE)
    if error > .009:
        flipped = float(np.max(np.abs(reference[::-1] - expected)) * RANGE)
        raise ValueError(f'Untouched export changed by {error:.5f} m (Y-flipped error {flipped:.5f} m). Check gamma, normalization, Flip Y and resolution.')
    raw = np.fromfile(source, dtype='<u2').reshape(2017, 2017)
    base = (raw.astype(np.float64) - 32768) / 64
    delta = resample((edited - reference)[::-1] * RANGE, 2017)
    largest = float(np.max(np.abs(delta)))
    if largest > max_change_m:
        raise ValueError(f'Change reaches {largest:.2f} m, beyond first-pass review limit {max_change_m:.2f} m. Review the Gaea settings before increasing --max-change-m.')
    protect = np.load(package / 'source/protect_2017.npy')
    if protect.shape != base.shape or not np.isfinite(protect).all() or protect.min() < 0 or protect.max() > 1:
        raise ValueError('Invalid protection map')
    candidate = base + delta * (1 - protect)
    encoded = np.rint(candidate * 64 + 32768)
    if encoded.min() < 0 or encoded.max() > 65535:
        raise ValueError('Returned terrain exceeds the existing Unreal vertical range')
    encoded = encoded.astype('<u2')
    fixed = protect == 1
    if not np.array_equal(encoded[fixed], raw[fixed]):
        raise ValueError('Protected road/lake/boundary samples changed')
    change = (encoded.astype(float) - raw.astype(float)) / 64
    report = {
        'ok': True, 'source_level': manifest['source_level'],
        'source_height_sha256': manifest['source_height_sha256'],
        'resolution': 2017, 'row_zero': 'south (-Y)',
        'location_cm': [-125000, -125000, 0],
        'scale': [250000 / 2016, 250000 / 2016, 200],
        'untouched_reference_max_error_m': error,
        'unprotected_raw_delta_max_m': largest,
        'encoded_delta_min_m': float(change.min()),
        'encoded_delta_max_m': float(change.max()),
        'encoded_delta_abs_p99_m': float(np.quantile(np.abs(change), .99)),
        'changed_samples': int(np.count_nonzero(change)),
        'protected_samples': int(np.count_nonzero(fixed)),
        'protected_samples_changed': 0,
        'identity_roundtrip': bool(np.array_equal(encoded, raw)),
        'anchors': [{'pixel': [i,j], 'z_m': float((int(encoded[j,i])-32768)/64)}
                    for j in [0,17,289,731,1008,1501,1999,2016]
                    for i in [0,31,417,809,1008,1613,1981,2016]],
        'notes': ['Candidate only; no Unreal map was edited.',
                  'The exact original base receives the Gaea delta. Protected cores are unchanged.',
                  'Protection feathers are applied again on return as a safety envelope.']
    }
    return encoded, report


def convert(edited_path, reference_path, output, package=OUT, max_change_m=12.):
    encoded, report = make_candidate(read_height(edited_path), read_height(reference_path), package, max_change_m)
    output = output.resolve()
    # Never allow a candidate to overwrite source or an existing production height folder.
    if output != (package/'candidate').resolve() and (package/'review').resolve() not in output.parents:
        raise ValueError('Output must be this package/candidate or a subfolder of this package/review')
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'H_Benmore_Gaea_2017.r16'
    encoded.tofile(target)
    Image.fromarray(encoded).save(output / 'H_Benmore_Gaea_2017.png')
    rgba = np.empty((*encoded.shape, 4), dtype=np.uint8)
    rgba[:,:,0] = encoded >> 8
    rgba[:,:,1] = encoded & 255
    rgba[:,:,2] = 0
    rgba[:,:,3] = 255
    Image.fromarray(rgba).save(output / 'T_Benmore_GaeaHeightRG.png')
    ((encoded.astype(np.float32)-32768)/64).astype('<f4').tofile(output / 'height_local_south_up.f32')
    report.update(candidate_sha256=sha(target), edited_path=str(edited_path.resolve()),
                  reference_path=str(reference_path.resolve()), edited_sha256=sha(edited_path),
                  reference_sha256=sha(reference_path))
    (output / 'import-manifest.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edited', type=Path, default=OUT/'return/H_Eroded.tif')
    parser.add_argument('--reference', type=Path, default=OUT/'return/H_InputCheck.tif')
    parser.add_argument('--output', type=Path, default=OUT/'candidate')
    parser.add_argument('--max-change-m', type=float, default=12.)
    args = parser.parse_args()
    report = convert(args.edited, args.reference, args.output, max_change_m=args.max_change_m)
    print(json.dumps({k:v for k,v in report.items() if k != 'anchors'}, indent=2))


if __name__ == '__main__':
    main()
