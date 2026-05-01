import { api } from './client'

export interface DienstplanEintrag {
  id: number
  mitarbeiter_id: number
  datum: string
  schichttyp: 'arbeit' | 'urlaub' | 'frei'
  start_zeit?: string
  end_zeit?: string
  pause_minuten?: number
}

export const dienstplanWoche = (datum_von: string) =>
  api.get<DienstplanEintrag[]>('/dienstplan/woche', { params: { datum_von } }).then((r) => r.data)

export const dienstplanMonat = (jahr: number, monat_nr: number) =>
  api.get<DienstplanEintrag[]>('/dienstplan/monat', { params: { jahr, monat_nr } }).then((r) => r.data)

export const dienstplanEintragSetzen = (data: {
  mitarbeiter_id: number
  datum: string
  schichttyp: string
  start_zeit?: string
  end_zeit?: string
  pause_minuten?: number
}) => api.post<DienstplanEintrag>('/dienstplan/eintrag', data).then((r) => r.data)

export const dienstplanEintragLoeschen = (id: number) =>
  api.delete(`/dienstplan/${id}`).then((r) => r.data)

export interface DienstplanWunsch {
  id: number
  mitarbeiter_id: number
  datum_von: string
  datum_bis: string
  wunsch_text?: string
  status: 'offen' | 'ausstehend' | 'genehmigt' | 'abgelehnt'
  erstellt_am?: string
  mitarbeiter?: { vorname: string; nachname: string }
}

export const dienstplanWunschEinreichen = (data: {
  datum_von: string
  datum_bis: string
  wunsch_text?: string
}) => api.post<DienstplanWunsch>('/dienstplan/wunsch', data).then((r) => r.data)

export const dienstplanWuenscheListe = () =>
  api.get<DienstplanWunsch[]>('/dienstplan/wuensche').then((r) => r.data)

export const dienstplanWunschEntscheiden = (
  id: number,
  status: 'genehmigt' | 'abgelehnt',
  ablehnungsgrund?: string,
) => api.patch(`/dienstplan/wunsch/${id}`, { status, ablehnungsgrund }).then((r) => r.data)

export const dienstplanEmailVersenden = (monat_nr: number, jahr: number) =>
  api.post('/dienstplan/email-versenden', null, { params: { monat_nr, jahr } }).then((r) => r.data)
