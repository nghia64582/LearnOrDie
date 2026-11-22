import { PARAM_GROUPS, ALL_PARAMS, PRESETS, GROUP_COLORS, defaultParams } from './config.js'
import { Sim } from './sim.js'
import { computeLayout, render } from './render.js'

const $ = id => document.getElementById(id)
const params = defaultParams()
let status = 'stopped' // stopped | running | paused
let speed = 1
let pendingStructural = false
const events = []
let sim

// ---------- Nhật ký sự kiện ----------
function onEvent (e) {
  events.unshift(e)
  if (events.length > 80) events.pop()
  eventsDirty = true
}
let eventsDirty = true
function renderEvents () {
  if (!eventsDirty) return
  eventsDirty = false
  $('events').innerHTML = events.length
    ? events.map(e => `<li class="${e.kind}"><span class="t">${(e.t / 1000).toFixed(1)}s</span>${e.text}</li>`).join('')
    : '<li class="t">Chưa có sự kiện. Thử bấm vào broker / consumer trên canvas, hoặc đổi số consumer khi đang chạy.</li>'
}

function newSim () {
  events.length = 0
  eventsDirty = true
  sim = new Sim(params, onEvent)
  pendingStructural = false
  $('pending').hidden = true
}

// ---------- Form tham số ----------
const inputs = {}
function buildParams () {
  const root = $('params')
  for (const grp of PARAM_GROUPS) {
    const h = document.createElement('h2')
    h.textContent = grp.title
    root.appendChild(h)
    if (grp.note) {
      const n = document.createElement('p')
      n.className = 'note'
      n.textContent = '🔁 ' + grp.note
      root.appendChild(n)
    }
    for (const d of grp.params) {
      const wrap = document.createElement('div')
      wrap.className = 'param' + (d.structural ? ' structural' : '')
      const lbl = document.createElement('div')
      lbl.className = 'lbl'
      lbl.innerHTML = `<span>${d.label}</span><span class="help" data-tip="${d.help.replace(/"/g, '&quot;')}">?</span>`
      wrap.appendChild(lbl)
      const row = document.createElement('div')
      row.className = 'row'
      if (d.type === 'select') {
        const sel = document.createElement('select')
        for (const [v, t] of d.options) sel.add(new Option(t, v))
        sel.value = params[d.key]
        sel.addEventListener('change', () => setParam(d, sel.value))
        row.appendChild(sel)
        inputs[d.key] = { set: v => { sel.value = v } }
      } else {
        const rg = document.createElement('input')
        Object.assign(rg, { type: 'range', min: d.min, max: d.max, step: d.step, value: params[d.key] })
        const num = document.createElement('input')
        Object.assign(num, { type: 'number', min: d.min, max: d.max, step: d.step, value: params[d.key] })
        rg.addEventListener('input', () => { num.value = rg.value; setParam(d, Number(rg.value)) })
        num.addEventListener('change', () => {
          let v = Number(num.value)
          if (!Number.isFinite(v)) v = d.def
          v = Math.min(d.max, Math.max(d.min, v))
          num.value = v; rg.value = v
          setParam(d, v)
        })
        row.append(rg, num)
        inputs[d.key] = { set: v => { rg.value = v; num.value = v } }
      }
      wrap.appendChild(row)
      root.appendChild(wrap)
    }
  }
}

function setParam (d, v) {
  if (params[d.key] === v) return
  params[d.key] = v
  if (d.key === 'replicationFactor' && v > params.brokers) {
    onEvent({ t: sim.t, text: `Replication factor ${v} > số broker ${params.brokers} → thực tế dùng RF = ${params.brokers}`, kind: 'warn' })
  }
  if (d.structural) {
    if (status === 'stopped') newSim()
    else { pendingStructural = true; $('pending').hidden = false }
    return
  }
  if (d.key === 'producers') sim.syncProducers()
  if (d.key === 'consumersPerGroup') for (const g of sim.groups) sim.setConsumerCount(g, v, status !== 'stopped')
}

function applyPreset (id) {
  const pr = PRESETS.find(p => p.id === id)
  Object.assign(params, defaultParams(), pr.set)
  for (const d of ALL_PARAMS) inputs[d.key].set(params[d.key])
  $('hint').innerHTML = '💡 ' + pr.hint
  newSim()
  setStatus('running')
}

