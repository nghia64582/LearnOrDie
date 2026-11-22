// Mô hình mô phỏng Kafka (không phụ thuộc giao diện).
// Đơn vị thời gian: mili-giây thời gian mô phỏng.
import { GROUP_NAMES, KEY_COLORS, PRODUCER_COLORS } from './config.js'

const REPL_RATE = 80 // message/giây tối đa một follower sao chép được (để thấy quá trình đồng bộ lại)
const ISR_SLACK = 2000 // follower trễ quá (replicaDelay + ISR_SLACK) ms thì bị loại khỏi ISR

function hashKey (s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}
const jitter = () => 0.8 + Math.random() * 0.4

export class Sim {
  constructor (params, onEvent = () => {}) {
    this.p = params // tham chiếu chung với UI → thay đổi live
    this.onEvent = onEvent
    this.build()
  }

  // ---------- Khởi tạo ----------
  build () {
    const p = this.p
    this.t = 0
    this.msgSeq = 0
    this.brokers = Array.from({ length: p.brokers }, (_, i) => ({ id: i, alive: true }))
    this.rf = Math.min(p.replicationFactor, p.brokers)
    this.topics = []
    this.parts = []
    let k = 0
    for (let t = 0; t < p.topics; t++) {
      const topic = { id: t, name: `topic-${t}`, parts: [] }
      for (let i = 0; i < p.partitions; i++) {
        const replicas = []
        for (let r = 0; r < this.rf; r++) replicas.push({ broker: (k + r) % p.brokers, leo: 0, inSync: true, budget: 0 })
        const part = {
          key: `T${t}-P${i}`, topic: t, idx: i, log: [], logStart: 0, leo: 0, hw: 0,
          leader: replicas[0].broker, epoch: 0, replicas, appended: 0, lost: 0, flashUntil: 0
        }
        topic.parts.push(part)
        this.parts.push(part)
        k++
      }
      this.topics.push(topic)
    }
    this.producers = []
    this.syncProducers()
    this.flights = []
    this.groups = []
    for (let g = 0; g < p.groups; g++) {
      const group = {
        id: g, name: GROUP_NAMES[g] || `group-${g}`, consumers: [], committed: {}, position: {},
        state: 'stable', rebalanceUntil: 0, gen: 0, nextCid: 0, consumed: 0, skipped: 0, prev: new Map()
      }
      for (const part of this.parts) { group.committed[part.key] = 0; group.position[part.key] = 0 }
      this.groups.push(group)
      this.setConsumerCount(group, p.consumersPerGroup, false)
    }
    this.stats = { produced: 0, appended: 0, acked: 0, failed: 0, lost: 0, retried: 0, deleted: 0 }
    this.history = []
    this.nextSample = 1000
    this.lastSnap = this.snapshot()
  }

  syncProducers () {
    const n = this.p.producers
    while (this.producers.length < n) {
      const id = this.producers.length
      this.producers.push({
        id, name: `Producer ${id + 1}`, color: PRODUCER_COLORS[id % PRODUCER_COLORS.length],
        topic: id % this.topics.length, acc: Math.random(), sent: 0, acked: 0, rr: id, sticky: null, stickyLeft: 0, pending: []
      })
    }
    while (this.producers.length > n) {
      const pr = this.producers.pop()
      this.flights = this.flights.filter(f => f.pr !== pr)
    }
  }

  log (text, kind = 'info') { this.onEvent({ t: this.t, text, kind }) }

  // ---------- Vòng lặp chính ----------
  step (dt) {
    this.t += dt
    this.stepProducers(dt)
    this.stepFlights()
    this.stepReplication(dt)
    this.stepAcks()
    this.stepConsumers(dt)
    for (const part of this.parts) this.applyRetention(part)
    if (this.t >= this.nextSample) { this.sample(); this.nextSample += 1000 }
  }

  // ---------- Producer ----------
  stepProducers (dt) {
    for (const pr of this.producers) {
      pr.acc += this.p.rate * dt / 1000
      while (pr.acc >= 1) { pr.acc -= 1; this.send(pr) }
    }
  }

