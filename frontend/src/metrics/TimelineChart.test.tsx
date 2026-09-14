import { fireEvent, render, screen } from '@testing-library/react'
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
