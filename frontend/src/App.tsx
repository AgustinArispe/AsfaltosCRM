import { useEffect, useState } from 'react'

type HealthResponse = {
  status: string
  database: string
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('Backend unavailable')
        return response.json() as Promise<HealthResponse>
      })
      .then(setHealth)
      .catch(() => setError(true))
  }, [])

  return (
    <main>
      <section aria-labelledby="project-title">
        <p className="eyebrow">Base técnica</p>
        <h1 id="project-title">Fábrica Argentina de Asfaltos</h1>
        <p>CRM en preparación.</p>
        <p className={error ? 'status error' : 'status'}>
          {error
            ? 'No se pudo conectar con la API.'
            : health
              ? `API y PostgreSQL: ${health.status}`
              : 'Verificando conexión con la API…'}
        </p>
      </section>
    </main>
  )
}
