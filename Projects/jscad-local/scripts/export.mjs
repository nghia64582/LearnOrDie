#!/usr/bin/env node
// Xuất model ra file STL bằng Node (không cần trình duyệt).
// Cách dùng:
//   npm run export                         -> models/main.js  => out/main.stl
//   npm run export -- models/gear.js       -> out/gear.stl
//   npm run export -- models/gear.js out/banh-rang.stl teeth=24 radius=30
//   npm run export -- --all                -> xuất tất cả model trong models/
import { writeFileSync, mkdirSync, readdirSync } from 'node:fs'
import { resolve, basename, dirname, join } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { serialize } from '@jscad/stl-serializer'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const args = process.argv.slice(2)

const parseValue = (v) => (v === 'true' ? true : v === 'false' ? false : v !== '' && !isNaN(v) ? Number(v) : v)

const defaults = (defs = []) => Object.fromEntries(
  defs.filter((d) => d.type !== 'group').map((d) => [d.name, d.type === 'checkbox' ? (d.checked ?? d.initial ?? false) : (d.initial ?? d.default ?? (d.values ? d.values[0] : undefined))])
)

const exportOne = async (modelPath, outPath, overrides = {}) => {
  const abs = resolve(process.cwd(), modelPath)
  const mod = await import(pathToFileURL(abs).href)
  if (typeof mod.main !== 'function') throw new Error(`${modelPath} không export hàm main()`)
  const params = { ...defaults(mod.getParameterDefinitions ? mod.getParameterDefinitions() : []), ...overrides }
  const solids = [mod.main(params)].flat(Infinity)
  const data = serialize({ binary: true }, ...solids)
  const out = resolve(process.cwd(), outPath || join(root, 'out', basename(abs, '.js') + '.stl'))
  mkdirSync(dirname(out), { recursive: true })
  writeFileSync(out, Buffer.concat(data.map((b) => Buffer.from(b))))
  console.log(`✔ ${modelPath} -> ${out}  (params: ${JSON.stringify(params)})`)
}

try {
  if (args[0] === '--all') {
    for (const f of readdirSync(join(root, 'models')).filter((f) => f.endsWith('.js'))) {
      await exportOne(join(root, 'models', f))
    }
  } else {
    const positional = args.filter((a) => !a.includes('='))
    const overrides = Object.fromEntries(args.filter((a) => a.includes('=')).map((a) => {
      const i = a.indexOf('=')
      return [a.slice(0, i), parseValue(a.slice(i + 1))]
    }))
    await exportOne(positional[0] || join(root, 'models', 'main.js'), positional[1], overrides)
  }
} catch (err) {
  console.error('✘ Lỗi:', err.message)
  process.exit(1)
}
