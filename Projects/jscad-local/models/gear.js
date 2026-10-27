// Model ví dụ 2: bánh răng đơn giản dùng extrude 2D -> 3D.
import jscad from '@jscad/modeling'

const { circle, polygon } = jscad.primitives
const { union, subtract } = jscad.booleans
const { extrudeLinear } = jscad.extrusions
const { rotateZ } = jscad.transforms
const { colorize } = jscad.colors

export const getParameterDefinitions = () => [
  { name: 'teeth', type: 'int', initial: 16, min: 6, max: 60, caption: 'Số răng' },
  { name: 'radius', type: 'number', initial: 20, min: 5, max: 80, caption: 'Bán kính' },
  { name: 'thickness', type: 'number', initial: 5, min: 1, max: 30, caption: 'Độ dày' }
]

export const main = ({ teeth = 16, radius = 20, thickness = 5 } = {}) => {
  const toothH = radius * 0.15
  const toothW = (2 * Math.PI * radius) / teeth / 2
  const tooth = polygon({
    points: [[radius - 1, -toothW / 2], [radius + toothH, -toothW / 4], [radius + toothH, toothW / 4], [radius - 1, toothW / 2]]
  })
  const toothsArr = []
  for (let i = 0; i < teeth; i++) toothsArr.push(rotateZ((i * 2 * Math.PI) / teeth, tooth))

  const profile = subtract(
    union(circle({ radius, segments: 96 }), ...toothsArr),
    circle({ radius: radius * 0.2, segments: 48 })
  )
  return colorize([0.8, 0.8, 0.3], extrudeLinear({ height: thickness }, profile))
}
