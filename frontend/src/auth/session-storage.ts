export const SESSION_TOKEN_KEY = 'faa.crm.access-token'

export function readSessionToken(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeSessionToken(token: string): void {
  window.sessionStorage.setItem(SESSION_TOKEN_KEY, token)
}

export function removeSessionToken(): void {
  try {
    window.sessionStorage.removeItem(SESSION_TOKEN_KEY)
  } catch {
    // A restricted browser context may disable storage; local state is still cleared.
  }
}
