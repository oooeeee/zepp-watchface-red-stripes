// Where every image goes for a given state. Pure: no Zepp OS imports, so it is
// tested with plain Node and also used to render the preview.
import { LAYOUT } from './layout.js'
import { clockDigits, batteryBarImage } from '../utils/format.js'

export const MAX_STEP_CHARS = 6

// Image slots, in drawing order (later ones are drawn on top)
const STEP_SLOTS = Array.from({ length: MAX_STEP_CHARS }, (_, i) => `st${i}`)
export const NORMAL_SLOTS = ['weekday', 'day', 'month', 'ampm', 'h0', 'h1', 'm0', 'm1',
  'stepsIcon', ...STEP_SLOTS, 'battery']
export const AOD_SLOTS = ['weekday', 'day', 'month', 'h0', 'h1', 'm0', 'm1']

// Lays items out along the tilted baseline (perpendicular to the stripes).
// (ax, ay) is a point on the row's center line; align is where it sits in the row.
export function row(items, ax, ay, align) {
  const { cos, sin } = LAYOUT.tilt
  const total = items.reduce((sum, it) => sum + it.adv, 0)
  let along = align === 'left' ? 0 : align === 'center' ? -total / 2 : -total
  return items.map((it) => {
    const mid = along + it.adv / 2
    along += it.adv
    const cx = ax + mid * cos
    const cy = ay - mid * sin
    return { src: it.src, x: Math.round(cx - it.w / 2), y: Math.round(cy - it.h / 2), w: it.w, h: it.h }
  })
}

// Places `second` right after `first` along the date stripe
export function followPosition(first, second) {
  const b = LAYOUT.date_band
  const cy = first.end_y + (b.gap + second.len / 2) * b.cos
  const cx = b.x0 + b.center + b.slope * cy
  return { src: second.src, x: Math.round(cx - second.w / 2), y: Math.round(cy - second.h / 2), w: second.w, h: second.h }
}

function placed({ src, x, y, w, h }) {
  return { src, x, y, w, h }
}

// Weekday, day and month labels; English is "Feb 22", Russian "22 фев"
function dateSlots(lang, weekday, month, day) {
  const labels = LAYOUT.langs[lang] || LAYOUT.langs.en
  const d = LAYOUT.days[day - 1]
  const m = labels.months[month - 1]
  return {
    weekday: placed(labels.weekdays[weekday - 1]),
    day: labels.order === 'day_month' ? placed(d) : followPosition(m, d),
    month: labels.order === 'day_month' ? followPosition(d, m) : placed(m)
  }
}

function textItems(text) {
  return text.split('').map((ch) => LAYOUT.glyphs[ch])
}

function digitItems(pair) {
  const { w, h, adv } = LAYOUT.digit
  return pair.map((n) => ({ src: `digits/${n}.png`, w, h, adv }))
}

function fill(slots, keys, placed) {
  keys.forEach((key, i) => {
    slots[key] = placed[i] || null
  })
}

// state: { lang ('en' | 'ru'), hour24, minute, is12h, weekday (1 = Monday), month (1-12), day, battery, steps }
export function scene(state) {
  const { hour, minute, ampm } = clockDigits(state.hour24, state.minute, state.is12h)
  const time = {}
  fill(time, ['h0', 'h1'], row(digitItems(hour), LAYOUT.hours.cx, LAYOUT.hours.cy, 'center'))
  fill(time, ['m0', 'm1'], row(digitItems(minute), LAYOUT.minutes.cx, LAYOUT.minutes.cy, 'center'))

  const date = dateSlots(state.lang, state.weekday, state.month, state.day)

  const normal = { ...date, ...time }
  normal.ampm = ampm ? { src: `date/${ampm}.png`, ...LAYOUT.ampm[ampm] } : null

  const stepsText = String(state.steps).slice(0, MAX_STEP_CHARS)
  const steps = row([LAYOUT.steps_icon, ...textItems(stepsText)], LAYOUT.steps.x, LAYOUT.steps.y, 'left')
  normal.stepsIcon = steps[0]
  fill(normal, STEP_SLOTS, steps.slice(1))

  const bar = LAYOUT.battery_bar
  normal.battery = { src: batteryBarImage(state.battery, bar.step), x: bar.x, y: bar.y, w: bar.w, h: bar.h }

  return { normal, aod: { ...date, ...time } }
}
