// Vẽ trạng thái mô phỏng lên canvas + tạo vùng hover/click.
import { GROUP_COLORS, BROKER_COLORS } from './config.js'

const PAD = 14
const PROD_W = 160
const CONS_W = 250
const ROW_H = 44
const CELL = 15
const LBL_W = 168

function rr (ctx, x, y, w, h, r = 6) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
function fit (ctx, text, maxW) {
  if (ctx.measureText(text).width <= maxW) return text
  while (text.length > 1 && ctx.measureText(text + '…').width > maxW) text = text.slice(0, -1)
  return text + '…'
}
const ease = t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2

export function computeLayout (sim, W) {
  const L = { prod: new Map(), part: new Map(), cons: new Map(), group: new Map(), broker: new Map(), topic: new Map() }
  const cx = PAD + PROD_W + 70
  const cx2 = W - PAD - CONS_W - 70
  L.cluster = { x: cx - 12, y: PAD, w: cx2 - cx + 24 }
  // brokers
  const B = sim.brokers.length
  const bw = Math.min(170, (cx2 - cx - (B - 1) * 10) / B)
  sim.brokers.forEach((b, i) => L.broker.set(b, { x: cx + i * (bw + 10), y: PAD + 26, w: bw, h: 50 }))
  let y = PAD + 26 + 50 + 18
  for (const t of sim.topics) {
    L.topic.set(t, { x: cx, y, w: cx2 - cx })
    y += 22
    for (const part of t.parts) {
      const logX = cx + LBL_W
      const logX2 = cx2 - 8
      L.part.set(part, { x: cx, y, w: cx2 - cx, h: ROW_H, logX, logX2, visible: Math.max(4, Math.floor((logX2 - logX) / CELL)) })
      y += ROW_H + 6
    }
    y += 10
  }
  L.cluster.h = y - PAD
  // producers
  let py = PAD + 26
  for (const pr of sim.producers) { L.prod.set(pr, { x: PAD, y: py, w: PROD_W, h: 64 }); py += 74 }
  // consumer groups
  let gy = PAD + 26
  const gx = W - PAD - CONS_W
  for (const g of sim.groups) {
    const h = 30 + Math.max(1, g.consumers.length) * 50 + 6
    L.group.set(g, { x: gx, y: gy, w: CONS_W, h })
    g.consumers.forEach((c, i) => L.cons.set(c, { x: gx + 8, y: gy + 30 + i * 50, w: CONS_W - 16, h: 44 }))
    gy += h + 14
  }
  L.height = Math.max(y, py, gy) + PAD
  return L
}

function windowStart (part, lay) {
  return Math.max(part.logStart, part.leo - lay.visible)
}
function offsetX (part, lay, off) {
  return lay.logX + (off - windowStart(part, lay)) * CELL
}

export function render (ctx, sim, W, H, L, hits, hover) {
  hits.length = 0
  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#0b1220'
  ctx.fillRect(0, 0, W, H)
  ctx.textBaseline = 'middle'

  // column titles
  ctx.font = 'bold 13px system-ui, sans-serif'
  ctx.fillStyle = '#94a3b8'
  ctx.fillText('PRODUCER', PAD, PAD + 8)
  ctx.fillText('KAFKA CLUSTER', L.cluster.x + 12, PAD + 8)
  ctx.fillText('CONSUMER GROUP', W - PAD - CONS_W, PAD + 8)

  // cluster background
  rr(ctx, L.cluster.x, L.cluster.y + 20, L.cluster.w, L.cluster.h - 14, 10)
  ctx.fillStyle = '#111a2e'
  ctx.fill()
  ctx.strokeStyle = '#1e2b47'
  ctx.stroke()

  drawBrokers(ctx, sim, L, hits)
  drawPartitions(ctx, sim, L, hits)
  drawAssignmentLines(ctx, sim, L)
  drawProducers(ctx, sim, L, hits)
  drawGroups(ctx, sim, L, hits)
  drawFlights(ctx, sim, L)

  if (hover) {
    ctx.strokeStyle = 'rgba(255,255,255,0.6)'
    ctx.lineWidth = 1.5
    rr(ctx, hover.x - 2, hover.y - 2, hover.w + 4, hover.h + 4, 7)
    ctx.stroke()
    ctx.lineWidth = 1
  }
}

