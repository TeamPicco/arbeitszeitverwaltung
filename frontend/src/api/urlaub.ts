import { api } from './client'

export const urlaubListe = (status?: string) =>
  api.get('/urlaub/', { params: status ? { status } : {} }).then((r) => r.data)

export const urlaubMitarbeiter = (mitarbeiter_id: number) =>
  api.get(`/urlaub/mitarbeiter/${mitarbeiter_id}`).then((r) => r.data)

export const urlaubSaldo = (mitarbeiter_id: number, jahr: number) =>
  api.get(`/urlaub/saldo/${mitarbeiter_id}`, { params: { jahr } }).then((r) => r.data)

export const urlaubBeantragen = (data: {
  mitarbeiter_id: number
  datum_von: string
  datum_bis: string
  anzahl_tage: number
  kommentar?: string
}) => api.post('/urlaub/', data).then((r) => r.data)

export const urlaubEntscheiden = (
  id: number,
  status: 'genehmigt' | 'abgelehnt',
  kommentar?: string
) => api.patch(`/urlaub/${id}`, { status, kommentar }).then((r) => r.data)
