import { api } from './client'

export const mitarbeiterListe = (aktiv?: boolean) =>
  api.get('/mitarbeiter/', { params: aktiv !== undefined ? { aktiv } : {} }).then((r) => r.data)

export const mitarbeiterDetail = (id: number) =>
  api.get(`/mitarbeiter/${id}`).then((r) => r.data)

export const mitarbeiterAnlegen = (data: Record<string, unknown>) =>
  api.post('/mitarbeiter/', data).then((r) => r.data)

export const mitarbeiterAktualisieren = (id: number, data: Record<string, unknown>) =>
  api.patch(`/mitarbeiter/${id}`, data).then((r) => r.data)