function drawBrokers (ctx, sim, L, hits) {
  for (const b of sim.brokers) {
    const r = L.broker.get(b)
    let lead = 0; let reps = 0
    for (const p of sim.parts) {
      if (p.leader === b.id) lead++
      if (p.replicas.some(x => x.broker === b.id)) reps++
    }
    rr(ctx, r.x, r.y, r.w, r.h, 8)
    ctx.fillStyle = b.alive ? '#16233d' : '#3b1219'
    ctx.fill()
    ctx.strokeStyle = b.alive ? BROKER_COLORS[b.id] : '#ef4444'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.lineWidth = 1
    ctx.fillStyle = BROKER_COLORS[b.id]
    ctx.font = 'bold 13px system-ui, sans-serif'
    ctx.fillText(`Broker ${b.id + 1}`, r.x + 10, r.y + 15)
    ctx.font = '11px system-ui, sans-serif'
    ctx.fillStyle = b.alive ? '#cbd5e1' : '#fca5a5'
    ctx.fillText(b.alive ? `★ leader: ${lead} · replica: ${reps}` : '💥 ĐÃ SẬP (bấm để bật)', r.x + 10, r.y + 35)
    ctx.fillStyle = b.alive ? '#22c55e' : '#ef4444'
    ctx.beginPath(); ctx.arc(r.x + r.w - 12, r.y + 14, 5, 0, Math.PI * 2); ctx.fill()
    hits.push({ ...r, action: { type: 'broker', id: b.id },
      tip: `<b>Broker ${b.id + 1}</b> ${b.alive ? '🟢 đang chạy' : '🔴 đã sập'}<br>Làm leader cho ${lead} partition, giữ bản sao của ${reps} partition.<br>Producer và consumer chỉ làm việc với <b>leader</b> của partition; follower chỉ sao chép dữ liệu.<br><i>Bấm để ${b.alive ? 'làm broker này sập' : 'bật lại broker'}.</i>` })
  }
}

function drawPartitions (ctx, sim, L, hits) {
  for (const t of sim.topics) {
    const tl = L.topic.get(t)
    ctx.font = 'bold 12px system-ui, sans-serif'
    ctx.fillStyle = '#e2e8f0'
    ctx.fillText(`📁 ${t.name}  (${t.parts.length} partition, RF=${sim.rf})`, tl.x, tl.y + 9)
    hits.push({ x: tl.x, y: tl.y, w: 260, h: 18,
      tip: `<b>Topic ${t.name}</b><br>Một topic gồm ${t.parts.length} partition. Mỗi partition có ${sim.rf} bản sao (replication factor).` })
    for (const part of t.parts) drawPartition(ctx, sim, part, L.part.get(part), hits)
  }
}

