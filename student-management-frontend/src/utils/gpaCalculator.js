export function scoreToGpa(score) {
  if (score > 100 || score < 0) throw new Error('分数范围 0-100')
  if (score >= 90) return 5.0
  if (score >= 85) return 4.5
  if (score >= 82) return 4.0
  if (score >= 78) return 3.5
  if (score >= 75) return 3.0
  if (score >= 72) return 2.5
  if (score >= 68) return 2.0
  if (score >= 64) return 1.5
  if (score >= 60) return 1.0
  return 0
}