  choosePartition (pr, key) {
    const parts = this.topics[pr.topic].parts
    if (key !== null) return parts[hashKey(key) % parts.length]
    const avail = parts.filter(pt => pt.leader >= 0)
    const list = avail.length ? avail : parts
    if (this.p.partitioner === 'sticky') {
      if (!pr.sticky || pr.stickyLeft <= 0 || !list.includes(pr.sticky)) {
        const others = list.length > 1 ? list.filter(x => x !== pr.sticky) : list
        pr.sticky = others[Math.floor(Math.random() * others.length)]
        pr.stickyLeft = this.p.stickyBatch
      }
      pr.stickyLeft--
      return pr.sticky
    }
    pr.rr = (pr.rr + 1) % list.length
    return list[pr.rr]
  }

  send (pr, retryMsg = null) {
    let msg = retryMsg
    if (!msg) {
      const key = this.p.partitioner === 'hash' ? `key-${Math.floor(Math.random() * this.p.keys)}` : null
      const color = key !== null ? KEY_COLORS[Number(key.slice(4)) % KEY_COLORS.length] : pr.color
      msg = { id: ++this.msgSeq, key, color, producer: pr.id, sentAt: this.t }
      this.stats.produced++
      pr.sent++
    }
    const part = msg.key !== null ? this.choosePartition(pr, msg.key) : (retryMsg && retryMsg.part ? retryMsg.part : this.choosePartition(pr, null))
    this.flights.push({ type: 'produce', pr, part, msg, t0: this.t, dur: this.p.latency * jitter() })
  }

  // ---------- Các "chuyến bay" (message di chuyển trên canvas) ----------
  stepFlights () {
    const done = []
    for (const f of this.flights) if (this.t - f.t0 >= f.dur) done.push(f)
    if (!done.length) return
    this.flights = this.flights.filter(f => this.t - f.t0 < f.dur)
    for (const f of done) {
      if (f.type === 'produce') this.onProduceArrive(f)
      else if (f.type === 'ack') { f.pr.acked++; this.stats.acked++ }
      else if (f.type === 'fetch') this.onFetchArrive(f)
    }
  }

  onProduceArrive (f) {
    const { part, pr, msg } = f
    if (!this.producers.includes(pr)) return
    const acks = this.p.acks
    if (part.leader < 0 || !this.brokers[part.leader].alive) {
      this.stats.failed++
      part.flashUntil = this.t + 400
      if (acks !== '0') { this.stats.retried++; this.send(pr, { ...msg, part: null }) } else { this.stats.lost++ }
      return
    }
    const entry = { ...msg, offset: part.leo, t: this.t, acked: false }
    delete entry.part
    part.log.push(entry)
    part.leo++
    part.appended++
    this.stats.appended++
    for (const r of part.replicas) if (r.broker === part.leader) r.leo = part.leo
    if (acks === '1') this.ack(part, pr, entry)
    else if (acks === 'all') pr.pending.push({ part, offset: entry.offset, entry })
    this.updateHW(part)
  }

  ack (part, pr, entry) {
    entry.acked = true
    this.flights.push({ type: 'ack', pr, part, t0: this.t, dur: this.p.latency * 0.6 })
  }

  stepAcks () {
    if (this.p.acks !== 'all') {
      // đổi acks khi đang chạy: xác nhận luôn các message đang chờ
      for (const pr of this.producers) {
        for (const pd of pr.pending) if (pd.part.leo > pd.offset) this.ack(pd.part, pr, pd.entry)
        pr.pending = []
      }
      return
    }
    for (const pr of this.producers) {
      if (!pr.pending.length) continue
      const keep = []
      for (const pd of pr.pending) {
        if (pd.part.hw > pd.offset) this.ack(pd.part, pr, pd.entry)
        else keep.push(pd)
      }
      pr.pending = keep
    }
  }

