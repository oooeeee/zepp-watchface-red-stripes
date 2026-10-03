#!/usr/bin/env python3
"""Generate the watch face images, watchface/layout.js and the preview.

Usage (needs Pillow and Node):  python3 tools/gen_assets.py

TEXT widgets can't be rotated, so everything that is tilted is pre-rendered
here: outlined digits, small glyphs for numbers, icons, the stripe background
and the date labels. Geometry lives in this file; the watch face reads it from
the generated watchface/layout.js and places images with watchface/scene.js.
The preview is rendered from the same scene.js, via tools/preview_scene.mjs.
"""
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets', '390x450-amazfit-bip-6')
FONT = os.path.join(ROOT, 'tools', 'fonts', 'Roboto.ttf')

SCREEN_W, SCREEN_H = 390, 450
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)

# Stripe colors the user can pick in the watch's edit mode (first is the default).
# The labels on the stripes stay white, so keep colors dark enough for white text.
STRIPE_COLORS = [
    ('red', RED),
    ('blue', (0, 110, 230, 255)),
    ('green', (0, 150, 70, 255)),
    ('orange', (240, 100, 0, 255)),
    ('purple', (140, 60, 210, 255)),
    ('gray', (100, 100, 100, 255)),
]
EDIT_TIPS = (16, 14, 110, 44)  # x, y, w, h of the "1/6" hint shown in edit mode

# Stripes run down and to the right: x grows by SLOPE per pixel of y.
SLOPE = 0.2
STRIPE_X0 = 235  # x of the stripes' left edge at y = 0
# Bands as horizontal offsets from the left edge: (start, end, color)
# Band colors: None means the selected stripe color
BANDS = [(0, 46, None), (46, 53, BLACK), (53, 104, None), (104, 110, BLACK), (110, 124, None)]
BAND_DATE = (0, 46)  # date and AM/PM
BAND_WEEKDAY = (53, 104)  # wider, and the weekday gets its whole visible length
STRIPE_TEXT_SIZE = 30
STRIPE_TEXT_GAP = 10  # between day and month along the stripe
WEEKDAY_START_Y = 30
DATE_START_Y = 30  # where the first date label (day or month) starts
AMPM_CENTER_Y = 178

# Everything else is tilted so its baseline is perpendicular to the stripes
TILT = math.degrees(math.atan(SLOPE))  # ~11.3 degrees, counterclockwise

# Outlined digits
DIGIT_SIZE = 212
DIGIT_WIDTH_AXIS = 75  # Roboto width axis, 75..100; narrower digits fit 390 px
DIGIT_STROKE = 4
HOURS_CENTER = (132, 140)
MINUTES_CENTER = (258, 322)

# Small numbers (steps)
GLYPH_SIZE = 26
GLYPHS = '0123456789'
ICON_GAP = 8
STEPS_START = (14, 330)  # left end of "[icon] 4900"

# Battery: a thin line under the steps row, pre-rendered per 5 % step
BATTERY_BAR_LEN = 120
BATTERY_BAR_THICK = 5
BATTERY_BAR_BELOW = 24  # distance from the steps row's center line
BATTERY_STEP = 5
BATTERY_OK = (0x33, 0xdd, 0x55, 255)
BATTERY_LOW = (0xff, 0x3b, 0x30, 255)
BATTERY_TRACK = (0x3a, 0x3a, 0x3a, 255)

# Labels per watch language; the watch face picks one with getLanguage().
# 'order' is which date label comes first along the stripe.
LANGS = {
    'en': {
        'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'order': 'month_day',
    },
    'ru': {
        'weekdays': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
        'months': ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'],
        'order': 'day_month',
    },
}


def font(size, weight, width=100):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([weight, width])
    return f


def save(img, rel):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def tilt(img):
    return img.rotate(TILT, resample=Image.BICUBIC, expand=True)


def stripe_x(offset, y):
    return STRIPE_X0 + offset + SLOPE * y


# ---------- stripes background: full screen (the editable background widget is
# positioned at 0, 0), transparent outside the stripes

