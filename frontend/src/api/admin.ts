import { api } from './client'

export const dashboardStats = () =>
  api.get('/admin/dashboard').then((r) => r.data)

export const betriebInfo = () =>
  api.get('/admin/betrieb').then((r) => r.data)

export const usersListe = () =>
  api.get('/admin/users').then((r) => r.data)

export const userAnlegen = (data: Record<string, unknown>) =>
  api.post('/admin/users', data).then((r) => r.data)
