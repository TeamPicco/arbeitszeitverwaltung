import { api } from './client'

export const pinLookup = (betrieb_id: number, pin: string) =>
  api.post('/stempel/pin', { betrieb_id, pin }).then((r) => r.data)

export const stempelEvent = (data: {
  mitarbeiter_id: number
  action: string
  geraet_id?: string
}) => api.post('/stempel/event', data).then((r) => r.data)

export const stempelStatus = (mitarbeiter_id: number) =>
  api.get(`/stempel/status/${mitarbeiter_id}`).then((r) => r.data)
