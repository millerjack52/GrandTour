"""CPU data checks for the terrain round trip (no driving or timing tests)."""
import json
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from convert_benmore_gaea import OUT, make_candidate, read_height, convert, sha


def main():
    checks = []
    reference = read_height(OUT/'roundtrip/H_InputCheck.tif')
    unchanged = read_height(OUT/'roundtrip/H_Eroded.tif')
    result = convert(OUT/'roundtrip/H_Eroded.tif', OUT/'roundtrip/H_InputCheck.tif', OUT/'review/identity')
    assert result['identity_roundtrip']
    assert result['candidate_sha256'] == result['source_height_sha256']
    checks.append('Actual Gaea 2.3 build returns byte-identical original Unreal R16')
    raw = np.fromfile(OUT/'source/H_Current_Unreal_2017.r16',dtype='<u2').reshape(2017,2017)
    # Shift every Gaea sample: editable ground must move while protected cores do not.
    changed, stats = make_candidate(reference + 1/512, reference)
    protect = np.load(OUT/'source/protect_2017.npy')
    assert np.array_equal(changed[protect == 1], raw[protect == 1])
    assert np.all(changed[protect == 0].astype(int)-raw[protect == 0].astype(int) == 64)
    checks.append('One-metre edit moves editable samples and leaves protected samples exact')
    for title, edit, ref, limit in [
        ('Y-flipped return reference rejected', unchanged[::-1], reference[::-1],12),
        ('Autolevelled reference rejected', unchanged, (reference-reference.min())/np.ptp(reference),12),
        ('Gamma-converted reference rejected', unchanged, np.sqrt(reference),12),
        ('Oversized terrain edit rejected', reference+20/512,reference,12),
    ]:
        try:
            make_candidate(edit, ref, max_change_m=limit)
        except ValueError:
            checks.append(title)
        else:
            raise AssertionError(title)
    with tempfile.TemporaryDirectory(prefix='benmore-gaea-check-') as folder:
        p = Path(folder)/'invalid.png'
        Image.fromarray(np.zeros((2048,2048),dtype='uint8')).save(p)
        try:
            read_height(p)
        except ValueError:
            checks.append('8-bit heightmap rejected')
        else:
            raise AssertionError('8-bit input accepted')
    study = read_height(OUT/'return/H_Eroded.tif')
    study_ref = read_height(OUT/'return/H_InputCheck.tif')
    edit_mask = read_height(OUT/'input/M_FirstPass_Edit_2048.png')
    assert np.array_equal(study[edit_mask == 0], study_ref[edit_mask == 0])
    checks.append('Built Gaea Combine preserves samples outside the first-pass mask')
    rivers = read_height(OUT/'return/M_Rivers.tif')
    depth = read_height(OUT/'return/M_Depth.tif')
    assert np.count_nonzero(rivers * edit_mask) > 0 and depth.max() > 0
    checks.append('Gaea river and depth exports contain a channel in the editable area')
    candidate = convert(OUT/'return/H_Eroded.tif',OUT/'return/H_InputCheck.tif',OUT/'candidate')
    assert candidate['protected_samples_changed'] == 0
    checks.append('Built river study converts successfully with protected cores unchanged')
    report = {'ok':True,'gaea_version':'2.3.0.1','checks':checks,
              'identity_height_sha256':result['candidate_sha256'],
              'graph_sha256':sha(OUT/'Benmore_01_RiverStudy.terrain'),
              'river_pixels_in_edit_area':int(np.count_nonzero(rivers*edit_mask)),
              'candidate_report':'candidate/import-manifest.json',
              'unreal_import_performed':False}
    (OUT/'review/validation-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
