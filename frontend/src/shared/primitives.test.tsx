import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Badge } from './Badge'
import { Button, buttonClassName } from './Button'
import { ConfirmationDialog } from './ConfirmationDialog'
import { Checkbox, Input, Radio, Search, Select } from './FormControls'
import { Icon } from './Icon'
import { IconButton } from './IconButton'
import { DropdownMenu, Popover, Toast, Tooltip } from './OverlayPrimitives'
import { SegmentedControl } from './SegmentedControl'
import {
  Avatar,
  ChartSurface,
  EmptyState,
  ErrorState,
  NotificationBadge,
  Skeleton,
  Surface,
} from './StatusStates'

describe('shared CRM-018 primitives', () => {
  it('renders buttons, icons, badges, and accessible status primitives', () => {
    const onClick = vi.fn()
    const { container } = render(
      <>
        <Button onClick={onClick} variant='primary'>
          Guardar
        </Button>
        <IconButton icon='menu' label='Abrir navegación' onClick={onClick} size='compact' />
        <Icon name='dashboard' />
        <Badge tone='won'>Ganada</Badge>
        <Surface>Contenido</Surface>
        <Skeleton />
        <Avatar name='María del Carmen' />
        <NotificationBadge count={3} />
        <NotificationBadge count={100} />
        <ChartSurface title='Actividad'>Datos</ChartSurface>
      </>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
    expect(onClick).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Ganada')).toHaveClass('rounded-full')
    expect(screen.getByText('Ganada')).toHaveClass('h-6', 'px-2.5', 'text-[0.8125rem]')
    expect(screen.getByRole('button', { name: 'Guardar' })).toHaveClass('h-11', 'text-sm')
    expect(screen.getByRole('button', { name: 'Abrir navegación' })).toHaveClass('size-9')
    expect(screen.getByRole('img', { name: 'María del Carmen' })).toHaveTextContent('MD')
    expect(
      screen.getByRole('status', { name: '3 notificaciones activas sin leer' }),
    ).toHaveTextContent('3')
    expect(
      screen.getByRole('status', { name: '100 notificaciones activas sin leer' }),
    ).toHaveTextContent('99+')
    expect(screen.getByRole('heading', { name: 'Actividad' })).toBeInTheDocument()
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    expect(buttonClassName({ variant: 'danger', size: 'compact', className: 'extra' })).toContain(
      'extra',
    )
    expect(buttonClassName()).toContain('surface-raised')
  })

  it('associates form labels, descriptions, errors, and choice controls', () => {
    const onChange = vi.fn()
    render(
      <>
        <Input description='Formato comercial' id='name' label='Nombre' />
        <Search id='search' label='Buscar clientes' />
        <Select error='Elegí una opción' id='type' label='Tipo'>
          <option value=''>Seleccionar</option>
        </Select>
        <Checkbox id='active' label='Activo' onChange={onChange} />
        <Radio id='sales' label='Ventas' name='area' onChange={onChange} />
      </>,
    )

    expect(screen.getByLabelText('Nombre')).toHaveAttribute('aria-describedby', 'name-message')
    expect(screen.getByLabelText('Buscar clientes')).toHaveAttribute('type', 'search')
    expect(screen.getByLabelText('Tipo')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Elegí una opción')).toHaveClass('ui-field-error')
    fireEvent.click(screen.getByLabelText('Activo'))
    fireEvent.click(screen.getByLabelText('Ventas'))
    expect(onChange).toHaveBeenCalledTimes(2)
  })

  it('uses controlled segmented controls and concise empty or error feedback', () => {
    const onChange = vi.fn()
    const onRetry = vi.fn()
    render(
      <>
        <SegmentedControl
          label='Estado'
          onChange={onChange}
          segments={[
            { value: 'all', label: 'Todos' },
            { value: 'done', label: 'Completados', disabled: true },
          ]}
          value='all'
        />
        <EmptyState description='No hay registros.' title='Sin resultados' />
        <ErrorState message='No pudimos cargar.' onRetry={onRetry} />
      </>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Todos' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onChange).toHaveBeenCalledWith('all')
    expect(screen.getByRole('button', { name: 'Completados' })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar.')
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('keeps overlays dismissible and exposes tooltip or toast feedback accessibly', () => {
    const onDismiss = vi.fn()
    render(
      <>
        <Tooltip label='Ayuda de campo'>
          <button type='button'>Ayuda</button>
        </Tooltip>
        <Popover label='Opciones' trigger='Abrir'>
          Contenido
        </Popover>
        <DropdownMenu label='Más acciones' trigger='Más'>
          Acción
        </DropdownMenu>
        <Toast message='Guardado' onDismiss={onDismiss} />
      </>,
    )

    expect(screen.getByText('Ayuda').parentElement).toHaveAttribute(
      'data-tooltip',
      'Ayuda de campo',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    expect(screen.getByRole('dialog', { name: 'Opciones' })).toHaveTextContent('Contenido')
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog', { name: 'Opciones' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Más' }))
    expect(screen.getByRole('dialog', { name: 'Más acciones' })).toHaveTextContent('Acción')
    fireEvent.mouseDown(document.body)
    expect(screen.queryByRole('dialog', { name: 'Más acciones' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar mensaje' }))
    expect(onDismiss).toHaveBeenCalledOnce()
    expect(screen.getByRole('status')).toHaveTextContent('Guardado')
  })

  it('uses a consistent deliberate confirmation pattern for destructive mutations', () => {
    const onCancel = vi.fn()
    const onConfirm = vi.fn()
    render(
      <ConfirmationDialog
        confirmLabel='Eliminar'
        error='No se pudo completar.'
        isOpen
        onCancel={onCancel}
        onConfirm={onConfirm}
        pendingLabel='Eliminando…'
        title='Eliminar cliente'
        variant='danger'
      >
        <p>La acción conserva el historial.</p>
      </ConfirmationDialog>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo completar.')
    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
