import { createWidget, widget, prop, show_level } from '@zos/ui'
import { Time, Battery, Step, TIME_HOUR_FORMAT_12 } from '@zos/sensor'
import { getLanguage } from '@zos/settings'
import { LAYOUT } from './layout'
import { scene, NORMAL_SLOTS, AOD_SLOTS } from './scene'

// Every visible element is a pre-rendered image (tools/gen_assets.py); scene.js
// decides which image goes where. Widgets are created once and only changed
// slots are updated.

// getLanguage() codes: https://docs.zepp.com/docs/v2/reference/related-resources/language-list/
const LANGUAGE_RU = 4

// Stripes as an editable background: the user picks the color in the watch's
// edit mode (long press, Edit), and the system remembers and draws the choice.
function createStripes() {
  const s = LAYOUT.stripes
  const level = show_level.ONLY_NORMAL | show_level.ONLY_EDIT
  if (widget.WATCHFACE_EDIT_BG === undefined) {
    console.log('WATCHFACE_EDIT_BG not available, using the default stripes')
    createWidget(widget.IMG, { x: 0, y: 0, src: s.options[0].src, show_level: level })
    return
  }
  createWidget(widget.WATCHFACE_EDIT_BG, {
    edit_id: 101,
    x: 0,
    y: 0,
    bg_config: s.options.map(({ id, src }) => ({ id, preview: src, path: src })),
    count: s.options.length,
    default_id: s.options[0].id,
    fg: s.fg,
    tips_x: s.tips.x,
    tips_y: s.tips.y,
    tips_bg: s.tips.src,
    show_level: level
  })
}

function createSlots(keys, level) {
  const widgets = {}
  for (const key of keys) {
    widgets[key] = createWidget(widget.IMG, { x: 0, y: 0, src: 'digits/0.png', show_level: level })
    widgets[key].setProperty(prop.VISIBLE, false)
  }
  return { widgets, last: {} }
}

function apply(set, slots) {
  for (const key in set.widgets) {
    const slot = slots[key]
    const sig = slot ? `${slot.src}@${slot.x},${slot.y}` : ''
    if (set.last[key] === sig) continue
    set.last[key] = sig
    const w = set.widgets[key]
    if (slot) {
      w.setProperty(prop.MORE, { x: slot.x, y: slot.y, w: slot.w, h: slot.h, src: slot.src })
      w.setProperty(prop.VISIBLE, true)
    } else {
      w.setProperty(prop.VISIBLE, false)
    }
  }
}

WatchFace({
  onInit() {
    this.time = new Time()
    this.battery = new Battery()
    this.step = new Step()
    this.normal = null
    this.aod = null
    this.refreshNow = () => this.refresh()
  },

  build() {
    // Stripes first so the digits (with black insides) are drawn over them
    createStripes()
    // Also shown in edit mode, so the stripe color is picked in context
    this.normal = createSlots(NORMAL_SLOTS, show_level.ONLY_NORMAL | show_level.ONLY_EDIT)
    // AOD: time, weekday and date in white on black, no stripes
    this.aod = createSlots(AOD_SLOTS, show_level.ONAL_AOD)

    this.refresh()
    // Also covers the date changing at midnight
    this.time.onPerMinute(this.refreshNow)
    this.battery.onChange(this.refreshNow)
    this.step.onChange(this.refreshNow)
  },

  refresh() {
    if (!this.normal) return
    const t = this.time
    const { normal, aod } = scene({
      lang: getLanguage() === LANGUAGE_RU ? 'ru' : 'en',
      hour24: t.getHours(),
      minute: t.getMinutes(),
      is12h: t.getHourFormat() === TIME_HOUR_FORMAT_12,
      weekday: t.getDay(),
      month: t.getMonth(),
      day: t.getDate(),
      battery: this.battery.getCurrent(),
      steps: this.step.getCurrent()
    })
    apply(this.normal, normal)
    apply(this.aod, aod)
  },

  onDestroy() {
    this.battery.offChange(this.refreshNow)
    this.step.offChange(this.refreshNow)
    // Time.onPerMinute has no matching off/unregister call in the API
    this.normal = null
    this.aod = null
  }
})
