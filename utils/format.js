// Pure display logic, no Zepp OS imports, so it can be tested with plain Node.

// Digits for the big clock. In 12-hour mode hours run 12, 1..11 and `ampm` is set.
export function clockDigits(hour24, minute, is12h) {
  const hour = is12h ? hour24 % 12 || 12 : hour24
  return {
    hour: [Math.floor(hour / 10), hour % 10],
    minute: [Math.floor(minute / 10), minute % 10],
    ampm: is12h ? (hour24 < 12 ? 'am' : 'pm') : null
  }
}

// Below this charge level the battery line turns red
export const LOW_BATTERY = 20

// Battery line image for a 0-100 charge; images exist for every `step` percent
export function batteryBarImage(percent, step) {
  const p = Math.max(0, Math.min(100, percent))
  const level = Math.round(p / step) * step
  return `battery/${p < LOW_BATTERY ? 'low' : 'ok'}_${level}.png`
}
