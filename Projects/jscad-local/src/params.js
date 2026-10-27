// Lấy giá trị mặc định & dựng form cho getParameterDefinitions (bản rút gọn của OpenJSCAD).
export const defaultParams = (defs = []) => {
  const values = {}
  for (const d of defs) {
    if (d.type === 'group') continue
    if (d.type === 'checkbox') values[d.name] = d.checked ?? d.initial ?? false
    else if (d.type === 'choice') values[d.name] = d.initial ?? d.default ?? (d.values ? d.values[0] : undefined)
    else values[d.name] = d.initial ?? d.default
  }
  return values
}

export const renderParamsForm = (container, defs, values, onChange) => {
  container.innerHTML = ''
  for (const d of defs) {
    if (d.type === 'group') {
      const h = document.createElement('h3')
      h.textContent = d.caption || d.name
      h.style.fontSize = '14px'
      container.appendChild(h)
      continue
    }
    const label = document.createElement('label')
    label.textContent = d.caption || d.name
    let input
    if (d.type === 'choice') {
      input = document.createElement('select')
      d.values.forEach((v, i) => {
        const o = document.createElement('option')
        o.value = i
        o.textContent = d.captions ? d.captions[i] : v
        if (v === values[d.name]) o.selected = true
        input.appendChild(o)
      })
      input.onchange = () => onChange(d.name, d.values[input.value])
    } else {
      input = document.createElement('input')
      const typeMap = { checkbox: 'checkbox', slider: 'range', number: 'number', int: 'number', float: 'number', text: 'text', color: 'color' }
      input.type = typeMap[d.type] || 'text'
      for (const k of ['min', 'max', 'step']) if (d[k] !== undefined) input[k] = d[k]
      if (d.type === 'int' && d.step === undefined) input.step = 1
      if (input.type === 'checkbox') input.checked = !!values[d.name]
      else input.value = values[d.name] ?? ''
      const read = () => {
        if (input.type === 'checkbox') return input.checked
        if (input.type === 'number' || input.type === 'range') return d.type === 'int' ? parseInt(input.value, 10) : parseFloat(input.value)
        return input.value
      }
      const evt = input.type === 'range' || input.type === 'checkbox' ? 'input' : 'change'
      input.addEventListener(evt, () => onChange(d.name, read()))
    }
    label.appendChild(input)
    container.appendChild(label)
  }
}
