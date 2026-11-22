# kafka-sim – Mô phỏng trực quan Apache Kafka

Web app nhỏ (Vite + JavaScript thuần + HTML Canvas) giúp **nhìn thấy** Kafka hoạt động thế nào:

- **Producer** gửi message (chấm tròn bay) tới **leader** của partition.
- **Broker / Topic / Partition**: mỗi partition là một log chỉ ghi nối, mỗi ô là 1 message tại 1 **offset**.
- **Replication**: leader ★, follower, **ISR**, **High Watermark (HW)**. Bấm vào broker để làm nó sập, xem bầu leader mới.
- **Consumer group**: chia partition cho consumer, poll, xử lý, **commit offset**, **lag**, **rebalance**.
- Bảng số liệu: throughput vào/ra, lag từng partition/group, tổng message, message mất, retention đã xoá, biểu đồ 60 giây.

Không cần cài Kafka thật: mọi thứ được mô phỏng ngay trong trình duyệt.

## 1. Yêu cầu

- **Node.js >= 18** (khuyên dùng LTS 20 hoặc 22). Kiểm tra: `node -v`
- Trình duyệt Chrome / Edge / Firefox.

## 2. Chạy

```bash
cd LearnOrDie
git pull
cd Projects/kafka-sim
npm install      # chỉ cần lần đầu
npm start
```

Trang mở ở **http://localhost:5174/** (cổng 5174 để không trùng với `jscad-local` dùng 5173).
Không muốn tự bật trình duyệt thì dùng `npm run dev`. Dừng server: `Ctrl + C`.

Build bản tĩnh (có thể đưa lên Cloudflare Pages / GitHub Pages): `npm run build` → thư mục `dist/`.

## 3. Cách dùng

| Nút | Tác dụng |
|---|---|
| ▶ **Chạy** | Bắt đầu / tiếp tục mô phỏng |
| ⏸ **Tạm dừng** | Đứng hình, vẫn rê chuột xem chi tiết được |
| ⏹ **Dừng** | Reset về trạng thái ban đầu và áp dụng các thông số cấu trúc cụm |
| **Tốc độ** | 0.25x → 5x thời gian mô phỏng |
| **Kịch bản** | Chọn nhanh một tình huống mẫu (consumer chậm, broker sập, key-hash, retention…) kèm gợi ý cần quan sát gì |

Tương tác trên canvas:

- **Rê chuột** lên producer, broker, partition, replica, consumer → tooltip giải thích bằng tiếng Việt.
- **Bấm vào broker** → broker sập / chạy lại. Partition mà nó làm leader sẽ bầu leader mới từ ISR. Không còn replica nào → partition OFFLINE.
- **Bấm vào consumer** → giả lập consumer crash, group rebalance.

### Đọc hình

- Ô màu trong partition = 1 message. Màu = producer (chế độ không key) hoặc màu của key (chế độ key-hash).
- Ô **mờ** = leader đã ghi nhưng chưa đủ ISR sao chép (nằm trên HW, consumer chưa đọc được).
- Vạch **đỏ nét đứt** = HW. Tam giác nhỏ phía trên = LEO của follower (đã sao chép tới đâu).
- Tam giác **màu group** phía dưới = offset đã commit của group đó. Khoảng cách tới HW = **lag**.
- Chip replica: `★B1` leader · xanh lá = follower trong ISR · cam = ngoài ISR · xám = broker đã sập.
- Ô vuông viền màu group bay sang phải = một lô message vừa được poll (số bên trong = số message).
- Dấu ✓ xanh bay về producer = ack.

## 4. Các thông số

Thông số có biểu tượng 🔁 là **cấu trúc cụm**. Nếu đang chạy, chúng chỉ áp dụng khi bấm ⏹ Dừng. Các thông số còn lại áp dụng ngay.

