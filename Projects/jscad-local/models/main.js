// Model ví dụ: hộp có lỗ + chữ cái nổi.
// Cú pháp giống hệt trên https://openjscad.xyz/v2/ , chỉ khác dòng import ở đầu
// (trên web dùng `const jscad = require('@jscad/modeling')`).
import jscad from '@jscad/modeling'

const { cuboid, cylinder, sphere } = jscad.primitives
const { subtract } = jscad.booleans
const { translate } = jscad.transforms
const { colorize } = jscad.colors

// Tham số hiển thị thành ô nhập ở thanh bên trái (giống OpenJSCAD).
export const getParameterDefinitions = () => [
  { name: 'size', type: 'number', initial: 30, min: 10, max: 100, step: 1, caption: 'Kích thước hộp (mm)' },
  { name: 'holeRadius', type: 'slider', initial: 8, min: 1, max: 14, step: 0.5, caption: 'Bán kính lỗ' },
  { name: 'withBall', type: 'checkbox', checked: true, caption: 'Thêm quả cầu' }
]

export const main = (params) => {
  const { size = 30, holeRadius = 8, withBall = true } = params || {}

  // center: đặt đáy hộp nằm trên mặt lưới (z = 0)
  const box = cuboid({ size: [size, size, size], center: [0, 0, size / 2] })
  const hole = cylinder({ radius: holeRadius, height: size * 2, center: [0, 0, size / 2], segments: 64 })
  let shape = colorize([0.2, 0.6, 1], subtract(box, hole))

  if (withBall) {
    const ball = colorize([1, 0.5, 0.1], translate([0, 0, size + 6], sphere({ radius: 6, segments: 48 })))
    shape = [shape, ball]
  }
  return shape
}
