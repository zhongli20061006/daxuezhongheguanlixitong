export function startCooldown(studentId, scheduleId) {
  const key = `cooldown_${studentId}_${scheduleId}`
  localStorage.setItem(key, (Date.now() + 120 * 1000).toString())
}

export function getCooldownRemaining(studentId, scheduleId) {
  const key = `cooldown_${studentId}_${scheduleId}`
  const endTime = localStorage.getItem(key)
  if (!endTime) return 0
  const remaining = Math.ceil((parseInt(endTime) - Date.now()) / 1000)
  return remaining > 0 ? remaining : 0
}
