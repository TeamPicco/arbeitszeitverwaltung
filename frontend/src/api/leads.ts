import { api } from './client'

export interface Lead {
  id: number
  firmenname: string
  ort?: string
  branche?: string
  telefon?: string
  email?: string
  website?: string
  status: 'neu' | 'kontaktiert' | 'interessiert' | 'abschluss'
  notizen?: string
  erstellt_am?: string
}

export interface LeadStats {
  gesamt: number
  neu: number
  kontaktiert: number
  interessiert: number
  abschluss: number
}

export const leadsListe = (status?: string, search?: string) =>
  api.get<Lead[]>('/leads/', { params: { status, search } }).then((r) => r.data)

export const leadsStats = () => api.get<LeadStats>('/leads/stats').then((r) => r.data)

export const leadAnlegen = (data: Partial<Lead>) =>
  api.post<Lead>('/leads/', data).then((r) => r.data)

export const leadAktualisieren = (id: number, data: Partial<Lead>) =>
  api.patch<Lead>(`/leads/${id}`, data).then((r) => r.data)

export const leadLoeschen = (id: number) =>
  api.delete(`/leads/${id}`).then((r) => r.data)
