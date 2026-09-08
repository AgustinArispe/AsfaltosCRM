import type { LeadSource } from '../pipeline/types'
import type { MetricsFilters, TimelineGranularity } from './types'

export type DashboardPeriodPreset = 'month' | 'last-three-months' | 'year' | 'custom'

export type DashboardFilters = MetricsFilters & {
  preset: DashboardPeriodPreset
  customStart: string
  customEnd: string
}

const BUENOS_AIRES_OFFSET = '-03:00'

function partsInBuenosAires(now: Date): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat('en-CA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'America/Argentina/Buenos_Aires',
  }).formatToParts(now)
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((item) => item.type === type)?.value ?? '0')
  return { year: part('year'), month: part('month'), day: part('day') }
}

function dateText(year: number, month: number, day: number): string {
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function utcDate(year: number, month: number, day: number): Date {
  return new Date(Date.UTC(year, month - 1, day))
}

function addDays(date: string, days: number): string {
  const [year, month, day] = date.split('-').map(Number)
  const result = utcDate(year, month, day + days)
  return dateText(result.getUTCFullYear(), result.getUTCMonth() + 1, result.getUTCDate())
}

function firstOfMonth(year: number, month: number): string {
  return dateText(year, month, 1)
}

function monthBoundary(year: number, month: number, offset: number): string {
  const date = utcDate(year, month + offset, 1)
  return dateText(date.getUTCFullYear(), date.getUTCMonth() + 1, 1)
}

function serializeBoundary(date: string): string {
  return `${date}T00:00:00${BUENOS_AIRES_OFFSET}`
}

export function defaultDashboardFilters(now = new Date()): DashboardFilters {
  const { year, month } = partsInBuenosAires(now)
  const from = firstOfMonth(year, month)
  const to = monthBoundary(year, month, 1)
  return {
    preset: 'month',
    customStart: from,
    customEnd: addDays(to, -1),
    from: serializeBoundary(from),
    to: serializeBoundary(to),
    source: null,
    productId: null,
    province: null,
  }
}

export function filtersForPreset(
  preset: Exclude<DashboardPeriodPreset, 'custom'>,
  current: DashboardFilters,
  now = new Date(),
): DashboardFilters {
  const { year, month } = partsInBuenosAires(now)
  const from =
    preset === 'month'
      ? firstOfMonth(year, month)
      : preset === 'last-three-months'
        ? monthBoundary(year, month, -2)
        : firstOfMonth(year, 1)
  const to = monthBoundary(year, month, 1)
  return {
    ...current,
    preset,
    customStart: from,
    customEnd: addDays(to, -1),
    from: serializeBoundary(from),
    to: serializeBoundary(to),
  }
}

export function filtersForCustomRange(
  current: DashboardFilters,
  customStart: string,
  customEnd: string,
): DashboardFilters {
  const isValid = /^\d{4}-\d{2}-\d{2}$/.test(customStart) && /^\d{4}-\d{2}-\d{2}$/.test(customEnd)
  const endBoundary = isValid ? addDays(customEnd, 1) : customEnd
  return {
    ...current,
    preset: 'custom',
    customStart,
    customEnd,
    from: serializeBoundary(customStart),
    to: serializeBoundary(endBoundary),
  }
}

export function timelineGranularity(filters: MetricsFilters): TimelineGranularity {
  const from = filters.from.slice(0, 10)
  const to = filters.to.slice(0, 10)
  const [fromYear, fromMonth, fromDay] = from.split('-').map(Number)
  const [toYear, toMonth, toDay] = to.split('-').map(Number)
  const days = Math.round(
    (utcDate(toYear, toMonth, toDay).getTime() - utcDate(fromYear, fromMonth, fromDay).getTime()) /
      86_400_000,
  )
  if (days <= 14) return 'day'
  if (days <= 120) return 'week'
  return 'month'
}

export function dashboardOutcomeQuery(filters: DashboardFilters): string {
  const query = new URLSearchParams({
    period: filters.preset === 'last-three-months' ? 'three-months' : filters.preset,
    from: filters.customStart,
    to: filters.customEnd,
  })
  if (filters.source) query.set('source', filters.source)
  if (filters.productId) query.set('product', String(filters.productId))
  if (filters.province) query.set('province', filters.province)
  return query.toString()
}

export function dashboardFiltersFromQuery(search: string, now = new Date()): DashboardFilters {
  const query = new URLSearchParams(search)
  const defaults = defaultDashboardFilters(now)
  const period = query.get('period')
  const preset: DashboardPeriodPreset =
    period === 'three-months'
      ? 'last-three-months'
      : period === 'year' || period === 'custom' || period === 'month'
        ? period
        : defaults.preset
  const from = query.get('from')
  const to = query.get('to')
  const validDates =
    from !== null &&
    to !== null &&
    /^\d{4}-\d{2}-\d{2}$/.test(from) &&
    /^\d{4}-\d{2}-\d{2}$/.test(to) &&
    from <= to
  const periodFilters = validDates
    ? filtersForCustomRange({ ...defaults, preset }, from, to)
    : preset === 'custom'
      ? defaults
      : filtersForPreset(preset, defaults, now)
  const source = query.get('source')
  const productId = Number(query.get('product'))
  return {
    ...periodFilters,
    preset,
    source: source === 'WEB' || source === 'WHATSAPP' ? source : null,
    productId: Number.isInteger(productId) && productId > 0 ? productId : null,
    province: query.get('province')?.trim() || null,
  }
}

export function activeFilterCount(filters: DashboardFilters): number {
  return (
    Number(filters.source !== null) +
    Number(filters.productId !== null) +
    Number(filters.province !== null) +
    Number(filters.preset !== 'month')
  )
}

export function sourceLabel(source: LeadSource): string {
  return source === 'WEB' ? 'Web' : 'WhatsApp'
}

export function pipelineDimensions(
  filters: DashboardFilters,
): Pick<MetricsFilters, 'source' | 'productId' | 'province'> {
  return {
    source: filters.source,
    productId: filters.productId,
    province: filters.province,
  }
}
