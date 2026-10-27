# jscad-local – Chạy OpenJSCAD (JSCAD) trên máy local

Project nhỏ giúp bạn làm giống như trang https://openjscad.xyz/v2/ nhưng chạy **hoàn toàn trên máy mình**:

- Viết model 3D bằng JavaScript trong thư mục `models/` (dùng thư viện chính chủ `@jscad/modeling`).
- Xem trực tiếp trên trình duyệt (dùng `@jscad/regl-renderer`, cùng bộ render với OpenJSCAD), có xoay / zoom / di chuyển camera.
- Lưu file là trang tự tải lại (Vite).
- Hỗ trợ `getParameterDefinitions()` → tự sinh ô nhập tham số ở thanh bên trái, giống OpenJSCAD.
- Xuất **STL** bằng nút trên web hoặc bằng lệnh `npm run export` (không cần trình duyệt).

## 1. Yêu cầu

- **Node.js >= 18** (khuyên dùng bản LTS 20 hoặc 22). Kiểm tra: `node -v`
  - Chưa có thì tải ở https://nodejs.org (chọn bản LTS), cài xong mở lại terminal.
- npm (đi kèm Node.js).
- Trình duyệt hỗ trợ WebGL (Chrome, Edge, Firefox đều được).

## 2. Lấy code về

```bash
cd LearnOrDie
git pull
cd Projects/jscad-local
```

## 3. Cài thư viện (chỉ cần làm lần đầu, hoặc khi `package.json` thay đổi)

```bash
npm install
```

## 4. Chạy

```bash
npm start
```

Lệnh này mở server ở **http://localhost:5173/** và tự bật trình duyệt.
(Nếu không muốn tự mở trình duyệt thì dùng `npm run dev`, rồi tự mở link trên.)

Dừng server: bấm `Ctrl + C` trong terminal.

Điều khiển camera:

| Thao tác | Tác dụng |
|---|---|
| Kéo chuột trái | Xoay |
| Kéo chuột phải, hoặc Shift + kéo | Di chuyển (pan) |
| Lăn chuột | Zoom |
| Nút "Zoom vừa khung" | Đưa model vào giữa màn hình |

Chọn model khác ở ô **Model** (danh sách lấy tự động từ thư mục `models/`). Có thể mở thẳng một model bằng link, ví dụ http://localhost:5173/#gear

## 5. Sửa / tạo model

- Mở `models/main.js` bằng VS Code, sửa và **lưu** → trình duyệt tự cập nhật.
- Tạo model mới: thêm một file `.js` bất kỳ vào `models/` (ví dụ `models/coc.js`), tải lại trang là thấy trong danh sách.

Khung tối thiểu của một file model:

```js
import jscad from '@jscad/modeling'

const { cuboid, sphere } = jscad.primitives
const { union } = jscad.booleans

// (Không bắt buộc) tham số hiển thị ở thanh bên trái
export const getParameterDefinitions = () => [
  { name: 'r', type: 'number', initial: 10, caption: 'Bán kính' }
]

export const main = ({ r = 10 } = {}) => {
  return union(cuboid({ size: [20, 20, 20] }), sphere({ radius: r }))
}
```

Các kiểu tham số hỗ trợ: `number`, `int`, `slider`, `checkbox`, `choice` (`values`, `captions`), `text`, `color`, `group`.

### Copy code từ openjscad.xyz sang

Code trên web thường viết theo kiểu CommonJS:

```js
const jscad = require('@jscad/modeling')
...
module.exports = { main, getParameterDefinitions }
```

Khi dán vào đây chỉ cần đổi 2 chỗ:

1. `const jscad = require('@jscad/modeling')` → `import jscad from '@jscad/modeling'`
2. `module.exports = { main, getParameterDefinitions }` → thêm `export` trước `const main = ...` và `const getParameterDefinitions = ...` (rồi xoá dòng `module.exports`).

Phần còn lại (primitives, booleans, transforms, extrusions, colors...) giữ nguyên.
Tài liệu API: https://openjscad.xyz/docs/

## 6. Xuất file STL

**Cách 1 – trên web:** bấm nút **"Tải STL"** → tải về model đang hiển thị với tham số hiện tại.

**Cách 2 – dòng lệnh** (kết quả nằm trong thư mục `out/`):

```bash
npm run export                                   # models/main.js -> out/main.stl
npm run export -- models/gear.js                 # -> out/gear.stl
npm run export -- models/gear.js out/g24.stl teeth=24 radius=30   # đổi tham số
npm run export -- --all                          # xuất tất cả model trong models/
```

> Lưu ý: STL không lưu màu, nên `colorize(...)` chỉ có tác dụng khi xem trên web.

## 7. Cấu trúc thư mục

```
jscad-local/
├── index.html          # giao diện web
├── src/
│   ├── main.js         # viewer: load model, render, điều khiển camera, nút tải STL
│   ├── params.js       # dựng form tham số từ getParameterDefinitions()
│   └── style.css
├── models/             # <-- các model 3D của bạn ở đây
│   ├── main.js         # ví dụ: hộp khoét lỗ + quả cầu
│   └── gear.js         # ví dụ: bánh răng (extrude 2D -> 3D)
├── scripts/export.mjs  # xuất STL bằng Node
├── vite.config.js
└── package.json
```

## 8. Gặp lỗi?

- **`'vite' is not recognized` / `vite: not found`** → chưa chạy `npm install` trong đúng thư mục `Projects/jscad-local`.
- **Cổng 5173 đang bận** → Vite sẽ tự chọn cổng khác (xem link in ra trong terminal), hoặc chạy `npm run dev -- --port 3000`.
- **Màn hình đen / không thấy gì** → xem dòng trạng thái ở thanh trái và tab Console của trình duyệt (F12); lỗi trong `main()` sẽ hiện ở đó. Bấm "Zoom vừa khung" nếu model nằm ngoài khung nhìn.
- **Lỗi `Cannot destructure property ... of 'jscad.primitives'`** → dùng `import jscad from '@jscad/modeling'` (import mặc định), **không** dùng `import * as jscad ...`.

## Muốn chạy nguyên bản giao diện openjscad.xyz?

Project này là bản gọn nhẹ. Nếu muốn đúng giao diện web đầy đủ (editor tích hợp, kéo-thả file...), có thể clone repo chính thức
https://github.com/jscad/OpenJSCAD.org và làm theo hướng dẫn ở `packages/web` của repo đó (nặng hơn và cài lâu hơn nhiều).
