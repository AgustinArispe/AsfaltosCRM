import { useEffect, useId, useState } from 'react'
import { Icon } from './Icon'
import { type PeriodSelection, periodSelection, QUICK_PERIODS, validDateRange } from './periods'
import { SegmentedControl } from './SegmentedControl'

export function PeriodFilter({
  value,
  onChange,
}: {
  value: PeriodSelection
  onChange: (value: PeriodSelection) => void
}) {
  const id = useId()
  const [draft, setDraft] = useState(value)
  const { preset, from, to } = value
  useEffect(() => setDraft({ preset, from, to }), [preset, from, to])
  const custom = draft.preset === 'custom'
  const invalid = custom && !validDateRange(draft.from, draft.to)
  const choose = (preset: PeriodSelection['preset']) => {
    const next = preset === 'custom' ? { ...draft, preset } : periodSelection(preset)
    setDraft(next)
    if (preset !== 'custom' || validDateRange(next.from, next.to)) onChange(next)
  }
  const changeDate = (key: 'from' | 'to', date: string) => {
    const next: PeriodSelection = { ...draft, preset: 'custom', [key]: date }
    setDraft(next)
    if (validDateRange(next.from, next.to)) onChange(next)
  }
  return (
    <section aria-labelledby={`${id}-title`} className='period-filter'>
      <header>
        <h3
          className='flex items-center gap-2 text-base font-semibold text-[var(--text-primary)]'
          id={`${id}-title`}
        >
          <Icon name='calendar' /> Período
        </h3>
        <p className='mt-1 text-sm text-[var(--text-secondary)]'>
          Elegí un rango rápido o definí fechas específicas.
        </p>
      </header>
      <div className='period-filter__presets'>
        <SegmentedControl
          label='Rangos rápidos de período'
          value={draft.preset}
          segments={QUICK_PERIODS}
          onChange={(preset) => choose(preset as PeriodSelection['preset'])}
        />
        <label className='period-filter__more'>
          <span className='sr-only'>Más períodos</span>
          <select
            className='ui-field'
            value={['three-months', 'year', 'custom'].includes(draft.preset) ? draft.preset : ''}
            onChange={(event) => choose(event.target.value as PeriodSelection['preset'])}
          >
            <option disabled value=''>
              Más períodos
            </option>
            <option value='three-months'>Últimos 3 meses</option>
            <option value='year'>Este año</option>
            <option value='custom'>Personalizado</option>
          </select>
        </label>
      </div>
      <div className='period-filter__dates'>
        {(['from', 'to'] as const).map((key) => (
          <label
            className='grid min-w-0 gap-1.5 text-xs font-medium text-[var(--text-secondary)]'
            key={key}
          >
            {key === 'from' ? 'Desde' : 'Hasta'}
            <input
              aria-describedby={invalid ? `${id}-error` : undefined}
              aria-invalid={invalid}
              className='ui-field min-w-0'
              max={key === 'from' ? draft.to || undefined : undefined}
              min={key === 'to' ? draft.from || undefined : undefined}
              onChange={(event) => changeDate(key, event.target.value)}
              required={custom}
              type='date'
              value={draft[key]}
            />
          </label>
        ))}
      </div>
      {invalid ? (
        <p className='ui-field-error' id={`${id}-error`} role='status'>
          Completá ambas fechas. Hasta debe ser igual o posterior a Desde.
        </p>
      ) : null}
    </section>
  )
}
