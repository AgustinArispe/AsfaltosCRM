export type PeriodPreset =
  | 'all'
  | 'today'
  | 'last-7-days'
  | 'last-15-days'
  | 'month'
  | 'three-months'
  | 'year'
  | 'custom'

export type PeriodSelection = { preset: PeriodPreset; from: string; to: string }

export const QUICK_PERIODS = [
  { value: 'all', label: 'Todo' },
  { value: 'today', label: 'Hoy' },
  { value: 'last-7-days', label: 'Últimos 7 días' },
  { value: 'last-15-days', label: 'Últimos 15 días' },
  { value: 'month', label: 'Este mes' },
] as const

export function isPeriodPreset(value: string | null): value is PeriodPreset {
  return [...QUICK_PERIODS.map((item) => item.value), 'three-months', 'year', 'custom'].some(
    (preset) => preset === value,
  )
}

export function addCalendarDays(value: string, days: number): string {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10)
}

export function validDateRange(from: string, to: string): boolean {
  const validDate = (value: string) =>
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(`${value}T00:00:00Z`)) &&
    new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value
  return validDate(from) && validDate(to) && from <= to
}

export function periodSelection(
  preset: Exclude<PeriodPreset, 'custom'>,
  now = new Date(),
): PeriodSelection {
  if (preset === 'all') return { preset, from: '', to: '' }
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Argentina/Buenos_Aires',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now)
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? ''
  const today = `${part('year')}-${part('month')}-${part('day')}`
  const year = Number(part('year'))
  const month = Number(part('month'))
  if (preset === 'today' || preset === 'last-7-days' || preset === 'last-15-days') {
    return {
      preset,
      from: addCalendarDays(today, preset === 'today' ? 0 : preset === 'last-7-days' ? -6 : -14),
      to: today,
    }
  }
  const from =
    preset === 'year'
      ? `${year}-01-01`
      : new Date(Date.UTC(year, month - (preset === 'three-months' ? 3 : 1), 1))
          .toISOString()
          .slice(0, 10)
  const to = new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10)
  return { preset, from, to }
}
