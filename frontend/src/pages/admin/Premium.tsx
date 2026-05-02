import { useState } from 'react'
import { Shield, FileText, Clock, Download, Scale, Lock, CheckCircle, AlertTriangle } from 'lucide-react'
import { Card } from '../../components/Card'

type Tab = 'gefaehrdung' | 'vorlagen' | 'arbzg' | 'datev' | 'rechtsstand'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'gefaehrdung', label: 'Gefährdungsbeurteilung', icon: <Shield size={16} /> },
  { id: 'vorlagen',    label: 'Vorlagen & Nachweise',   icon: <FileText size={16} /> },
  { id: 'arbzg',       label: 'ArbZG-Wächter',          icon: <Clock size={16} /> },
  { id: 'datev',       label: 'DATEV-Export',            icon: <Download size={16} /> },
  { id: 'rechtsstand', label: 'Rechtsstand',             icon: <Scale size={16} /> },
]

export function AdminPremium() {
  const [tab, setTab] = useState<Tab>('gefaehrdung')

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span
            className="text-xs font-bold px-2.5 py-1 rounded-full"
            style={{ background: 'rgba(249,115,22,0.15)', color: 'var(--accent)', border: '1px solid rgba(249,115,22,0.3)' }}
          >
            PREMIUM
          </span>
          <h1 className="font-bold" style={{ fontSize: 26 }}>Compliance-Tools</h1>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>
          Rechtssichere Dokumentation, Vorlagen und Überwachungstools
        </p>
      </div>

      {/* Tabs */}
      <div
        className="flex gap-1.5 p-1.5 rounded-xl mb-7 overflow-x-auto"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap"
            style={{
              fontSize: 14,
              ...(tab === t.id
                ? { background: 'var(--accent)', color: '#fff' }
                : { color: 'var(--text-muted)' }),
            }}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'gefaehrdung' && <GefaehrdungsTab />}
      {tab === 'vorlagen' && <VorlagenTab />}
      {tab === 'arbzg' && <ComingSoon title="ArbZG-Wächter" desc="Automatische Überwachung der Arbeitszeitgrenzen nach §3–§9 ArbZG mit Echtzeit-Benachrichtigungen." />}
      {tab === 'datev' && <ComingSoon title="DATEV-Export" desc="Direkte Lohndatenübergabe an DATEV Lohn und Gehalt. Erspart manuelle Übertragungen und reduziert Fehlerquellen." />}
      {tab === 'rechtsstand' && <RechtsstandTab />}
    </div>
  )
}

