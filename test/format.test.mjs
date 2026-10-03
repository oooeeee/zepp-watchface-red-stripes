// Run with: node --test test/
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { clockDigits, batteryBarImage } from '../utils/format.js'
import { scene, NORMAL_SLOTS, AOD_SLOTS } from '../watchface/scene.js'

test('12-hour clock', () => {
  assert.deepEqual(clockDigits(17, 46, true), { hour: [0, 5], minute: [4, 6], ampm: 'pm' })
  assert.deepEqual(clockDigits(0, 5, true), { hour: [1, 2], minute: [0, 5], ampm: 'am' })
  assert.deepEqual(clockDigits(12, 0, true), { hour: [1, 2], minute: [0, 0], ampm: 'pm' })
  assert.deepEqual(clockDigits(11, 59, true), { hour: [1, 1], minute: [5, 9], ampm: 'am' })
})

test('24-hour clock', () => {
  assert.deepEqual(clockDigits(17, 46, false), { hour: [1, 7], minute: [4, 6], ampm: null })
  assert.deepEqual(clockDigits(0, 0, false), { hour: [0, 0], minute: [0, 0], ampm: null })
})

test('battery line image: 5 % steps, red below 20 %', () => {
  assert.equal(batteryBarImage(0, 5), 'battery/low_0.png')
  assert.equal(batteryBarImage(19, 5), 'battery/low_20.png')
  assert.equal(batteryBarImage(20, 5), 'battery/ok_20.png')
  assert.equal(batteryBarImage(69, 5), 'battery/ok_70.png')
  assert.equal(batteryBarImage(100, 5), 'battery/ok_100.png')
})

const base = { lang: 'en', hour24: 17, minute: 46, is12h: true, weekday: 3, month: 2, day: 22, battery: 69, steps: 4900 }

test('scene fills every slot it declares', () => {
  const { normal, aod } = scene(base)
  for (const k of NORMAL_SLOTS) assert.ok(k in normal, `normal slot ${k}`)
  for (const k of AOD_SLOTS) assert.ok(aod[k], `aod slot ${k}`)
  assert.equal(normal.st4, null) // "4900" uses 4 of 6 step slots
})

test('date order: month first in English, day first in Russian', () => {
  const en = scene(base).normal
  assert.equal(en.month.src, 'date/en/mon_2.png')
  assert.ok(en.month.y < en.day.y)
  const ru = scene({ ...base, lang: 'ru' }).normal
  assert.equal(ru.month.src, 'date/ru/mon_2.png')
  assert.ok(ru.day.y < ru.month.y)
  assert.equal(scene({ ...base, lang: 'de' }).normal.weekday.src, 'date/en/wd_3.png')
})

test('24-hour mode hides AM/PM', () => {
  assert.equal(scene({ ...base, is12h: false }).normal.ampm, null)
})

test('every date and the longest numbers stay on screen', () => {
  for (const lang of ['en', 'ru']) for (let weekday = 1; weekday <= 7; weekday++) {
    for (let month = 1; month <= 12; month++) {
      for (let day = 1; day <= 31; day++) {
        const { normal } = scene({ ...base, lang, weekday, month, day, battery: 100, steps: 999999 })
        for (const key of ['weekday', 'day', 'month', 'st5', 'battery']) {
          const s = normal[key]
          assert.ok(s.x >= 0 && s.y >= 0 && s.x + s.w <= 390 && s.y + s.h <= 450, `${key} off screen`)
        }
        // The month must end above the AM/PM label
        assert.ok(Math.max(normal.month.y + normal.month.h, normal.day.y + normal.day.h) <= normal.ampm.y + 8, `${lang} date overlaps AM/PM on ${day}.${month}`)
      }
    }
  }
})