  // ---------- Replication / ISR / High Watermark ----------
  stepReplication (dt) {
    const delay = this.p.replicaDelay
    for (const part of this.parts) {
      if (part.leader < 0) continue
      for (const r of part.replicas) {
        if (r.broker === part.leader) { r.leo = part.leo; r.inSync = true; continue }
        if (!this.brokers[r.broker].alive) {
          if (r.inSync) { r.inSync = false }
          continue
        }
        if (r.leo < part.logStart) r.leo = part.logStart
        r.budget = Math.min(r.budget + REPL_RATE * dt / 1000, 20)
        while (r.leo < part.leo && r.budget >= 1) {
          const e = part.log[r.leo - part.logStart]
          if (!e || this.t - e.t < delay) break
          r.leo++
          r.budget--
        }
        const next = part.log[r.leo - part.logStart]
        const behindMs = next ? this.t - next.t : 0
        if (r.inSync && behindMs > delay + ISR_SLACK) {
          r.inSync = false
          this.log(`${part.key}: replica trên Broker ${r.broker + 1} tụt quá xa → bị loại khỏi ISR`, 'warn')
        } else if (!r.inSync && r.leo >= part.hw && behindMs <= delay + 200) {
          r.inSync = true
          this.log(`${part.key}: replica trên Broker ${r.broker + 1} đã bắt kịp → vào lại ISR`, 'ok')
        }
      }
      this.updateHW(part)
    }
  }

  updateHW (part) {
    if (part.leader < 0) return
    let min = part.leo
    for (const r of part.replicas) if (r.inSync) min = Math.min(min, r.leo)
    part.hw = Math.min(part.leo, Math.max(part.hw, min))
  }

  // ---------- Broker sập / bật lại ----------
  toggleBroker (id) {
    const b = this.brokers[id]
    b.alive = !b.alive
    if (!b.alive) {
      this.log(`💥 Broker ${id + 1} sập`, 'bad')
      for (const part of this.parts) {
        for (const r of part.replicas) if (r.broker === id) r.inSync = false
        if (part.leader === id) this.electLeader(part, false)
      }
    } else {
      this.log(`✅ Broker ${id + 1} chạy lại`, 'ok')
      for (const part of this.parts) {
        const r = part.replicas.find(x => x.broker === id)
        if (!r) continue
        if (part.leader < 0) {
          // partition đang offline: replica vừa sống lại lên làm leader (unclean, có thể mất dữ liệu)
          this.electLeader(part, true)
        } else {
          r.leo = Math.min(r.leo, part.hw) // follower cắt log về HW rồi đồng bộ lại từ leader
          r.inSync = false
        }
      }
    }
  }

  electLeader (part, unclean) {
    const old = part.leader
    let cands = part.replicas.filter(r => r.broker !== old && this.brokers[r.broker].alive && r.inSync)
    if (!cands.length && unclean) cands = part.replicas.filter(r => this.brokers[r.broker].alive)
    if (!cands.length) {
      part.leader = -1
      this.log(`⛔ ${part.key}: không còn replica nào trong ISR → partition OFFLINE`, 'bad')
      return
    }
    cands.sort((a, b) => b.leo - a.leo)
    const nl = cands[0]
    if (nl.leo < part.leo) this.truncate(part, nl.leo)
    part.leader = nl.broker
    part.epoch++
    nl.inSync = true
    for (const r of part.replicas) if (r.leo > part.leo) r.leo = part.leo
    part.hw = Math.min(part.hw, part.leo)
    for (const g of this.groups) {
      g.committed[part.key] = Math.min(g.committed[part.key], part.leo)
      g.position[part.key] = Math.min(g.position[part.key], part.leo)
    }
    this.log(`👑 ${part.key}: Broker ${nl.broker + 1} được bầu làm leader mới (epoch ${part.epoch})${unclean ? ' [unclean]' : ''}`, 'warn')
  }

