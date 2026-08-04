const QUANTITY_FORMATTER = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 3,
})

export function formatQuantityKg(quantity: string | number): string {
  return `${QUANTITY_FORMATTER.format(Number(quantity))} kg`
}

export function formatTimeInStage(enteredAt: string, now = new Date()): string {
  const enteredTime = new Date(enteredAt).getTime()
  const elapsedMilliseconds = Math.max(0, now.getTime() - enteredTime)
  const elapsedHours = Math.floor(elapsedMilliseconds / 3_600_000)

  if (elapsedHours < 1) return 'Hace menos de 1 h'
  if (elapsedHours < 24) return `Hace ${elapsedHours} h`

  const elapsedDays = Math.floor(elapsedHours / 24)
  if (elapsedDays < 30) {
    return `Hace ${elapsedDays} ${elapsedDays === 1 ? 'día' : 'días'}`
  }

  const elapsedMonths = Math.floor(elapsedDays / 30)
  if (elapsedMonths < 12) {
    return `Hace ${elapsedMonths} ${elapsedMonths === 1 ? 'mes' : 'meses'}`
  }

  const elapsedYears = Math.floor(elapsedMonths / 12)
  return `Hace ${elapsedYears} ${elapsedYears === 1 ? 'año' : 'años'}`
}
