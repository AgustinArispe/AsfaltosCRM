import { useRef, useState, type FormEvent } from 'react'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../shared/Brand'

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 401
          ? 'invalid'
          : 'unexpected',
      )
      emailRef.current?.focus()
    } finally {
      setIsSubmitting(false)
    }
  }

  const errorMessage = error ? ERROR_MESSAGES[error] : null

  return (
    <main className="grid min-h-dvh bg-slate-50 text-slate-900 lg:grid-cols-[minmax(19rem,0.72fr)_minmax(28rem,1fr)]">
      <section className="hidden border-r border-slate-800 bg-slate-950 px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between" aria-label="Identidad FAA">
        <Brand inverse />
        <div className="max-w-sm border-l-2 border-amber-400 pl-6">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-400">
            Acceso interno
          </p>
          <p className="mt-4 text-2xl font-semibold leading-tight tracking-tight">
            Gestión comercial clara, rápida y centralizada.
          </p>
        </div>
        <p className="text-xs text-slate-500">Fábrica Argentina de Asfaltos</p>
      </section>

      <section className="flex items-center justify-center px-5 py-10 sm:px-8" aria-labelledby="login-title">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Brand />
          </div>

          <div className="mb-7">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
              CRM de FAA
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950" id="login-title">
              Ingresar al sistema
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Usá las credenciales asignadas por tu supervisor.
            </p>
          </div>

          <form aria-busy={isSubmitting} className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-800" htmlFor="email">
                Email
              </label>
              <input
                aria-describedby={errorMessage ? 'login-error' : undefined}
                aria-invalid={Boolean(errorMessage)}
                autoComplete="username"
                autoFocus
                className="min-h-11 w-full border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-950 outline-none transition-colors duration-150 placeholder:text-slate-400 hover:border-slate-400 focus:border-amber-600 focus:ring-2 focus:ring-amber-200 disabled:cursor-not-allowed disabled:bg-slate-100 motion-reduce:transition-none"
                disabled={isSubmitting}
                id="email"
                name="email"
                onChange={(event) => setEmail(event.target.value)}
                ref={emailRef}
                required
                type="email"
                value={email}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-800" htmlFor="password">
                Contraseña
              </label>
              <input
                aria-describedby={errorMessage ? 'login-error' : undefined}
                aria-invalid={Boolean(errorMessage)}
                autoComplete="current-password"
                className="min-h-11 w-full border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-950 outline-none transition-colors duration-150 hover:border-slate-400 focus:border-amber-600 focus:ring-2 focus:ring-amber-200 disabled:cursor-not-allowed disabled:bg-slate-100 motion-reduce:transition-none"
                disabled={isSubmitting}
                id="password"
                minLength={1}
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </div>

            {errorMessage ? (
              <p className="border-l-2 border-red-600 bg-red-50 px-3 py-2.5 text-sm font-medium text-red-800" id="login-error" role="alert">
                {errorMessage}
              </p>
            ) : null}

            <button
              className="flex min-h-11 w-full items-center justify-center gap-2 bg-amber-500 px-4 py-2.5 text-sm font-bold text-slate-950 outline-none transition-colors duration-150 hover:bg-amber-400 focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:bg-amber-300 disabled:text-slate-600 motion-reduce:transition-none"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? (
                <>
                  <span aria-hidden="true" className="size-4 animate-spin rounded-full border-2 border-slate-500 border-t-slate-900 motion-reduce:animate-none" />
                  Ingresando…
                </>
              ) : (
                'Ingresar'
              )}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
