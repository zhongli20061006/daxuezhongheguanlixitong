function parseRangePart(part) {
  const m = part.trim().match(/^(\d+)\s*-\s*(\d+)(?:\((单|双)\))?$/)
  if (m) {
    const start = parseInt(m[1])
    const end = parseInt(m[2])
    let parity = 'all'
    if (m[3] === '单') parity = 'odd'
    else if (m[3] === '双') parity = 'even'
    return { start, end, parity }
  }
  const single = parseInt(part.trim())
  if (!isNaN(single)) return { start: single, end: single, parity: 'all' }
  return null
}

export function isWeekInRange(week, weeksStr) {
  const parts = weeksStr.split(',')
  for (const part of parts) {
    const range = parseRangePart(part)
    if (!range) continue
    if (week < range.start || week > range.end) continue
    if (range.parity === 'odd' && week % 2 === 0) continue
    if (range.parity === 'even' && week % 2 === 1) continue
    return true
  }
  return false
}
