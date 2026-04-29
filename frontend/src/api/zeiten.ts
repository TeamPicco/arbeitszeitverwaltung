import { api } from './client'

export const zeitenMonat = (mitarbeiter_id: number, monat: number, jahr: number) =>
  api
    .get(`/zeiten/monat/${mitarbeiter_id}`, { params: { monat, jahr } })
    .then((r) => r.data)

export const zeitenManuell = (data: {
  mitarbeiter_id: number
  datum: string
  start_zeit: string
  ende_zeit: string
  pause_minuten?: number
  manuell_kommentar?: string
}) => api.post('/zeiten/manuell', data).then((r) => r.data)

export const azkMonat = (mitarbeiter_id: number, monat: number, jahr: number) =>
  api
    .get(`/zeiten/azk/${mitarbeiter_id}`, { params: { monat, jahr } })
    .then((r) => r.data)