function drawPartition (ctx, sim, part, lay, hits) {
  const { x, y, w, h, logX, visible } = lay
  const offline = part.leader < 0
  rr(ctx, x, y, w, h, 6)
  ctx.fillStyle = offline ? '#3b1219' : (sim.t < part.flashUntil ? '#4c1d24' : '#0f1830')
  ctx.fill()
  ctx.strokeStyle = '#24324f'
  ctx.stroke()

  // label + replicas
  ctx.font = 'bold 12px system-ui, sans-serif'
  ctx.fillStyle = '#e2e8f0'
  ctx.fillText(`P${part.idx}`, x + 8, y + 13)
  ctx.font = '10px system-ui, sans-serif'
  ctx.fillStyle = '#94a3b8'
  ctx.fillText(offline ? 'OFFLINE' : `LEO ${part.leo} · HW ${part.hw}`, x + 30, y + 13)
  let rx = x + 8
  for (const r of part.replicas) {
    const isLeader = r.broker === part.leader
    const alive = sim.brokers[r.broker].alive
    const label = `${isLeader ? '★' : ''}B${r.broker + 1}`
    const cw = isLeader ? 34 : 28
    rr(ctx, rx, y + 24, cw, 15, 4)
    ctx.fillStyle = !alive ? '#4b5563' : isLeader ? BROKER_COLORS[r.broker] : r.inSync ? '#14532d' : '#78350f'
    ctx.fill()
    ctx.fillStyle = isLeader && alive ? '#0b1220' : '#e5e7eb'
    ctx.font = 'bold 10px system-ui, sans-serif'
    ctx.fillText(label, rx + 4, y + 32)
    hits.push({ x: rx, y: y + 24, w: cw, h: 15,
      tip: `<b>${part.key} trên Broker ${r.broker + 1}</b>: ${isLeader ? '★ LEADER (nhận ghi/đọc)' : 'follower (sao chép)'}<br>LEO của replica: ${r.leo}<br>${!alive ? '🔴 Broker đã sập' : r.inSync ? '🟢 Trong ISR (in-sync replica)' : '🟠 Ngoài ISR (đang tụt lại / đồng bộ lại)'}` })
    rx += cw + 4
  }

  // log cells
  const ws = windowStart(part, lay)
  const cy = y + 9
  const ch = 18
  if (part.leo === part.logStart) {
    ctx.fillStyle = '#475569'
    ctx.font = 'italic 11px system-ui, sans-serif'
    ctx.fillText(offline ? 'partition không có leader → không ghi/đọc được' : 'log trống', logX + 4, cy + ch / 2)
  }
  for (let off = ws; off < part.leo; off++) {
    const e = part.log[off - part.logStart]
    if (!e) continue
    const cx = logX + (off - ws) * CELL
    const age = sim.t - e.t
    const pop = age < 250 ? 1 + (1 - age / 250) * 0.35 : 1
    const cw = (CELL - 2) * pop
    const chh = ch * pop
    ctx.globalAlpha = off >= part.hw ? 0.35 : 1
    ctx.fillStyle = e.color
    ctx.fillRect(cx + 1 + (CELL - 2 - cw) / 2, cy + (ch - chh) / 2, cw, chh)
    ctx.globalAlpha = 1
    if (off % 5 === 0) {
      ctx.fillStyle = '#64748b'
      ctx.font = '9px system-ui, sans-serif'
      ctx.fillText(String(off), cx + 1, cy + ch + 8)
    }
  }
  if (ws > part.logStart || part.logStart > 0) {
    ctx.fillStyle = '#64748b'
    ctx.font = '9px system-ui, sans-serif'
    ctx.fillText(ws > part.logStart ? '◀…' : `🗑${part.logStart}`, logX - 22, cy + ch / 2)
  }

  // follower LEO ticks
  for (const r of part.replicas) {
    if (r.broker === part.leader || r.leo < ws || r.leo > part.leo) continue
    const fx = offsetX(part, lay, r.leo)
    ctx.fillStyle = BROKER_COLORS[r.broker]
    ctx.beginPath(); ctx.moveTo(fx, cy - 1); ctx.lineTo(fx - 3, cy - 6); ctx.lineTo(fx + 3, cy - 6); ctx.fill()
  }
  // HW line
  if (!offline && part.hw >= ws) {
    const hx = offsetX(part, lay, part.hw)
    ctx.strokeStyle = '#f87171'
    ctx.setLineDash([3, 2])
    ctx.beginPath(); ctx.moveTo(hx, cy - 4); ctx.lineTo(hx, cy + ch + 2); ctx.stroke()
    ctx.setLineDash([])
  }
  // committed offsets per group
  sim.groups.forEach((g, gi) => {
    const c = g.committed[part.key]
    const col = GROUP_COLORS[gi]
    const my = cy + ch + 3 + gi * 0
    let gx
    if (c < ws) { gx = logX - 4 } else gx = offsetX(part, lay, c)
    ctx.fillStyle = col
    ctx.beginPath(); ctx.moveTo(gx, my); ctx.lineTo(gx - 4, my + 7); ctx.lineTo(gx + 4, my + 7); ctx.fill()
    if (c < ws) { ctx.font = '9px system-ui'; ctx.fillText(String(c), gx - 16, my + 4) }
  })
  // lag text
  const lags = sim.groups.map(g => sim.lag(g, part))
  ctx.font = '10px system-ui, sans-serif'
  ctx.textAlign = 'right'
  sim.groups.forEach((g, gi) => {
    ctx.fillStyle = GROUP_COLORS[gi]
    ctx.fillText(`lag ${lags[gi]}`, x + w - 6 - gi * 50, y + h - 7)
  })
  ctx.textAlign = 'left'

  const groupsInfo = sim.groups.map((g, gi) => `<span style="color:${GROUP_COLORS[gi]}">▲ ${g.name}</span>: committed ${g.committed[part.key]}, lag <b>${lags[gi]}</b>`).join('<br>')
  hits.push({ x: logX, y, w: lay.logX2 - logX, h,
    tip: `<b>Partition ${part.key}</b> – log chỉ ghi nối (append-only)<br>` +
      `Offset còn lưu: ${part.logStart} → ${part.leo - 1}${part.logStart > 0 ? ` (${part.logStart} message cũ đã bị retention xoá)` : ''}<br>` +
      `<b>LEO</b> (log end offset, offset tiếp theo sẽ ghi): ${part.leo}<br>` +
      `<b style="color:#f87171">HW</b> (high watermark, consumer chỉ đọc tới đây): ${part.hw}<br>` +
      `Ô mờ = đã ghi ở leader nhưng chưa đủ ISR sao chép.<br>${groupsInfo}` +
      (part.lost ? `<br>✂️ Đã bị cắt khi đổi leader: ${part.lost}` : '') })
}

