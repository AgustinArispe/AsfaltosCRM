import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import './styles.css'

const rootElement = document.getElementById('root')
if (!rootElement) throw new Error('No se encontró el contenedor raíz de FAA CRM.')

createRoot(rootElement).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