  truncate (part, newLeo) {
    const removed = part.leo - newLeo
    const start = Math.max(0, newLeo - part.logStart)
    const cut = part.log.splice(start)
    let ackedLost = 0
    for (const e of cut) if (e.acked) ackedLost++
    part.leo = newLeo
    if (part.logStart > newLeo) part.logStart = newLeo
    part.lost += removed
    this.stats.lost += ackedLost
    // message đang chờ acks=all bị cắt → producer gửi lại
    for (const pr of this.producers) {
      const keep = []
      for (const pd of pr.pending) {
        if (pd.part === part && pd.offset >= newLeo) {
          this.stats.retried++
          const { offset, t, acked, ...msg } = pd.entry
          this.send(pr, { ...msg, part: null })
        } else keep.push(pd)
      }
      pr.pending = keep
    }
    this.log(`✂️ ${part.key}: cắt ${removed} message chưa được replicate (${ackedLost} message đã được ack → MẤT)`, ackedLost ? 'bad' : 'warn')
  }

  applyRetention (part) {
    const max = this.p.retention
    if (part.log.length <= max) return
    const n = part.log.length - max
    part.log.splice(0, n)
    part.logStart += n
    this.stats.deleted += n
  }

  // ---------- Consumer group ----------
  setConsumerCount (group, n, animate = true) {
    if (group.consumers.length === n) return
    while (group.consumers.length < n) {
      const id = group.nextCid++
      group.consumers.push({ id, name: `C${id + 1}`, assigned: [], state: 'idle', batch: [], cur: null, remaining: 0, curDur: 1, processed: 0, rr: 0, fetchPart: null })
    }
    while (group.consumers.length > n) group.consumers.pop()
    this.startRebalance(group, `số consumer = ${n}`, animate)
  }

  crashConsumer (group, consumer) {
    group.consumers = group.consumers.filter(c => c !== consumer)
    this.log(`💥 Group ${group.name}: consumer ${consumer.name} bị crash`, 'bad')
    this.startRebalance(group, `${consumer.name} rời group`, true)
  }

  startRebalance (group, reason, animate = true) {
    group.gen++
    group.prev = new Map()
    for (const c of group.consumers) group.prev.set(c.id, c.assigned.map(p => p.key))
    for (const c of group.consumers) { c.assigned = []; c.state = 'idle'; c.batch = []; c.cur = null }
    for (const part of this.parts) group.position[part.key] = group.committed[part.key]
    this.flights = this.flights.filter(f => !(f.type === 'fetch' && f.group === group))
    if (animate && this.p.rebalanceTime > 0) {
      group.state = 'rebalancing'
      group.rebalanceUntil = this.t + this.p.rebalanceTime
      this.log(`🔄 Group ${group.name} bắt đầu rebalance (${reason}) — cả group tạm ngừng đọc`, 'warn')
    } else {
      this.finishRebalance(group, animate)
    }
  }

  finishRebalance (group, announce = true) {
    group.state = 'stable'
    const res = assignPartitions(this.p.assignor, group.consumers, this.topics, group.prev)
    let moved = 0
    for (const c of group.consumers) {
      c.assigned = res.get(c)
      const prev = group.prev.get(c.id) || []
      moved += c.assigned.filter(p => !prev.includes(p.key)).length
    }
    if (announce) {
      const desc = group.consumers.map(c => `${c.name}←[${c.assigned.map(p => p.key).join(', ') || 'rảnh'}]`).join('  ')
      this.log(`✅ Group ${group.name} rebalance xong (${this.p.assignor}, ${moved} partition đổi chủ): ${desc || 'không còn consumer'}`, 'ok')
    }
  }

  stepConsumers (dt) {
    for (const g of this.groups) {
      if (g.state === 'rebalancing') {
        if (this.t >= g.rebalanceUntil) this.finishRebalance(g)
        else continue
      }
      for (const c of g.consumers) {
        if (c.state === 'idle') this.tryFetch(g, c)
        if (c.state === 'processing') {
          c.remaining -= dt
          while (c.state === 'processing' && c.remaining <= 0) {
            const e = c.cur
            g.committed[c.fetchPart.key] = Math.max(g.committed[c.fetchPart.key], e.offset + 1)
            g.consumed++
            c.processed++
            c.batch.shift()
            if (c.batch.length) this.startProcessing(c, c.batch[0], c.remaining)
            else { c.state = 'idle'; c.cur = null }
          }
        }
      }
    }
  }

