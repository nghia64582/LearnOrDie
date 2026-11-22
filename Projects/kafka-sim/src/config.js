// Định nghĩa toàn bộ tham số mô phỏng.
// structural: true  -> thay đổi cấu trúc cụm, chỉ áp dụng khi bấm "Dừng" (reset)
// structural: false -> áp dụng ngay khi đang chạy

export const PARAM_GROUPS = [
  {
    title: '🖥️ Cụm Kafka',
    note: 'Các thông số này áp dụng khi bấm ⏹ Dừng (reset).',
    params: [
      { key: 'brokers', label: 'Số broker', type: 'range', min: 1, max: 5, step: 1, def: 3, structural: true,
        help: 'Broker là một máy chủ Kafka. Nhiều broker tạo thành một cụm (cluster). Mỗi partition có một broker làm leader, các broker khác giữ bản sao (follower). Bấm vào ô broker trên canvas để làm nó sập / bật lại.' },
      { key: 'replicationFactor', label: 'Replication factor', type: 'range', min: 1, max: 5, step: 1, def: 2, structural: true,
        help: 'Số bản sao của mỗi partition (gồm cả leader). Không thể lớn hơn số broker. RF = 3 nghĩa là chịu được 2 broker sập mà không mất dữ liệu đã commit.' },
      { key: 'topics', label: 'Số topic', type: 'range', min: 1, max: 3, step: 1, def: 1, structural: true,
        help: 'Topic là một "kênh" chứa message cùng loại (ví dụ orders, payments). Producer ghi vào topic, consumer đọc từ topic.' },
      { key: 'partitions', label: 'Partition mỗi topic', type: 'range', min: 1, max: 8, step: 1, def: 3, structural: true,
        help: 'Mỗi topic được chia thành nhiều partition. Partition là một log chỉ ghi nối (append-only), mỗi message có một số thứ tự gọi là offset. Thứ tự chỉ được đảm bảo trong cùng một partition. Số partition giới hạn số consumer làm việc song song trong một group.' },
      { key: 'groups', label: 'Số consumer group', type: 'range', min: 1, max: 3, step: 1, def: 1, structural: true,
        help: 'Mỗi consumer group đọc TOÀN BỘ message của topic một cách độc lập, và có offset riêng. Ví dụ group "billing" và group "analytics" cùng đọc topic orders mà không ảnh hưởng nhau.' },
      { key: 'retention', label: 'Retention (số message giữ lại / partition)', type: 'range', min: 10, max: 300, step: 5, def: 80, structural: false,
        help: 'Kafka không xoá message sau khi đọc, mà xoá theo thời gian hoặc dung lượng (retention). Ở đây giới hạn theo số message: vượt quá thì message cũ nhất bị xoá. Consumer chậm có thể bị mất message chưa kịp đọc.' },
      { key: 'replicaDelay', label: 'Độ trễ replicate (ms)', type: 'range', min: 0, max: 3000, step: 50, def: 300, structural: false,
        help: 'Thời gian follower cần để sao chép một message từ leader. High Watermark (HW) chỉ tăng khi mọi replica trong ISR đã có message, và consumer chỉ đọc được tới HW.' }
    ]
  },
  {
    title: '📤 Producer',
    params: [
      { key: 'producers', label: 'Số producer', type: 'range', min: 1, max: 6, step: 1, def: 2, structural: false,
        help: 'Producer là ứng dụng gửi message vào Kafka. Producer i ghi vào topic (i mod số topic).' },
      { key: 'rate', label: 'Message/giây mỗi producer', type: 'range', min: 0.5, max: 30, step: 0.5, def: 2, structural: false,
        help: 'Tốc độ gửi message của mỗi producer.' },
      { key: 'partitioner', label: 'Chiến lược chọn partition', type: 'select', def: 'roundrobin', structural: false,
        options: [
          ['roundrobin', 'Round-robin (không key)'],
          ['sticky', 'Sticky (không key, theo lô)'],
          ['hash', 'Key-hash (có key)']
        ],
        help: 'Round-robin: lần lượt từng partition. Sticky: dính vào một partition cho cả một lô rồi mới đổi (mặc định của Kafka mới cho message không key, giúp batch to hơn). Key-hash: partition = hash(key) mod số partition, nên cùng key luôn vào cùng partition → giữ được thứ tự theo key. Ở chế độ không key, màu message là màu producer; ở chế độ key-hash, màu là màu của key.' },
      { key: 'keys', label: 'Số key khác nhau (key-hash)', type: 'range', min: 1, max: 12, step: 1, def: 4, structural: false,
        help: 'Chỉ dùng cho key-hash. Ví dụ key là userId: mọi sự kiện của cùng một user vào cùng partition. Ít key hơn số partition thì sẽ có partition bị bỏ trống (lệch tải).' },
      { key: 'stickyBatch', label: 'Kích thước lô (sticky)', type: 'range', min: 2, max: 30, step: 1, def: 8, structural: false,
        help: 'Chỉ dùng cho sticky: số message gửi vào cùng một partition trước khi chuyển sang partition khác.' },
      { key: 'acks', label: 'acks', type: 'select', def: '1', structural: false,
        options: [
          ['0', 'acks=0 (gửi rồi quên)'],
          ['1', 'acks=1 (leader ghi xong)'],
          ['all', 'acks=all (mọi ISR ghi xong)']
        ],
        help: 'acks=0: không chờ xác nhận, nhanh nhất nhưng có thể mất message. acks=1: leader ghi xong là xác nhận; nếu leader sập trước khi follower kịp sao chép thì message đã "thành công" vẫn bị mất. acks=all: chờ mọi replica trong ISR có message (tới HW) mới xác nhận → an toàn nhất, độ trễ cao hơn.' }
    ]
  },
  {
    title: '📥 Consumer',
    params: [
      { key: 'consumersPerGroup', label: 'Consumer mỗi group', type: 'range', min: 0, max: 8, step: 1, def: 2, structural: false,
        help: 'Đổi số consumer khi đang chạy sẽ gây rebalance: group tạm dừng, chia lại partition cho các consumer. Mỗi partition chỉ thuộc về đúng 1 consumer trong group; consumer thừa sẽ ngồi rảnh. Bấm vào một consumer trên canvas để giả lập nó bị crash.' },
      { key: 'procTime', label: 'Thời gian xử lý 1 message (ms)', type: 'range', min: 20, max: 3000, step: 10, def: 400, structural: false,
        help: 'Thời gian consumer xử lý một message (có dao động ±20%). Xử lý chậm hơn tốc độ ghi thì lag sẽ tăng dần.' },
      { key: 'maxPoll', label: 'Số message mỗi lần poll (max.poll.records)', type: 'range', min: 1, max: 10, step: 1, def: 3, structural: false,
        help: 'Mỗi lần poll consumer lấy tối đa bấy nhiêu message rồi xử lý lần lượt, xử lý xong message nào thì commit offset message đó.' },
      { key: 'assignor', label: 'Chiến lược chia partition', type: 'select', def: 'range', structural: false,
        options: [
          ['range', 'Range'],
          ['roundrobin', 'Round-robin'],
          ['sticky', 'Sticky']
        ],
        help: 'Cách group chia partition cho consumer khi rebalance. Range: chia từng topic thành các khúc liên tiếp. Round-robin: chia lần lượt mọi partition. Sticky: cân bằng nhưng giữ nguyên càng nhiều partition cũ càng tốt (ít bị di chuyển). Áp dụng từ lần rebalance tiếp theo.' },
      { key: 'rebalanceTime', label: 'Thời gian rebalance (ms)', type: 'range', min: 0, max: 5000, step: 100, def: 1500, structural: false,
        help: 'Trong lúc rebalance (kiểu eager), cả group ngừng đọc. Message đang xử lý dở chưa commit sẽ được đọc lại từ offset đã commit.' }
    ]
  },
  {
    title: '🌐 Mạng',
    params: [
      { key: 'latency', label: 'Độ trễ mạng (ms)', type: 'range', min: 100, max: 2000, step: 50, def: 600, structural: false,
        help: 'Thời gian message bay từ producer tới broker (và từ broker tới consumer bằng một nửa). Chủ yếu để nhìn rõ animation.' }
    ]
  }
]