function GefaehrdungsTab() {
  const BEREICHE = ['Alle', 'Küche', 'Service', 'Theke', 'Lager', 'Büro']
  const GEFAEHRDUNGEN = [
    { id: 1, bereich: 'Küche',   titel: 'Brandgefahr durch Fettdämpfe',  risiko: 'hoch',   massnahme: 'Regelmäßige Reinigung der Lüftungsanlage, Fettfilter monatlich prüfen', erledigt: true },
    { id: 2, bereich: 'Küche',   titel: 'Schnittverletzungen',            risiko: 'mittel', massnahme: 'Schnittschutzhandschuhe bereitstellen, Schulung Messerpflege', erledigt: true },
    { id: 3, bereich: 'Service', titel: 'Stolpergefahr durch Kabel',      risiko: 'mittel', massnahme: 'Kabel mit Kabelkanälen sichern, regelmäßige Begehung', erledigt: false },
    { id: 4, bereich: 'Lager',   titel: 'Überlastung beim Heben',         risiko: 'mittel', massnahme: 'Hubwagen bereitstellen, max. 20 kg Handhabung', erledigt: false },
  ]

  const risikoColor: Record<string, string> = { hoch: '#ef4444', mittel: '#F97316', niedrig: '#22c55e' }
  const erledigt = GEFAEHRDUNGEN.filter((g) => g.erledigt).length

  return (
    <div>
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Gesamt', val: GEFAEHRDUNGEN.length, color: 'var(--text)' },
          { label: 'Erledigt', val: erledigt, color: '#22c55e' },
          { label: 'Offen', val: GEFAEHRDUNGEN.length - erledigt, color: '#F97316' },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl px-5 py-4"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
            <p className="font-bold mt-1" style={{ fontSize: 26, color: s.color }}>{s.val}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-2 flex-wrap">
          {BEREICHE.map((b) => (
            <span
              key={b}
              className="text-sm px-3 py-1.5 rounded-full cursor-pointer"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            >
              {b}
            </span>
          ))}
        </div>
        <button
          className="text-sm px-4 py-2 rounded-lg font-medium cursor-pointer"
          style={{ background: 'var(--accent)', color: '#fff' }}
        >
          + Neue Gefährdung
        </button>
      </div>

      <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
        Gemäß §5 ArbSchG — Beurteilung der Arbeitsbedingungen
      </p>

      <div className="flex flex-col gap-3">
        {GEFAEHRDUNGEN.map((g) => (
          <div
            key={g.id}
            className="flex items-start gap-4 p-5 rounded-xl"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <div className="mt-0.5 shrink-0">
              {g.erledigt
                ? <CheckCircle size={20} style={{ color: '#22c55e' }} />
                : <AlertTriangle size={20} style={{ color: risikoColor[g.risiko] }} />
              }
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap mb-1.5">
                <p className="font-semibold" style={{ fontSize: 15 }}>{g.titel}</p>
                <span className="text-xs px-2.5 py-0.5 rounded-full" style={{ background: 'var(--surface2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                  {g.bereich}
                </span>
                <span
                  className="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                  style={{ color: risikoColor[g.risiko], background: `${risikoColor[g.risiko]}18`, border: `1px solid ${risikoColor[g.risiko]}33` }}
                >
                  {g.risiko}
                </span>
              </div>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Maßnahme: {g.massnahme}
              </p>
            </div>
            <span
              className="text-sm px-3 py-1 rounded-lg shrink-0 font-medium"
              style={g.erledigt
                ? { background: 'rgba(34,197,94,0.1)', color: '#22c55e' }
                : { background: 'rgba(249,115,22,0.1)', color: '#F97316' }
              }
            >
              {g.erledigt ? 'Erledigt' : 'Offen'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function VorlagenTab() {
  const VORLAGEN = [
    { name: 'Arbeitsvertrag (Vollzeit)', typ: 'Vertrag', version: 'v2024-01' },
    { name: 'Arbeitsvertrag (Teilzeit/Minijob)', typ: 'Vertrag', version: 'v2024-01' },
    { name: 'Abmahnung', typ: 'Maßnahme', version: 'v2023-09' },
    { name: 'Kündigung durch Arbeitgeber', typ: 'Kündigung', version: 'v2024-01' },
    { name: 'Urlaubsantrag (Papierform)', typ: 'Antrag', version: 'v2023-06' },
    { name: 'Überstunden-Auszahlungsvereinbarung', typ: 'Vertrag', version: 'v2024-03' },
    { name: 'Datenschutzerklärung Mitarbeiter (DSGVO)', typ: 'Compliance', version: 'v2024-05' },
    { name: 'Einwilligung Personalfoto', typ: 'DSGVO', version: 'v2023-11' },
  ]

  const typColor: Record<string, string> = {
    Vertrag: '#60a5fa',
    Maßnahme: '#F97316',
    Kündigung: '#ef4444',
    Antrag: '#22c55e',
    Compliance: '#a78bfa',
    DSGVO: '#a78bfa',
  }

  return (
    <div>
      <p className="mb-6" style={{ color: 'var(--text-muted)', fontSize: 15 }}>
        Rechtssichere Vorlagen — aktuell nach deutschem Arbeitsrecht
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {VORLAGEN.map((v) => (
          <div
            key={v.name}
            className="flex items-center justify-between p-5 rounded-xl cursor-pointer hover:opacity-80 transition-opacity"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <div className="flex items-center gap-4">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
              >
                <FileText size={18} style={{ color: 'var(--text-muted)' }} />
              </div>
              <div>
                <p className="font-medium" style={{ fontSize: 14 }}>{v.name}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{v.version}</p>
              </div>
            </div>
            <span
              className="text-xs px-2.5 py-1 rounded-full ml-3 shrink-0"
              style={{ color: typColor[v.typ] ?? '#888', background: `${typColor[v.typ] ?? '#888'}18`, border: `1px solid ${typColor[v.typ] ?? '#888'}33` }}
            >
              {v.typ}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function RechtsstandTab() {
  const GESETZE = [
    { name: 'Mindestlohn (MiLoG)', wert: '12,82 €/h', seit: '01.01.2025', status: 'aktuell' },
    { name: 'Gesetzlicher Urlaubsanspruch (BUrlG §3)', wert: '24 Werktage', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Maximale Arbeitszeit (ArbZG §3)', wert: '8h/Tag, max. 10h', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Ruhezeit zwischen Schichten (ArbZG §5)', wert: 'Mind. 11 Stunden', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Pausenregelung (ArbZG §4)', wert: '30 Min ab 6h, 45 Min ab 9h', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Lohnfortzahlung im Krankheitsfall (EFZG §3)', wert: '6 Wochen, 100%', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Sonn-/Feiertagsarbeit (ArbZG §11)', wert: 'Nur mit behördl. Ausnahme', seit: 'Dauerhaft', status: 'aktuell' },
    { name: 'Aufbewahrungspflicht Lohnunterlagen', wert: '10 Jahre', seit: 'Dauerhaft', status: 'aktuell' },
  ]

  return (
    <div>
      <p className="mb-6" style={{ color: 'var(--text-muted)', fontSize: 15 }}>
        Aktueller Rechtsstand — automatisch gepflegt (Stand: Januar 2025)
      </p>
      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        {GESETZE.map((g, idx) => (
          <div
            key={g.name}
            className="flex items-center justify-between px-6 py-4"
            style={{
              borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
              background: idx % 2 === 0 ? 'var(--surface)' : '#0f0f0f',
            }}
          >
            <div>
              <p className="font-medium" style={{ fontSize: 15 }}>{g.name}</p>
              <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>seit {g.seit}</p>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-4">
              <span className="font-semibold" style={{ fontSize: 15 }}>{g.wert}</span>
              <CheckCircle size={16} style={{ color: '#22c55e' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ComingSoon({ title, desc }: { title: string; desc: string }) {
  return (
    <Card className="flex flex-col items-center py-20 gap-5 text-center">
      <div
        className="w-20 h-20 rounded-2xl flex items-center justify-center"
        style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
      >
        <Lock size={32} style={{ color: 'var(--text-muted)' }} />
      </div>
      <div>
        <p className="font-bold" style={{ fontSize: 20 }}>{title}</p>
        <p className="mt-2 max-w-sm" style={{ color: 'var(--text-muted)', fontSize: 15 }}>{desc}</p>
      </div>
      <span
        className="text-sm font-bold px-4 py-2 rounded-full"
        style={{ background: 'rgba(249,115,22,0.15)', color: 'var(--accent)', border: '1px solid rgba(249,115,22,0.3)' }}
      >
        Demnächst verfügbar
      </span>
    </Card>
  )
}
