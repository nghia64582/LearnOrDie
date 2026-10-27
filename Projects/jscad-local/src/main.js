import { prepareRender, drawCommands, cameras, controls, entitiesFromSolids } from '@jscad/regl-renderer'
import { serialize } from '@jscad/stl-serializer'
import { defaultParams, renderParamsForm } from './params.js'

// Tự động tìm tất cả model trong thư mục models/
const modelModules = import.meta.glob('../models/*.js')
const modelNames = Object.keys(modelModules).map((p) => p.replace('../models/', '').replace(/\.js$/, '')).sort()

const $ = (id) => document.getElementById(id)
const viewer = $('viewer')
const select = $('model-select')
const status = $('status')
const paramsBox = $('params')

const flatten = (arr) => (Array.isArray(arr) ? arr.reduce((a, x) => a.concat(flatten(x)), []) : [arr])

// ---------- Viewer (regl-renderer) ----------
const perspectiveCamera = cameras.perspective
const orbitControls = controls.orbit

const state = {
  camera: Object.assign({}, perspectiveCamera.defaults),
  controls: orbitControls.defaults,
  solids: [],
  entities: [],
  params: {},
  defs: [],
  model: null,
  needsRender: true
}
state.camera.position = [80, -120, 90]

const grid = { visuals: { drawCmd: 'drawGrid', show: true, color: [0.5, 0.5, 0.5, 0.6], subColor: [0.4, 0.4, 0.4, 0.3] }, size: [400, 400], ticks: [10, 1] }
const axis = { visuals: { drawCmd: 'drawAxis', show: true }, size: 100 }

const renderOptions = {
  glOptions: { container: viewer },
  camera: state.camera,
  drawCommands: {
    drawAxis: drawCommands.drawAxis,
    drawGrid: drawCommands.drawGrid,
    drawLines: drawCommands.drawLines,
    drawMesh: drawCommands.drawMesh
  },
  rendering: { background: [0.12, 0.12, 0.12, 1], meshColor: [0.6, 0.6, 0.9, 1] },
  entities: [grid, axis]
}
const render = prepareRender(renderOptions)

const resize = () => {
  const { width, height } = viewer.getBoundingClientRect()
  perspectiveCamera.setProjection(state.camera, state.camera, { width, height })
  state.needsRender = true
}
window.addEventListener('resize', resize)
resize()

const updateAndRender = () => {
  const updated = orbitControls.update({ controls: state.controls, camera: state.camera })
  state.controls = { ...state.controls, ...updated.controls }
  if (state.controls.changed) state.needsRender = true
  state.camera.position = updated.camera.position
  perspectiveCamera.update(state.camera)
  if (state.needsRender) {
    renderOptions.entities = [grid, axis, ...state.entities]
    render(renderOptions)
    state.needsRender = false
  }
  requestAnimationFrame(updateAndRender)
}
requestAnimationFrame(updateAndRender)

// Chuột: trái = xoay, phải/shift = pan, lăn = zoom
let last = null
let panMode = false
viewer.addEventListener('contextmenu', (e) => e.preventDefault())
viewer.addEventListener('pointerdown', (e) => {
  last = [e.clientX, e.clientY]
  panMode = e.button === 2 || e.shiftKey
  viewer.setPointerCapture(e.pointerId)
})
viewer.addEventListener('pointerup', () => { last = null })
viewer.addEventListener('pointermove', (e) => {
  if (!last) return
  const dx = e.clientX - last[0]
  const dy = e.clientY - last[1]
  last = [e.clientX, e.clientY]
  if (panMode) {
    const u = orbitControls.pan({ controls: state.controls, camera: state.camera, speed: 1 }, [dx, dy])
    state.camera.position = u.camera.position
    state.camera.target = u.camera.target
  } else {
    const u = orbitControls.rotate({ controls: state.controls, camera: state.camera, speed: 0.003 }, [-dx, dy])
    state.controls = { ...state.controls, ...u.controls }
  }
  state.needsRender = true
})
viewer.addEventListener('wheel', (e) => {
  e.preventDefault()
  const u = orbitControls.zoom({ controls: state.controls, camera: state.camera, speed: 0.08 }, Math.sign(e.deltaY) * 2)
  state.controls = { ...state.controls, ...u.controls }
  state.needsRender = true
}, { passive: false })

const zoomToFit = () => {
  if (!state.entities.length) return
  const u = orbitControls.zoomToFit({ controls: state.controls, camera: state.camera, entities: state.entities })
  state.controls = { ...state.controls, ...u.controls }
  state.needsRender = true
}

// ---------- Model ----------
const setStatus = (msg, isError = false) => {
  status.textContent = msg
  status.className = isError ? 'error' : ''
}

const rebuild = () => {
  try {
    const t0 = performance.now()
    const result = state.model.main({ ...state.params })
    state.solids = flatten(result).filter(Boolean)
    state.entities = entitiesFromSolids({}, ...state.solids)
    state.needsRender = true
    setStatus(`OK: ${state.solids.length} vật thể · ${Math.round(performance.now() - t0)} ms`)
  } catch (err) {
    console.error(err)
    setStatus('Lỗi khi chạy main():\n' + err.message, true)
  }
}

const loadModel = async (name, firstLoad) => {
  try {
    setStatus('Đang tải ' + name + '...')
    const mod = await modelModules[`../models/${name}.js`]()
    if (typeof mod.main !== 'function') throw new Error('File model phải export hàm main()')
    state.model = mod
    state.defs = mod.getParameterDefinitions ? mod.getParameterDefinitions() : []
    // Giữ lại giá trị tham số đã chỉnh (qua các lần reload)
    const saved = JSON.parse(sessionStorage.getItem('params:' + name) || '{}')
    state.params = { ...defaultParams(state.defs), ...saved }
    renderParamsForm(paramsBox, state.defs, state.params, (k, v) => {
      state.params[k] = v
      sessionStorage.setItem('params:' + name, JSON.stringify(state.params))
      rebuild()
    })
    rebuild()
    if (firstLoad) zoomToFit()
  } catch (err) {
    console.error(err)
    setStatus('Lỗi khi tải model:\n' + err.message, true)
  }
}

for (const n of modelNames) {
  const o = document.createElement('option')
  o.value = n
  o.textContent = n
  select.appendChild(o)
}
const initial = decodeURIComponent(location.hash.slice(1)) || (modelNames.includes('main') ? 'main' : modelNames[0])
select.value = modelNames.includes(initial) ? initial : modelNames[0]
select.onchange = () => {
  location.hash = select.value
  loadModel(select.value, true)
}
window.addEventListener('hashchange', () => {
  const n = decodeURIComponent(location.hash.slice(1))
  if (modelNames.includes(n) && n !== select.value) {
    select.value = n
    loadModel(n, true)
  }
})
$('btn-fit').onclick = zoomToFit
$('btn-stl').onclick = () => {
  try {
    const data = serialize({ binary: true }, ...state.solids)
    const blob = new Blob(data, { type: 'application/octet-stream' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = select.value + '.stl'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (err) {
    setStatus('Xuất STL lỗi: ' + err.message, true)
  }
}

if (modelNames.length === 0) setStatus('Không có model nào trong thư mục models/', true)
else loadModel(select.value, true)
