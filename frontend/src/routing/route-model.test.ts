import { describe, expect, it } from 'vitest'

import {
  normalizePath,
  owningWorkspace,
  parseRoute,
  pathForRoute,
  readHistoryOrigin,
} from './route-model'

describe('CRM-018 route model', () => {
  it('parses every canonical workspace and detail path', () => {
    expect(parseRoute('/pipeline/')).toEqual({ kind: 'workspace', workspace: 'pipeline' })
    expect(parseRoute('/pipeline/opportunities/10')).toEqual({
      kind: 'opportunity',
      opportunityId: 10,
      surface: 'pipeline',
    })
    expect(parseRoute('/lost/opportunities/11')).toEqual({
      kind: 'opportunity',
      opportunityId: 11,
      surface: 'lost',
    })
    expect(parseRoute('/customers/12')).toEqual({ kind: 'customer', customerId: 12 })
    expect(parseRoute('/whatsapp/conversations/13')).toEqual({
      kind: 'conversation',
      conversationId: 13,
    })
    expect(parseRoute('/whatsapp-sends/14')).toEqual({ kind: 'broadcast', broadcastId: 14 })
  })

  it('serializes routes and resolves their owning workspace fallback', () => {
    const route = { kind: 'conversation', conversationId: 13 } as const
    expect(pathForRoute(route)).toBe('/whatsapp/conversations/13')
    expect(owningWorkspace(route)).toEqual({ kind: 'workspace', workspace: 'whatsapp' })
    expect(owningWorkspace({ kind: 'opportunity', opportunityId: 7, surface: 'lost' })).toEqual({
      kind: 'workspace',
      workspace: 'lost',
    })
    expect(pathForRoute({ kind: 'workspace', workspace: 'users' })).toBe('/users')
  })

  it('rejects non-canonical or unsafe paths and untyped history data', () => {
    expect(normalizePath('')).toBe('/')
    expect(normalizePath('/customers/1/')).toBe('/customers/1')
    expect(parseRoute('/opportunities/1')).toBeNull()
    expect(parseRoute('/customers/0')).toBeNull()
    expect(parseRoute('/whatsapp/conversations/1.5')).toBeNull()
    expect(parseRoute('/not-a-workspace')).toBeNull()
    expect(readHistoryOrigin({ crmOrigin: { kind: 'workspace', workspace: 'customers' } })).toEqual(
      {
        kind: 'workspace',
        workspace: 'customers',
      },
    )
    expect(
      readHistoryOrigin({ crmOrigin: { kind: 'workspace', workspace: 'external' } }),
    ).toBeNull()
    expect(readHistoryOrigin({ crmOrigin: '/arbitrary-return-url' })).toBeNull()
    expect(readHistoryOrigin(null)).toBeNull()
  })
})