  startProcessing (c, e, carry = 0) {
    c.cur = e
    c.curDur = this.p.procTime * jitter()
    c.remaining = c.curDur + carry
  }

  tryFetch (g, c) {
    const n = c.assigned.length
    for (let i = 0; i < n; i++) {
      const idx = (c.rr + i) % n
      const part = c.assigned[idx]
      if (part.leader < 0) continue
      let pos = g.position[part.key]
      if (pos < part.logStart) {
        const skip = part.logStart - pos
        g.skipped += skip
        this.log(`🗑️ Group ${g.name}: ${part.key} offset ${pos}..${part.logStart - 1} đã bị retention xoá → bỏ qua ${skip} message`, 'bad')
        pos = part.logStart
        g.position[part.key] = pos
        if (g.committed[part.key] < pos) g.committed[part.key] = pos
      }
      if (pos < part.hw) {
        const cnt = Math.min(this.p.maxPoll, part.hw - pos)
        const entries = part.log.slice(pos - part.logStart, pos - part.logStart + cnt)
        if (!entries.length) continue
        g.position[part.key] = pos + entries.length
        c.state = 'fetching'
        c.fetchPart = part
        c.rr = idx + 1
        this.flights.push({ type: 'fetch', group: g, consumer: c, part, entries, gen: g.gen, t0: this.t, dur: this.p.latency * 0.5 })
        return
      }
    }
  }

  onFetchArrive (f) {
    const { group: g, consumer: c } = f
    if (f.gen !== g.gen || !g.consumers.includes(c)) return
    c.state = 'processing'
    c.batch = f.entries.slice()
    this.startProcessing(c, c.batch[0])
  }

  // ---------- Số liệu ----------
  lag (g, part) { return Math.max(0, part.hw - g.committed[part.key]) }
  groupLag (g) { return this.parts.reduce((s, p) => s + this.lag(g, p), 0) }

  snapshot () {
    return { appended: this.stats.appended, consumed: this.groups.map(g => g.consumed) }
  }

  sample () {
    const s = this.snapshot()
    this.history.push({
      t: this.t,
      in: s.appended - this.lastSnap.appended,
      out: s.consumed.map((v, i) => v - (this.lastSnap.consumed[i] || 0)),
      lag: this.groups.map(g => this.groupLag(g))
    })
    if (this.history.length > 60) this.history.shift()
    this.lastSnap = s
  }
}

// ---------- Thuật toán chia partition cho consumer ----------
export function assignPartitions (strategy, consumers, topics, prev = new Map()) {
  const res = new Map(consumers.map(c => [c, []]))
  const m = consumers.length
  if (!m) return res
  const all = topics.flatMap(t => t.parts)
  if (strategy === 'range') {
    for (const t of topics) {
      const n = t.parts.length
      const per = Math.floor(n / m)
      const extra = n % m
      let idx = 0
      consumers.forEach((c, i) => {
        const cnt = per + (i < extra ? 1 : 0)
        res.get(c).push(...t.parts.slice(idx, idx + cnt))
        idx += cnt
      })
    }
  } else if (strategy === 'roundrobin') {
    all.forEach((p, i) => res.get(consumers[i % m]).push(p))
  } else {
    // sticky: giữ partition cũ trong giới hạn quota, phần còn lại chia cho consumer ít việc nhất
    const n = all.length
    const base = Math.floor(n / m)
    let extras = n % m
    const taken = new Set()
    for (const c of consumers) {
      const keep = (prev.get(c.id) || []).map(k => all.find(p => p.key === k)).filter(p => p && !taken.has(p))
      const cap = base + (extras > 0 ? 1 : 0)
      const kept = keep.slice(0, cap)
      if (kept.length > base) extras--
      kept.forEach(p => taken.add(p))
      res.get(c).push(...kept)
    }
    for (const p of all) {
      if (taken.has(p)) continue
      let best = consumers[0]
      for (const c of consumers) if (res.get(c).length < res.get(best).length) best = c
      res.get(best).push(p)
      taken.add(p)
    }
    for (const c of consumers) res.get(c).sort((a, b) => all.indexOf(a) - all.indexOf(b))
  }
  return res
}
