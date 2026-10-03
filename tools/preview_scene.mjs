// Prints the normal-mode image slots for a sample state, for the preview in gen_assets.py.
// Optional argument: JSON overriding fields of the sample state.
import { scene, NORMAL_SLOTS } from '../watchface/scene.js'

const { normal } = scene({
  lang: 'en', hour24: 17, minute: 46, is12h: true, weekday: 3, month: 2, day: 22, battery: 69, steps: 4900,
  ...JSON.parse(process.argv[2] || '{}')
})
console.log(JSON.stringify(NORMAL_SLOTS.map((k) => normal[k]).filter(Boolean)))