function drawAssignmentLines (ctx, sim, L) {
  sim.groups.forEach((g, gi) => {
    for (const c of g.consumers) {
      const cl = L.cons.get(c)
      for (const part of c.assigned) {
        const pl = L.part.get(part)
        const x1 = pl.x + pl.w; const y1 = pl.y + pl.h / 2
        const x2 = cl.x; const y2 = cl.y + cl.h / 2
        ctx.strokeStyle = GROUP_COLORS[gi]
        ctx.globalAlpha = 0.35
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.bezierCurveTo(x1 + 40, y1, x2 - 40, y2, x2, y2)
        ctx.stroke()
        ctx.globalAlpha = 1
      }
    }
  })
}

function drawProducers (ctx, sim, L, hits) {
  for (const pr of sim.producers) {
    const r = L.prod.get(pr)
    rr(ctx, r.x, r.y, r.w, r.h, 8)
    ctx.fillStyle = '#132037'
    ctx.fill()
    ctx.strokeStyle = pr.color
    ctx.stroke()
    ctx.fillStyle = pr.color
    ctx.fillRect(r.x, r.y + 6, 4, r.h - 12)
    ctx.font = 'bold 12px system-ui, sans-serif'
    ctx.fillStyle = '#e2e8f0'
    ctx.fillText(`📤 ${pr.name}`, r.x + 10, r.y + 13)
    ctx.font = '11px system-ui, sans-serif'
    ctx.fillStyle = '#94a3b8'
    ctx.fillText(`→ ${sim.topics[pr.topic].name} · ${sim.p.rate} msg/s`, r.x + 10, r.y + 31)
    ctx.fillText(`gửi ${pr.sent} · ack ${pr.acked}${pr.pending.length ? ` · chờ ${pr.pending.length}` : ''}`, r.x + 10, r.y + 49)
    hits.push({ ...r,
      tip: `<b>${pr.name}</b> ghi vào <b>${sim.topics[pr.topic].name}</b><br>Đã gửi: ${pr.sent}, đã nhận ack: ${pr.acked}<br>Đang chờ ack (acks=all): ${pr.pending.length}<br>Chế độ: acks=${sim.p.acks}, partitioner: ${sim.p.partitioner}` })
  }
}

function drawGroups (ctx, sim, L, hits) {
  sim.groups.forEach((g, gi) => {
    const r = L.group.get(g)
    const col = GROUP_COLORS[gi]
    rr(ctx, r.x, r.y, r.w, r.h, 10)
    ctx.fillStyle = '#111a2e'
    ctx.fill()
    ctx.strokeStyle = col
    ctx.stroke()
    ctx.font = 'bold 12px system-ui, sans-serif'
    ctx.fillStyle = col
    ctx.fillText(`👥 Group "${g.name}"`, r.x + 10, r.y + 15)
    ctx.textAlign = 'right'
    ctx.font = '11px system-ui, sans-serif'
    if (g.state === 'rebalancing') {
      const left = Math.max(0, g.rebalanceUntil - sim.t)
      ctx.fillStyle = '#fbbf24'
      const spin = '◐◓◑◒'[Math.floor(sim.t / 150) % 4]
      ctx.fillText(`${spin} rebalance… ${(left / 1000).toFixed(1)}s`, r.x + r.w - 10, r.y + 15)
    } else {
      ctx.fillStyle = '#94a3b8'
      ctx.fillText(`lag ${sim.groupLag(g)} · đã xử lý ${g.consumed}`, r.x + r.w - 10, r.y + 15)
    }
    ctx.textAlign = 'left'
    hits.push({ x: r.x, y: r.y, w: r.w, h: 26,
      tip: `<b>Consumer group "${g.name}"</b><br>Trạng thái: ${g.state === 'rebalancing' ? '🔄 đang rebalance (ngừng đọc)' : '✅ ổn định'}<br>Tổng lag: ${sim.groupLag(g)} · Đã xử lý: ${g.consumed} · Bỏ qua do retention: ${g.skipped}<br>Mỗi partition chỉ được giao cho 1 consumer trong group.` })
    if (!g.consumers.length) {
      ctx.fillStyle = '#64748b'
      ctx.font = 'italic 11px system-ui, sans-serif'
      ctx.fillText('Không có consumer nào → lag tăng dần', r.x + 12, r.y + 50)
    }
    for (const c of g.consumers) drawConsumer(ctx, sim, g, c, col, L.cons.get(c), hits)
  })
}

