import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  role: string | null
  betriebId: number | null
  betriebName: string | null
  userId: number | null
  mitarbeiterId: number | null
  setAuth: (data: {
    token: string
    role: string
    betrieb_id: number
    betrieb_name: string
    user_id: number
    mitarbeiter_id?: number | null
  }) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      betriebId: null,
      betriebName: null,
      userId: null,
      mitarbeiterId: null,
      setAuth: (data) =>
        set({
          token: data.token,
          role: data.role,
          betriebId: data.betrieb_id,
          betriebName: data.betrieb_name,
          userId: data.user_id,
          mitarbeiterId: data.mitarbeiter_id ?? null,
        }),
      logout: () =>
        set({
          token: null,
          role: null,
          betriebId: null,
          betriebName: null,
          userId: null,
          mitarbeiterId: null,
        }),
    }),
    { name: 'complio-auth' }
  )
)
