const ARGENTINA_TIME_ZONE = 'America/Argentina/Buenos_Aires'
const MILLISECONDS_PER_DAY = 86_400_000

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('es-AR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZone: ARGENTINA_TIME_ZONE,
})

const QUANTITY_FORMATTER = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 3,
})

export function formatQuantityKg(quantity: string | number): string {
  return `${QUANTITY_FORMATTER.format(Number(quantity))} kg`
}

export function sumQuantitiesKg(quantities: readonly (string | number)[]): number {
  return quantities.reduce<number>((total, quantity) => total + Number(quantity), 0)
}

export function formatDateTime(value: string | Date): string {
  const parts = DATE_TIME_FORMATTER.formatToParts(
    typeof value === 'string' ? new Date(value) : value,
  )
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? ''

  return `${part('day')} ${part('month').replace('.', '')} ${part('year')}, ${part('hour')}:${part('minute')}`
}

export function formatStageDuration(enteredAt: string, now = new Date()): string {
  const elapsedMilliseconds = Math.max(0, now.getTime() - new Date(enteredAt).getTime())
  const elapsedDays = Math.floor(elapsedMilliseconds / MILLISECONDS_PER_DAY)

  if (elapsedDays < 1) return 'Hoy'
  if (elapsedDays < 7) {
    return `${elapsedDays} ${elapsedDays === 1 ? 'día' : 'días'}`
  }

  const elapsedWeeks = Math.floor(elapsedDays / 7)
  if (elapsedDays < 30) {
    return `${elapsedWeeks} ${elapsedWeeks === 1 ? 'semana' : 'semanas'}`
  }

  const elapsedMonths = Math.floor(elapsedDays / 30)
  if (elapsedDays < 365) {
    return `${elapsedMonths} ${elapsedMonths === 1 ? 'mes' : 'meses'}`
  }

  const elapsedYears = Math.floor(elapsedDays / 365)
  return `${elapsedYears} ${elapsedYears === 1 ? 'año' : 'años'}`
}

export function formatTimeInStage(enteredAt: string, now = new Date()): string {
  const duration = formatStageDuration(enteredAt, now)
  return duration === 'Hoy' ? duration : `Hace ${duration}`
}
