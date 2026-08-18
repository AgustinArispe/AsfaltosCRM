import { type FormEvent, useEffect, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../shared/Brand'
import { Button } from '../shared/Button'

type LoginError = 'invalid' | 'unexpected' | null

const ERROR_MESSAGES = {
  invalid: 'El email o la contraseña no son correctos.',
  unexpected: 'No pudimos iniciar sesión. Intentá nuevamente.',
} as const

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<LoginError>(null)
  const emailRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (error) emailRef.current?.focus()
  }, [error])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 401 ? 'invalid' : 'unexpected',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const errorMessage = error ? ERROR_MESSAGES[error] : null

  return (
    <main className='grid min-h-dvh bg-[var(--surface-secondary)] text-[var(--text-primary)] lg:grid-cols-[18rem_minmax(28rem,1fr)]'>
      <section
        className='hidden border-e border-[var(--strong-border)] bg-[var(--brand-deep)] px-7 py-7 text-[var(--on-brand)] lg:flex lg:flex-col lg:justify-between'
        aria-label='Identidad FAA'
      >
        <Brand inverse />
        <p className='max-w-md text-sm leading-6 text-[var(--text-tertiary)]'>
          Acceso interno al sistema de gestión comercial.
        </p>
        <p className='text-xs text-[var(--text-tertiary)]'>Fábrica Argentina de Asfaltos</p>
      </section>

      <section
        className='flex items-center justify-center px-5 py-10 sm:px-8'
        aria-labelledby='login-title'
      >
        <div className='ui-panel w-full max-w-sm px-5 py-6 sm:px-6'>
          <div className='mb-10 lg:hidden'>
            <Brand />
          </div>

          <div className='mb-6'>
            <h1
              className='text-xl font-semibold tracking-tight text-[var(--text-primary)]'
              id='login-title'
            >
              Ingresar al sistema
            </h1>
            <p className='mt-2 text-sm leading-6 text-[var(--text-secondary)]'>
              Usá las credenciales asignadas por tu supervisor.
            </p>
          </div>

          <form aria-busy={isSubmitting} className='space-y-5' onSubmit={handleSubmit}>
            <div>
              <label className='ui-label' htmlFor='email'>
                Email
              </label>
              <input
                aria-describedby={errorMessage ? 'login-error' : undefined}
                aria-invalid={Boolean(errorMessage)}
                autoComplete='username'
                className='ui-field text-base'
                disabled={isSubmitting}
                id='email'
                name='email'
                onChange={(event) => setEmail(event.target.value)}
                ref={emailRef}
                required
                type='email'
                value={email}
              />
            </div>

            <div>
              <label className='ui-label' htmlFor='password'>
                Contraseña
              </label>
              <input
                aria-describedby={errorMessage ? 'login-error' : undefined}
                aria-invalid={Boolean(errorMessage)}
                autoComplete='current-password'
                className='ui-field text-base'
                disabled={isSubmitting}
                id='password'
                minLength={1}
                name='password'
                onChange={(event) => setPassword(event.target.value)}
                required
                type='password'
                value={password}
              />
            </div>

            {errorMessage ? (
              <p
                className='rounded-[var(--radius-control)] border border-[var(--destructive-border)] bg-[var(--destructive-subtle)] px-3 py-2.5 text-sm font-medium text-[var(--destructive-text)]'
                id='login-error'
                role='alert'
              >
                {errorMessage}
              </p>
            ) : null}

            <Button className='w-full' disabled={isSubmitting} type='submit' variant='primary'>
              {isSubmitting ? (
                <>
                  <span
                    aria-hidden='true'
                    className='size-4 animate-spin rounded-full border-2 border-[var(--strong-border)] border-t-[var(--text-primary)] motion-reduce:animate-none'
                  />
                  Ingresando…
                </>
              ) : (
                'Ingresar'
              )}
            </Button>
          </form>
        </div>
      </section>
    </main>
  )
}