// ---------- Điều khiển ----------
function setStatus (s) {
  status = s
  const el = $('status')
  el.textContent = { stopped: 'Đã dừng', running: 'Đang chạy', paused: 'Tạm dừng' }[s]
  el.className = s
  $('btn-run').classList.toggle('active', s === 'running')
  if (s === 'running') $('hint').innerHTML = $('hint').innerHTML.replace(' Bấm <b>▶ Chạy</b> để bắt đầu.', '')
  $('btn-pause').classList.toggle('active', s === 'paused')
}
$('btn-run').onclick = () => setStatus('running')
$('btn-pause').onclick = () => { if (status === 'running') setStatus('paused') }
$('btn-stop').onclick = () => { newSim(); setStatus('stopped') }
$('speed').oninput = e => { speed = Number(e.target.value); $('speed-val').textContent = speed + 'x' }
for (const p of PRESETS) $('preset').add(new Option(p.name, p.id))
$('preset').onchange = e => applyPreset(e.target.value)

// ---------- Canvas, hover, click ----------
const canvas = $('canvas')
const ctx = canvas.getContext('2d')
const tooltip = $('tooltip')
const hits = []
let mouse = null
let hover = null
let W = 1000; let H = 600; let L

function resize () {
  W = Math.max(1050, $('canvas-wrap').clientWidth)
}
window.addEventListener('resize', resize)

canvas.addEventListener('mousemove', e => {
  const r = canvas.getBoundingClientRect()
  mouse = { x: e.clientX - r.left, y: e.clientY - r.top, cx: e.clientX, cy: e.clientY }
})
canvas.addEventListener('mouseleave', () => { mouse = null; hover = null; tooltip.hidden = true })
canvas.addEventListener('click', () => {
  if (!hover || !hover.action) return
  const a = hover.action
  if (a.type === 'broker') sim.toggleBroker(a.id)
  if (a.type === 'consumer') sim.crashConsumer(a.group, a.consumer)
})
document.addEventListener('mouseover', e => {
  const t = e.target.closest && e.target.closest('[data-tip]')
  if (!t) return
  showTip(t.dataset.tip, e.clientX, e.clientY)
  t.addEventListener('mouseleave', () => { tooltip.hidden = true }, { once: true })
})
function showTip (html, x, y) {
  tooltip.innerHTML = html
  tooltip.hidden = false
  const tw = tooltip.offsetWidth; const th = tooltip.offsetHeight
  tooltip.style.left = Math.min(window.innerWidth - tw - 8, x + 14) + 'px'
  tooltip.style.top = Math.min(window.innerHeight - th - 8, y + 14) + 'px'
}

function updateHover () {
  if (!mouse) return
  hover = null
  for (let i = hits.length - 1; i >= 0; i--) {
    const h = hits[i]
    if (mouse.x >= h.x && mouse.x <= h.x + h.w && mouse.y >= h.y && mouse.y <= h.y + h.h) { hover = h; break }
  }
  canvas.style.cursor = hover && hover.action ? 'pointer' : 'default'
  if (hover) showTip(hover.tip, mouse.cx, mouse.cy)
  else tooltip.hidden = true
}

