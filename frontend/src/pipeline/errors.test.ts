import { describe, expect, it } from 'vitest'

import { ApiError } from '../api/client'
import { pipelineErrorMessage } from './errors'

describe('pipelineErrorMessage', () => {
  it('keeps authentication and generic command failures actionable', () => {
    expect(pipelineErrorMessage(new ApiError(401, 'expired'), 'transition')).toContain(
      'sesión expiró',
    )
    expect(pipelineErrorMessage(new ApiError(500, 'failed'), 'quote')).toContain(
      'No pudimos completar',
    )
  })
})
