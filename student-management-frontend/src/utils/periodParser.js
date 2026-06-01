export function parsePeriod(periodStr) {
  const parts = periodStr.trim().split('-')
  if (parts.length !== 2) throw new Error(`无法解析节次: ${periodStr}`)
  const start = parseInt(parts[0])
  const end = parseInt(parts[1])
  if (start > end) throw new Error(`起始节号不能大于结束节号: ${periodStr}`)
  return { start, end }
}

export function doPeriodsOverlap(period1, period2) {
  const a = parsePeriod(period1)
  const b = parsePeriod(period2)
  return a.start <= b.end && b.start <= a.end
}