export const ALL_PARAMS = PARAM_GROUPS.flatMap(g => g.params)

export function defaultParams () {
  const p = {}
  for (const d of ALL_PARAMS) p[d.key] = d.def
  return p
}

export const PRESETS = [
  { id: 'basic', name: 'Cơ bản (mặc định)', set: {},
    hint: 'Producer gửi message, mỗi partition là một log có offset, consumer đọc và commit offset. Rê chuột lên các thành phần để xem giải thích.' },
  { id: 'slow', name: 'Consumer chậm → lag tăng', set: { procTime: 1500, maxPoll: 1, rate: 3, consumersPerGroup: 1 },
    hint: 'Consumer xử lý chậm hơn tốc độ ghi nên lag tăng liên tục. Thử kéo "Consumer mỗi group" lên 3 để thấy rebalance và lag giảm dần.' },
  { id: 'idle', name: 'Nhiều consumer hơn partition', set: { partitions: 2, consumersPerGroup: 4 },
    hint: 'Chỉ có 2 partition nên chỉ 2 consumer có việc, 2 consumer còn lại ngồi rảnh. Số partition là giới hạn mức song song của một group.' },
  { id: 'key', name: 'Key-hash giữ thứ tự theo key', set: { partitioner: 'hash', keys: 3, partitions: 4 },
    hint: 'Màu = key. Cùng key luôn vào cùng một partition (giữ thứ tự theo key). 3 key cho 4 partition nên có partition bị bỏ trống.' },
  { id: 'failover', name: 'Broker sập, acks=1 có thể mất message', set: { acks: '1', replicaDelay: 2000, replicationFactor: 2, rate: 6 },
    hint: 'Bấm vào một broker đang làm leader để làm nó sập. Follower trong ISR lên làm leader; các message leader đã nhận nhưng follower chưa kịp sao chép bị cắt bỏ → với acks=1 chúng đã được báo thành công mà vẫn mất. Đổi sang acks=all rồi thử lại: producer sẽ gửi lại, không mất.' },
  { id: 'groups', name: '2 consumer group độc lập', set: { groups: 2, consumersPerGroup: 2 },
    hint: 'Mỗi group đọc toàn bộ message và có offset (tam giác màu) riêng. Một group chậm không làm group kia chậm.' },
  { id: 'retention', name: 'Retention xoá message chưa đọc', set: { retention: 20, procTime: 1200, maxPoll: 1, rate: 4, consumersPerGroup: 1 },
    hint: 'Retention nhỏ + consumer chậm: message cũ bị xoá trước khi được đọc, consumer bị nhảy offset và mất message (xem "Bỏ qua do retention").' }
]

export const GROUP_COLORS = ['#f59e0b', '#a855f7', '#14b8a6']
export const GROUP_NAMES = ['billing', 'analytics', 'audit']
export const PRODUCER_COLORS = ['#38bdf8', '#f472b6', '#a3e635', '#fb923c', '#c084fc', '#facc15']
export const KEY_COLORS = ['#ef4444', '#3b82f6', '#22c55e', '#eab308', '#ec4899', '#06b6d4', '#f97316', '#8b5cf6', '#84cc16', '#f43f5e', '#0ea5e9', '#d946ef']
export const BROKER_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#c084fc']