// ---------- Số liệu ----------
function fmt (n) { return Number.isInteger(n) ? String(n) : n.toFixed(1) }
function recentRate (sel) {
  const h = sim.history.slice(-3)
  if (!h.length) return 0
  return h.reduce((s, x) => s + sel(x), 0) / h.length
}
function renderMetrics () {
  const s = sim.stats
  const cards = [
    ['Throughput vào', fmt(recentRate(x => x.in)), 'msg/s ghi vào partition (TB 3s)'],
    ...sim.groups.map((g, i) => [`<span style="color:${GROUP_COLORS[i]}">Throughput ra · ${g.name}</span>`, fmt(recentRate(x => x.out[i] || 0)), 'msg/s xử lý xong (TB 3s)']),
    ['Tổng message', s.appended, `produce ${s.produced} · ack ${s.acked}`],
    ...sim.groups.map((g, i) => [`<span style="color:${GROUP_COLORS[i]}">Lag · ${g.name}</span>`, sim.groupLag(g), `đã xử lý ${g.consumed} · bỏ qua do retention ${g.skipped}`]),
    ['Lỗi / gửi lại', `${s.failed} / ${s.retried}`, 'gửi vào partition không có leader'],
    ['Message MẤT', s.lost, 'đã gửi nhưng không còn trong Kafka (acks=0 lỗi, hoặc acks=1 bị cắt khi đổi leader)'],
    ['Retention đã xoá', s.deleted, `giữ tối đa ${params.retention} msg/partition`]
  ]
  $('metrics').innerHTML = cards.map(([k, v, sub]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${sub}</div></div>`).join('')

  const maxLag = Math.max(1, ...sim.parts.flatMap(p => sim.groups.map(g => sim.lag(g, p))))
  let html = '<table><tr><th>Partition</th><th>Leader</th><th>ISR</th><th>Start</th><th>LEO</th><th>HW</th>' +
    sim.groups.map((g, i) => `<th style="color:${GROUP_COLORS[i]}">Lag ${g.name}</th>`).join('') + '</tr>'
  for (const p of sim.parts) {
    const isr = p.replicas.filter(r => r.inSync && sim.brokers[r.broker].alive).map(r => 'B' + (r.broker + 1)).join(',')
    html += `<tr><td>${p.key}</td><td>${p.leader < 0 ? '<span style="color:#f87171">offline</span>' : 'B' + (p.leader + 1)}</td><td>${isr || '-'}</td><td>${p.logStart}</td><td>${p.leo}</td><td>${p.hw}</td>` +
      sim.groups.map((g, i) => { const l = sim.lag(g, p); return `<td style="color:${GROUP_COLORS[i]}">${l}<span class="lagbar" style="width:${Math.round(40 * l / maxLag)}px"></span></td>` }).join('') + '</tr>'
  }
  $('lag-table').innerHTML = html + '</table>'
  drawChart($('chart-tp'), [
    { name: 'vào', color: '#38bdf8', data: sim.history.map(h => h.in) },
    ...sim.groups.map((g, i) => ({ name: 'ra ' + g.name, color: GROUP_COLORS[i], data: sim.history.map(h => h.out[i] || 0) }))
  ])
  drawChart($('chart-lag'), sim.groups.map((g, i) => ({ name: g.name, color: GROUP_COLORS[i], data: sim.history.map(h => h.lag[i] || 0) })))
}

function drawChart (cv, series) {
  const dpr = window.devicePixelRatio || 1
  const w = cv.clientWidth; const h = cv.clientHeight
  if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr }
  const c = cv.getContext('2d')
  c.setTransform(dpr, 0, 0, dpr, 0, 0)
  c.clearRect(0, 0, w, h)
  const max = Math.max(1, ...series.flatMap(s => s.data))
  const left = 32; const bottom = h - 16; const top = 8
  c.strokeStyle = '#1e293b'; c.fillStyle = '#64748b'; c.font = '10px system-ui'
  for (let i = 0; i <= 2; i++) {
    const y = top + (bottom - top) * i / 2
    c.beginPath(); c.moveTo(left, y); c.lineTo(w, y); c.stroke()
    c.fillText(fmt(max * (1 - i / 2)), 2, y + 3)
  }
  c.fillText('60 giây gần nhất →', left, h - 3)
  series.forEach((s, si) => {
    c.strokeStyle = s.color; c.lineWidth = 2
    c.beginPath()
    s.data.forEach((v, i) => {
      const x = left + (w - left) * (i + 60 - s.data.length) / 59
      const y = bottom - (bottom - top) * v / max
      i ? c.lineTo(x, y) : c.moveTo(x, y)
    })
    c.stroke()
    c.fillStyle = s.color
    c.fillText('■ ' + s.name, w - 90, top + 8 + si * 12)
  })
  c.lineWidth = 1
}

// ---------- Vòng lặp ----------
let last = performance.now()
let lastMetrics = 0
function frame (now) {
  const dtReal = Math.min(100, now - last)
  last = now
  if (status === 'running') {
    let dt = dtReal * speed
    while (dt > 0) { const s = Math.min(20, dt); sim.step(s); dt -= s }
  }
  resize()
  L = computeLayout(sim, W)
  H = L.height
  const dpr = window.devicePixelRatio || 1
  if (canvas.width !== W * dpr || canvas.height !== H * dpr) {
    canvas.width = W * dpr; canvas.height = H * dpr
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px'
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  render(ctx, sim, W, H, L, hits, hover)
  updateHover()
  $('clock').firstChild.textContent = `⏱ ${(sim.t / 1000).toFixed(1)}s · `
  if (now - lastMetrics > 250) { lastMetrics = now; renderMetrics(); renderEvents() }
  requestAnimationFrame(frame)
}

buildParams()
newSim()
$('hint').innerHTML = '💡 ' + PRESETS[0].hint + ' Bấm <b>▶ Chạy</b> để bắt đầu.'
setStatus('stopped')
window.__kafkaSim = () => sim // tiện debug trong DevTools
requestAnimationFrame(frame)
