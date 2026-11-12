import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TimelineChart } from './DashboardVisuals'
import type { TimelineMetrics } from './types'

function dailyTimeline(dayCount: number): TimelineMetrics {
  return {
    period: {
      from: '2026-01-01T03:00:00Z',
      to: '2026-04-01T03:00:00Z',
    },
    granularity: 'day',
    timezone: 'America/Argentina/Buenos_Aires',
    items: Array.from({ length: dayCount }, (_, index) => {
      const date = new Date(Date.UTC(2026, 0, index + 1))
      return {
        bucket: date.toISOString().slice(0, 10),
        leads_created: 1,
        won: index % 2,
        lost: index % 3 === 0 ? 1 : 0,
        kg_won: '0.000',
        kg_lost: '0.000',
      }
    }),
  }
}

describe('TimelineChart daily X axis', () => {
  const defaultProps = {
    error: undefined,
    hasActiveFilters: false,
    onDrilldown: vi.fn(),
    onRetry: vi.fn(),
  }

  it('explains the units and dates without replacing the three series or exact data', () => {
    render(<TimelineChart {...defaultProps} timeline={dailyTimeline(30)} />)

    expect(screen.getByRole('region', { name: 'Evolución comercial' })).toHaveClass(
      'dashboard-timeline-surface',
    )
    expect(
      screen.getByText('Creadas por fecha de alta. Ganadas y pérdidas por fecha de cierre.'),
    ).toBeVisible()
    expect(screen.getByText('Cantidad de oportunidades')).toBeVisible()
    expect(screen.getByText('Días del período')).toBeVisible()
    expect(screen.getByText('Seleccioná un día para ver sus movimientos.')).toBeVisible()
    expect(screen.getByRole('list', { name: 'Series de evolución' }).children).toHaveLength(3)

    fireEvent.click(screen.getByText('Ver datos exactos de evolución'))
    expect(screen.getByRole('table')).toHaveTextContent('Kg ganados')
    expect(screen.getByRole('table').querySelectorAll('tbody tr')).toHaveLength(30)
  })

  it('uses evenly spaced integer ticks and keeps bar magnitudes on that scale', () => {
    const timeline = dailyTimeline(2)
    timeline.items[0].leads_created = 7
    render(<TimelineChart {...defaultProps} timeline={timeline} />)

    const chart = screen.getByLabelText('Evolución comercial diaria')
    expect(
      Array.from(chart.querySelectorAll('.dashboard-daily-chart__grid text')).map(
        (tick) => tick.textContent,
      ),
    ).toEqual(['0', '3', '6', '9'])
    const firstBar = chart.querySelector('[data-series="created"]')
    expect(Number(firstBar?.getAttribute('height'))).toBeCloseTo((7 / 9) * 188)
  })

  it('measures the plot after async data arrives and disconnects its resize observer', () => {
    let resize: ((entries: { contentRect: { width: number } }[]) => void) | undefined
    const observe = vi.fn()
    const disconnect = vi.fn()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: NonNullable<typeof resize>) {
          resize = callback
        }
        observe = observe
        disconnect = disconnect
      },
    )
    const { rerender, unmount } = render(<TimelineChart {...defaultProps} />)
    expect(observe).not.toHaveBeenCalled()

    rerender(<TimelineChart {...defaultProps} timeline={dailyTimeline(30)} />)
    expect(observe).toHaveBeenCalledWith(screen.getByLabelText('Evolución comercial diaria'))
    act(() => resize?.([{ contentRect: { width: 1600 } }]))
    expect(screen.getByLabelText('Evolución comercial diaria')).toHaveAttribute(
      'viewBox',
      '0 0 1600 256',
    )
    act(() => resize?.([{ contentRect: { width: 350 } }]))
    expect(screen.getByLabelText('Evolución comercial diaria')).toHaveAttribute(
      'viewBox',
      '0 0 896 256',
    )
    unmount()
    expect(disconnect).toHaveBeenCalledOnce()
  })

  it('keeps zero activity honest and retains the exact-data disclosure', () => {
    const timeline = dailyTimeline(1)
    timeline.items[0] = { ...timeline.items[0], leads_created: 0, won: 0, lost: 0 }
    render(<TimelineChart {...defaultProps} timeline={timeline} />)

    expect(screen.getByText('No hay evolución en el período')).toBeVisible()
    expect(screen.queryByLabelText('Evolución comercial diaria')).not.toBeInTheDocument()
    expect(screen.getByText('Ver datos exactos de evolución')).toBeVisible()
  })

  it('alternates subtle daily backgrounds including days with no movements', () => {
    const timeline = dailyTimeline(4)
    timeline.items[1] = { ...timeline.items[1], leads_created: 0, won: 0, lost: 0 }
    render(<TimelineChart {...defaultProps} timeline={timeline} />)

    const chart = screen.getByLabelText('Evolución comercial diaria')
    const bands = chart.querySelectorAll('[data-day-band]')
    expect(Array.from(bands).map((band) => band.getAttribute('data-day-band'))).toEqual([
      '2026-01-02',
      '2026-01-04',
    ])
    expect(bands[0]).toHaveAttribute('focusable', 'false')
    expect(screen.getAllByRole('button', { name: /Abrir movimientos de/ })).toHaveLength(4)
    expect(Number(bands[0].getAttribute('width'))).toBeGreaterThan(0)
    expect(chart.firstElementChild).toBe(bands[0])
  })

  it('thins only labels while keeping every bar, hit target, and exact tooltip', () => {
    const onDrilldown = vi.fn()
    render(
      <TimelineChart
        error={undefined}
        hasActiveFilters={false}
        onDrilldown={onDrilldown}
        onRetry={vi.fn()}
        timeline={dailyTimeline(90)}
      />,
    )

    const chart = screen.getByLabelText('Evolución comercial diaria')
    expect(chart.querySelectorAll('.dashboard-daily-chart__label')).toHaveLength(30)
    expect(chart.querySelectorAll('[data-series="created"]')).toHaveLength(90)

    const dailyTargets = screen.getAllByRole('button', { name: /Abrir movimientos de/ })
    expect(dailyTargets).toHaveLength(90)

    const hiddenLabelDay = screen.getByRole('button', {
      name: /Abrir movimientos de 31 de marzo: 1 creadas, 1 ganadas, 0 pérdidas/,
    })
    expect(chart.querySelector('[data-axis-bucket="2026-03-31"]')).not.toBeInTheDocument()

    fireEvent.mouseEnter(hiddenLabelDay)
    expect(screen.getByRole('tooltip')).toHaveTextContent('31 de marzo')

    fireEvent.click(hiddenLabelDay)
    expect(onDrilldown).toHaveBeenCalledWith(
      expect.objectContaining({ bucket: '2026-03-31', granularity: 'day' }),
    )
  })
})