def band_polygon(a, b):
    top, bottom = -10, SCREEN_H + 10
    return [(stripe_x(a, top), top), (stripe_x(b, top), top), (stripe_x(b, bottom), bottom), (stripe_x(a, bottom), bottom)]


def stripes_image(stripe_color):
    img = Image.new('RGBA', (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for a, b, color in BANDS:
        d.polygon(band_polygon(a, b), fill=color or stripe_color)
    return img


def edit_fg_image():
    """Outline of the stripes, drawn over them in edit mode to show what changes"""
    img = Image.new('RGBA', (SCREEN_W, SCREEN_H), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(band_polygon(BANDS[0][0], BANDS[-1][1]), outline=WHITE, width=3)
    return img


def edit_tips_image():
    _, _, w, h = EDIT_TIPS
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(60, 60, 60, 255))
    return img


# ---------- outlined digits with an opaque black inside, so stripes don't show through

def digit_image(ch, f, cell_w, cell_h, top):
    img = Image.new('RGBA', (cell_w, cell_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = d.textlength(ch, font=f)
    d.text(((cell_w - w) / 2, -top), ch, font=f, fill=BLACK, stroke_width=DIGIT_STROKE, stroke_fill=WHITE)
    # Fill counters (holes in 0, 4, 6, 8, 9) black: anything transparent that the
    # outside can't reach is inside the glyph.
    mask = Image.new('L', (cell_w + 2, cell_h + 2), 0)
    mask.paste(img.getchannel('A'), (1, 1))
    ImageDraw.floodfill(mask, (0, 0), 128, thresh=0)
    px, mpx = img.load(), mask.load()
    for y in range(cell_h):
        for x in range(cell_w):
            if mpx[x + 1, y + 1] == 0:
                px[x, y] = BLACK
    return img


def digits():
    f = font(DIGIT_SIZE, 900, DIGIT_WIDTH_AXIS)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    boxes = [probe.textbbox((0, 0), str(n), font=f, stroke_width=DIGIT_STROKE) for n in range(10)]
    top = min(b[1] for b in boxes)
    cell_h = max(b[3] for b in boxes) - top
    cell_w = math.ceil(max(probe.textlength(str(n), font=f) for n in range(10))) + DIGIT_STROKE * 2
    return [digit_image(str(n), f, cell_w, cell_h, top) for n in range(10)], cell_w


# ---------- small glyphs: same cell height so they line up on one baseline

def glyphs():
    f = font(GLYPH_SIZE, 400)
    ascent, descent = f.getmetrics()
    out = {}
    for i, ch in enumerate(GLYPHS):
        adv = math.ceil(f.getlength(ch))
        img = Image.new('RGBA', (adv, ascent + descent), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((0, 0), ch, font=f, fill=WHITE)
        rotated = tilt(img)
        save(rotated, f'glyphs/{ch}.png')
        out[ch] = {'src': f'glyphs/{ch}.png', 'w': rotated.width, 'h': rotated.height, 'adv': adv}
    return out


# ---------- slanted stripe labels

STRIPE_ANGLE = -(90 - TILT)  # text reads down along the stripe


def stripe_label(text):
    f = font(STRIPE_TEXT_SIZE, 600)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, t, r, b = probe.textbbox((0, 0), text, font=f)
    img = Image.new('RGBA', (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2 - l, 2 - t), text, font=f, fill=WHITE)
    return img.rotate(STRIPE_ANGLE, resample=Image.BICUBIC, expand=True), r - l


def place_on_band(img, band, center_y):
    """Top-left for a rotated label centered on the band's axis at center_y."""
    cx = stripe_x((band[0] + band[1]) / 2, center_y)
    return round(cx - img.width / 2), round(center_y - img.height / 2)


# ---------- icons (drawn upright, then tilted)

def battery_bar(percent, color):
    scale = 4
    w, h = BATTERY_BAR_LEN * scale, BATTERY_BAR_THICK * scale
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=BATTERY_TRACK)
    fill_w = round(w * percent / 100)
    if fill_w > 0:
        d.rounded_rectangle((0, 0, max(fill_w, h) - 1, h - 1), radius=h // 2, fill=color)
    return img.resize((BATTERY_BAR_LEN, BATTERY_BAR_THICK), Image.LANCZOS)


def steps_icon(size=30):
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for dx, dy in ((0.08, 0.0), (0.52, 0.18)):
        x, y = dx * s, dy * s
        d.ellipse((x, y, x + 0.36 * s, y + 0.5 * s), fill=WHITE)  # sole
        d.ellipse((x + 0.04 * s, y + 0.56 * s, x + 0.32 * s, y + 0.8 * s), fill=WHITE)  # heel
    return img.resize((size, size), Image.LANCZOS)


def main():
    rad = math.radians(TILT)
    layout = {
        'screen': [SCREEN_W, SCREEN_H],
        # Baseline direction of tilted rows is (cos, -sin)
        'tilt': {'cos': math.cos(rad), 'sin': math.sin(rad)},
    }

    options = []
    for i, (name, color) in enumerate(STRIPE_COLORS):
        save(stripes_image(color), f'stripes/{name}.png')
        options.append({'id': i + 1, 'name': name, 'src': f'stripes/{name}.png'})
    save(edit_fg_image(), 'stripes/edit_fg.png')
    save(edit_tips_image(), 'stripes/edit_tips.png')
    tx, ty, _, _ = EDIT_TIPS
    layout['stripes'] = {'options': options, 'fg': 'stripes/edit_fg.png',
                         'tips': {'x': tx, 'y': ty, 'src': 'stripes/edit_tips.png'}}

    digit_imgs, cell_w = digits()
    for n, img in enumerate(digit_imgs):
        rotated = tilt(img)
        save(rotated, f'digits/{n}.png')
    layout['digit'] = {'w': rotated.width, 'h': rotated.height, 'adv': cell_w}
    layout['hours'] = {'cx': HOURS_CENTER[0], 'cy': HOURS_CENTER[1]}
    layout['minutes'] = {'cx': MINUTES_CENTER[0], 'cy': MINUTES_CENTER[1]}

    layout['glyphs'] = glyphs()

    steps = steps_icon()
    rotated = tilt(steps)
    save(rotated, 'icons/steps.png')
    layout['steps_icon'] = {'src': 'icons/steps.png', 'w': rotated.width, 'h': rotated.height, 'adv': steps.width + ICON_GAP}
    layout['steps'] = {'x': STEPS_START[0], 'y': STEPS_START[1]}

    # Battery line: same size for every level, so its position is fixed. Its
    # center is half its length along the steps row, then BATTERY_BAR_BELOW down
    # (perpendicular to the row, i.e. along the stripes).
    for percent in range(0, 101, BATTERY_STEP):
        for key, color in (('ok', BATTERY_OK), ('low', BATTERY_LOW)):
            bar = tilt(battery_bar(percent, color))
            save(bar, f'battery/{key}_{percent}.png')
    cos_t, sin_t = math.cos(rad), math.sin(rad)
    cx = STEPS_START[0] + BATTERY_BAR_LEN / 2 * cos_t + BATTERY_BAR_BELOW * sin_t
    cy = STEPS_START[1] - BATTERY_BAR_LEN / 2 * sin_t + BATTERY_BAR_BELOW * cos_t
    layout['battery_bar'] = {'x': round(cx - bar.width / 2), 'y': round(cy - bar.height / 2),
                             'w': bar.width, 'h': bar.height, 'step': BATTERY_STEP}

    # Date labels: each stores where it goes when it comes first on the stripe
    # (starting at DATE_START_Y) and its length, so the second label can follow
    # it (see followPosition() in scene.js)
    cos_a = 1 / math.sqrt(1 + SLOPE ** 2)

    def date_label(text, src):
        img, length = stripe_label(text)
        save(img, src)
        x, y = place_on_band(img, BAND_DATE, DATE_START_Y + (length / 2) * cos_a)
        return {'src': src, 'x': x, 'y': y, 'w': img.width, 'h': img.height,
                'len': length, 'end_y': round(DATE_START_Y + length * cos_a, 1)}

    layout['days'] = [date_label(str(n), f'date/day_{n}.png') for n in range(1, 32)]
    layout['date_band'] = {'x0': STRIPE_X0, 'center': (BAND_DATE[0] + BAND_DATE[1]) / 2,
                           'slope': SLOPE, 'cos': cos_a, 'gap': STRIPE_TEXT_GAP}

    layout['langs'] = {}
    for lang, labels in LANGS.items():
        weekdays = []
        for i, name in enumerate(labels['weekdays']):
            src = f'date/{lang}/wd_{i + 1}.png'
            img, length = stripe_label(name)
            save(img, src)
            x, y = place_on_band(img, BAND_WEEKDAY, WEEKDAY_START_Y + (length / 2) * cos_a)
            weekdays.append({'src': src, 'x': x, 'y': y, 'w': img.width, 'h': img.height})
        months = [date_label(name, f'date/{lang}/mon_{i + 1}.png') for i, name in enumerate(labels['months'])]
        layout['langs'][lang] = {'weekdays': weekdays, 'months': months, 'order': labels['order']}

    ampm = {}
    for key in ('am', 'pm'):
        img, _ = stripe_label(key.upper())
        save(img, f'date/{key}.png')
        x, y = place_on_band(img, BAND_DATE, AMPM_CENTER_Y)
        ampm[key] = {'x': x, 'y': y, 'w': img.width, 'h': img.height}
    layout['ampm'] = ampm

    with open(os.path.join(ROOT, 'watchface', 'layout.js'), 'w') as fh:
        fh.write('// Generated by tools/gen_assets.py, do not edit by hand\n')
        fh.write(f'export const LAYOUT = {json.dumps(layout, indent=2, ensure_ascii=False)}\n')

    # The watch shows one preview (icon.png): English, default color.
    # tools/preview-<lang>.png are full-size previews for the store listing, and
    # tools/preview-colors.png shows every stripe color.
    default = options[0]['src']
    for lang in LANGS:
        screen = render_preview(lang, default)
        screen.save(os.path.join(ROOT, 'tools', f'preview-{lang}.png'))
        if lang == 'en':
            # 266x307 is the previewSize for 390x450 screens in the zeus device list
            screen.resize((266, 307), Image.LANCZOS).save(os.path.join(ASSETS, 'icon.png'))
    shots = [render_preview('en', o['src']).resize((195, 225), Image.LANCZOS) for o in options]
    sheet = Image.new('RGB', (len(shots) * 205 - 10, 225), (40, 40, 40))
    for i, shot in enumerate(shots):
        sheet.paste(shot, (i * 205, 0))
    sheet.save(os.path.join(ROOT, 'tools', 'preview-colors.png'))


# ---------- preview: the real scene (from scene.js) at a sample time

def render_preview(lang, stripes_src):
    out = subprocess.run(['node', os.path.join(ROOT, 'tools', 'preview_scene.mjs'), json.dumps({'lang': lang})],
                         check=True, capture_output=True, text=True).stdout
    slots = json.loads(out)
    screen = Image.new('RGBA', (SCREEN_W, SCREEN_H), BLACK)
    screen.alpha_composite(Image.open(os.path.join(ASSETS, stripes_src)).convert('RGBA'))
    for slot in slots:
        img = Image.open(os.path.join(ASSETS, slot['src'])).convert('RGBA')
        # Paste with clipping, like the screen does
        layer = Image.new('RGBA', (SCREEN_W + 400, SCREEN_H + 400), (0, 0, 0, 0))
        layer.alpha_composite(img, (slot['x'] + 200, slot['y'] + 200))
        screen.alpha_composite(layer.crop((200, 200, 200 + SCREEN_W, 200 + SCREEN_H)))
    return screen.convert('RGB')


if __name__ == '__main__':
    main()