function drawConsumer (ctx, sim, g, c, col, r, hits) {
  rr(ctx, r.x, r.y, r.w, r.h, 6)
  ctx.fillStyle = '#16233d'
  ctx.fill()
  ctx.strokeStyle = '#2a3a5c'
  ctx.stroke()
  ctx.font = 'bold 11px system-ui, sans-serif'
  ctx.fillStyle = '#e2e8f0'
  ctx.fillText(`📥 ${c.name}`, r.x + 8, r.y + 11)
  ctx.font = '10px system-ui, sans-serif'
  ctx.fillStyle = '#94a3b8'
  const parts = c.assigned.map(p => p.key).join(', ')
  ctx.fillText(fit(ctx, g.state === 'rebalancing' ? '⏳ chờ chia partition…' : (parts || 'rảnh (không có partition)'), r.w - 54), r.x + 46, r.y + 11)
  let status = ''
  if (g.state === 'rebalancing') status = 'tạm dừng do rebalance'
  else if (c.state === 'processing') status = `xử lý ${c.fetchPart.key} offset ${c.cur.offset}${c.batch.length > 1 ? ` (+${c.batch.length - 1} trong lô)` : ''}`
  else if (c.state === 'fetching') status = `đang poll ${c.fetchPart.key}…`
  else status = c.assigned.length ? 'chờ message mới' : '—'
  ctx.fillStyle = '#cbd5e1'
  ctx.fillText(fit(ctx, status, r.w - 60), r.x + 8, r.y + 26)
  ctx.textAlign = 'right'
  ctx.fillStyle = '#64748b'
  ctx.fillText(`✔ ${c.processed}`, r.x + r.w - 6, r.y + 26)
  ctx.textAlign = 'left'
  // progress bar
  const bx = r.x + 8; const by = r.y + 34; const bw = r.w - 16
  ctx.fillStyle = '#0b1220'
  ctx.fillRect(bx, by, bw, 5)
  if (c.state === 'processing' && c.cur) {
    const prog = Math.min(1, Math.max(0, 1 - c.remaining / c.curDur))
    ctx.fillStyle = c.cur.color
    ctx.fillRect(bx, by, bw * prog, 5)
  }
  hits.push({ ...r, action: { type: 'consumer', group: g, consumer: c },
    tip: `<b>Consumer ${c.name}</b> (group ${g.name})<br>Partition được giao: ${parts || 'không có'}<br>Đã xử lý: ${c.processed} message<br>Xử lý xong message nào thì commit offset (offset+1) của message đó.<br><i>Bấm để giả lập consumer này bị crash → group rebalance.</i>` })
}

function drawFlights (ctx, sim, L) {
  for (const f of sim.flights) {
    const k = ease(Math.min(1, (sim.t - f.t0) / f.dur))
    let a, b
    if (f.type === 'produce' || f.type === 'ack') {
      const pr = L.prod.get(f.pr); const pl = L.part.get(f.part)
      if (!pr || !pl) continue
      const p1 = { x: pr.x + pr.w, y: pr.y + pr.h / 2 }
      const pos = Math.min(f.part.leo - windowStart(f.part, pl), pl.visible - 1)
      const p2 = f.type === 'produce' ? { x: pl.logX + pos * CELL + CELL / 2, y: pl.y + 18 } : { x: pl.x, y: pl.y + pl.h / 2 }
      if (f.type === 'produce') { a = p1; b = p2 } else { a = p2; b = p1 }
    } else {
      const pl = L.part.get(f.part); const cl = L.cons.get(f.consumer)
      if (!pl || !cl) continue
      a = { x: pl.x + pl.w, y: pl.y + pl.h / 2 }
      b = { x: cl.x, y: cl.y + cl.h / 2 }
    }
    const x = a.x + (b.x - a.x) * k
    const y = a.y + (b.y - a.y) * k - Math.sin(k * Math.PI) * 18
    if (f.type === 'produce') {
      ctx.fillStyle = f.msg.color
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill()
      ctx.strokeStyle = '#0b1220'; ctx.stroke()
    } else if (f.type === 'ack') {
      ctx.fillStyle = '#4ade80'
      ctx.font = 'bold 11px system-ui'
      ctx.fillText('✓', x - 3, y)
    } else {
      const gi = sim.groups.indexOf(f.group)
      ctx.fillStyle = f.entries[0].color
      rr(ctx, x - 7, y - 7, 14, 14, 3); ctx.fill()
      ctx.strokeStyle = GROUP_COLORS[gi]; ctx.lineWidth = 2; ctx.stroke(); ctx.lineWidth = 1
      if (f.entries.length > 1) {
        ctx.fillStyle = '#fff'; ctx.font = 'bold 9px system-ui'
        ctx.fillText(String(f.entries.length), x - 3, y)
      }
    }
  }
}
