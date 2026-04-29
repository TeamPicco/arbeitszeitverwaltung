import { api } from './client'

export interface LoginPayload {
  betriebsnummer: string
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  role: string
  betrieb_id: number
  betrieb_name: string
  user_id: number
  mitarbeiter_id?: number | null
  expires_in_minutes: number
}

export const login = (data: LoginPayload) =>
  api.post<LoginResponse>('/auth/login', data).then((r) => r.data)

export const changePassword = (data: { old_password: string; new_password: string }) =>
  api.post('/auth/change-password', data).then((r) => r.data)

export const getMe = () => api.get('/auth/me').then((r) => r.data)
