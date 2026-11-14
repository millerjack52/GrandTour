"""Assemble labelled Unreal/reference evidence without grading source screenshots.

Only greyscale thumbnails are converted; colour images retain their recorded RGB.
No successful render automatically passes a visual gate.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat

R = Path('C:/GrandTour')
O = R / 'Art/Export/FloraTrail/PaletteCandidate'
FONT = 'C:/Windows/Fonts/segoeui.ttf'
BG = '#142025'


def board(cards, path, title, subtitle, columns=3):
    cell_w, cell_h = 570, 450
    rows = (len(cards) + columns - 1) // columns
    result = Image.new('RGB', (24 + cell_w*columns, 110 + cell_h*rows), BG)
    draw = ImageDraw.Draw(result)
    draw.text((16, 12), title, font=ImageFont.truetype(FONT, 27), fill='#F0ECDC')
    draw.text((16, 54), subtitle, font=ImageFont.truetype(FONT, 19), fill='#C7D4D2')
    for index, (label, source) in enumerate(cards):
        x, y = 12 + index % columns*cell_w, 100 + index // columns*cell_h
        draw.text((x, y), label, font=ImageFont.truetype(FONT, 18), fill='#E8CB96')
        im = Image.open(source).convert('RGB')
        native = im.size
        display = im.copy(); display.thumbnail((552, 294), Image.Resampling.LANCZOS)
        result.paste(display, (x, y+28))
        thumb = im.copy(); thumb.thumbnail((320, 172), Image.Resampling.LANCZOS)
        # Separate exact-width greyscale/colour evidence, without enlarging screenshots.
        thumb.save(O / (Path(source).stem + '_320_colour.png'))
        thumb.convert('L').save(O / (Path(source).stem + '_320_grey.png'))
        draw.text((x, y+337), f'Original: {native[0]} x {native[1]} | fit only, no colour grade',
                  font=ImageFont.truetype(FONT, 16), fill='#C7D4D2')
        grey = thumb.convert('L'); grey.thumbnail((130, 70), Image.Resampling.LANCZOS)
        result.paste(grey, (x, y+364))
    result.save(path, quality=94)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--historical', action='store_true',
                        help='Explicitly label existing sunlight images; never invent candidate evidence')
    args = parser.parse_args()
    O.mkdir(parents=True, exist_ok=True)
    refs = json.loads((R / 'Art/Export/FloraPaletteStudy/reference-evidence.json').read_text())['sources']
    reference_cards = [(label, Path(refs[key])) for key, label in (
        ('woodland', 'Reference / primary green woodland'),
        ('path', 'Reference / selective light and depth'),
        ('sunlit', 'Reference / warm faces, cool interiors'))]
    if args.historical:
        cards = reference_cards + [(label, R / 'Art/Export/FloraTrail/Sunlight' / filename)
            for label, filename in (
                ('Existing Unreal / open road', 'game_saved_road.png'),
                ('Existing Unreal / upward crowns; NOT depth evidence', 'game_saved_canopy.png'),
                ('Existing Unreal / mixed materials', 'game_saved_mixed.png'))]
        board(cards, O / 'baseline-reference-review.jpg', 'FLORA TRAIL / baseline is not visually accepted',
              'Historical saved Unreal views, 13 November. No candidate render, motion check or new visual pass.')
        print(O / 'baseline-reference-review.jpg')
        return
    report = json.loads((O / 'diagnose-report.json').read_text())
    process = json.loads((O / 'diagnose-process.json').read_text(encoding='utf-8-sig'))
    assert report['ok'] and process['exit_code'] == 0
    sizes = {tuple(item['native_size']) for item in report['images']}
    assert len(sizes) == 1, 'Before/after captures have different native resolutions'
    for item in report['images']:
        with Image.open(O / (item['name'] + '.png')) as im:
            assert list(im.size) == item['native_size']
    display = Image.open(O / 'display_check.png').convert('RGB')
    x, y = display.width//2, display.height//2
    rgb = ImageStat.Stat(display.crop((x-8, y-8, x+8, y+8))).mean
    expected = (1.055 * .18**(1/2.4) - .055)*255
    assert max(abs(v-expected) for v in rgb) < 3, ('Standard neutral card failed', rgb)
    for view in ('road', 'canopy'):
        cards = reference_cards + [(case['name'] + ' / ' + view, O / (case['name']+'_'+view+'.png'))
                                   for case in json.loads((R/'Art/flora_trail_palette_probe_settings.json').read_text())['cases']
                                   if view in case['views']]
        board(cards, O / ('diagnosis_' + view + '.jpg'), 'FLORA TRAIL / controlled diagnosis / ' + view,
              'Actual Unreal. Fixed exposure, Standard display, FOV and quality. Review identity control first.')
    result = {'technical_capture_complete': True, 'native_size': list(next(iter(sizes))),
              'display_card_rgb': rgb, 'display_card_expected': expected,
              'candidate_installed': False, 'visual_acceptance': 'not tested',
              'motion': 'not tested', 'performance': 'not tested',
              'limits': 'Review each case visually before choosing material-family changes. A neutral card checks midgrey transfer only; it does not characterize the complete display curve.'}
    (O / 'review-report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