| Thông số | Ý nghĩa |
|---|---|
| 🔁 Số broker (1–5) | Số server Kafka trong cụm |
| 🔁 Replication factor (1–5) | Số bản sao mỗi partition (tối đa = số broker) |
| 🔁 Số topic (1–3) | Producer *i* ghi vào topic *i mod số topic*; mọi group đọc tất cả topic |
| 🔁 Partition mỗi topic (1–8) | Mức song song tối đa của một consumer group |
| 🔁 Số consumer group (1–3) | Các group đọc độc lập, mỗi group có offset riêng |
| Retention (10–300) | Số message tối đa giữ lại mỗi partition, cũ hơn sẽ bị xoá (kể cả chưa ai đọc) |
| Độ trễ replicate (ms) | Thời gian follower sao chép 1 message. Trễ quá ~2s so với mức này thì bị loại khỏi ISR |
| Số producer (1–6) | Thay đổi ngay khi đang chạy |
| Message/giây mỗi producer | 0.5–30 |
| Chiến lược chọn partition | **Round-robin** (không key) · **Sticky** (không key, gửi theo lô vào 1 partition rồi đổi) · **Key-hash** (`hash(key) mod số partition`, cùng key → cùng partition, giữ thứ tự theo key) |
| Số key khác nhau | Dùng cho key-hash |
| Kích thước lô (sticky) | Số message gửi vào 1 partition trước khi đổi |
| acks | **0**: không chờ, partition offline thì mất luôn · **1**: leader ghi xong là ack (có thể mất khi đổi leader) · **all**: chờ mọi ISR (tới HW) mới ack; bị cắt thì producer gửi lại |
| Consumer mỗi group (0–8) | Đổi khi đang chạy → **rebalance** |
| Thời gian xử lý 1 message (ms) | ±20% ngẫu nhiên. Chậm hơn tốc độ ghi thì lag tăng |
| Số message mỗi lần poll | Giống `max.poll.records`. Xử lý xong message nào thì commit message đó |
| Chiến lược chia partition | **Range** (chia khúc liên tiếp theo từng topic) · **Round-robin** · **Sticky** (giữ partition cũ nhiều nhất có thể). Áp dụng từ lần rebalance sau |
| Thời gian rebalance (ms) | Thời gian cả group ngừng đọc khi rebalance (kiểu eager). 0 = tức thì |
| Độ trễ mạng (ms) | Thời gian message bay producer → broker. Broker → consumer bằng một nửa |

## 5. Gợi ý thí nghiệm

1. **Lag**: kịch bản "Consumer chậm". Lag tăng đều, rồi kéo *Consumer mỗi group* lên 3 → rebalance → lag giảm.
2. **Consumer thừa**: 2 partition, 4 consumer → 2 consumer ngồi rảnh.
3. **Thứ tự theo key**: key-hash, 3 key, 4 partition → mỗi màu chỉ nằm ở 1 partition.
4. **Mất dữ liệu với acks=1**: kịch bản "Broker sập", bấm vào broker đang làm leader → log bị cắt, ô "Message MẤT" tăng. Đổi sang acks=all, ⏹ Dừng, chạy lại và thử lần nữa → không mất, producer gửi lại.
5. **Retention**: retention 20 + consumer chậm → consumer bị nhảy offset ("bỏ qua do retention").

## 6. Đơn giản hoá so với Kafka thật

Đây là mô hình để học, không phải Kafka thật:

- Retention tính theo **số message** thay vì thời gian/dung lượng. Không có segment, compaction.
- Không mô phỏng `min.insync.replicas`, transaction, idempotent producer, KRaft/ZooKeeper/controller.
- Producer không gom batch theo `linger.ms`. Mỗi message bay riêng, trừ chế độ sticky mô phỏng việc dính partition theo lô.
- Rebalance kiểu **eager** (cả group dừng). Chiến lược sticky chỉ ảnh hưởng cách chia, không phải cooperative rebalance.
- Commit offset ngay sau khi xử lý từng message (giống commit đồng bộ thủ công).
- Thêm/bớt partition, topic, broker, group cần bấm ⏹ Dừng (reset).

## 7. Cấu trúc thư mục

```
kafka-sim/
├── index.html        # khung giao diện, chú giải
├── src/
│   ├── config.js     # định nghĩa thông số, kịch bản mẫu, màu
│   ├── sim.js        # mô hình Kafka: producer, partition, replication/ISR/HW, consumer group, rebalance
│   ├── render.js     # vẽ canvas + vùng hover/click
│   ├── main.js       # điều khiển, form thông số, bảng số liệu, biểu đồ, nhật ký
│   └── style.css
├── package.json
└── vite.config.js
```

Muốn sửa logic mô phỏng thì xem `src/sim.js`. Muốn đổi giao diện thì xem `src/render.js`. Trong DevTools có thể gõ `__kafkaSim()` để xem trạng thái hiện tại.
