"use client";

import { useEffect, useMemo, useState } from "react";

import UpgradePrompt from "../../components/premium/UpgradePrompt";
import { FEATURES, isFeatureEnabled } from "../../lib/features/featureFlags";
import HazardErrorBoundary from "./HazardErrorBoundary";
import HazardForm from "./HazardForm";

type HazardAssessment = {
  id: number | string;
  title: string;
  status: "entwurf" | "aktiv" | "ueberfaellig" | string;
  industry?: string | null;
  last_reviewed_at?: string | null;
  next_review_due?: string | null;
};

type BadgeVariant = "green" | "yellow" | "red";

function getDueBadge(assessment: HazardAssessment): { label: string; variant: BadgeVariant } {
  if (assessment.status === "ueberfaellig") {
    return { label: "Überfällig ⚠️", variant: "red" };
  }

  if (assessment.next_review_due) {
    const dueDate = new Date(assessment.next_review_due);
    const today = new Date();
    const msPerDay = 24 * 60 * 60 * 1000;
    const daysUntilDue = Math.ceil(
      (dueDate.setHours(0, 0, 0, 0) - today.setHours(0, 0, 0, 0)) / msPerDay,
    );

    if (daysUntilDue < 0) {
      return { label: "Überfällig ⚠️", variant: "red" };
    }

    if (daysUntilDue <= 30) {
      return { label: "Bald fällig", variant: "yellow" };
    }
  }

  return { label: "Aktuell ✓", variant: "green" };
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return new Intl.DateTimeFormat("de-DE").format(date);
}

function HazardModuleContent() {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [assessments, setAssessments] = useState<HazardAssessment[]>([]);

  const featureEnabled = useMemo(
    () => isFeatureEnabled(FEATURES.HAZARD_ASSESSMENT),
    [],
  );

  useEffect(() => {
    let mounted = true;

    const loadAssessments = async () => {
      if (!featureEnabled) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setLoadError(null);

      try {
        const response = await fetch("/api/modules/hazard/assessments", {
          credentials: "include",
        });

        if (!response.ok) {
          if (response.status === 404) {
            if (mounted) {
              setAssessments([]);
            }
            return;
          }
          throw new Error("Gefährdungsbeurteilungen konnten nicht geladen werden.");
        }

        const payload = (await response.json()) as
          | HazardAssessment[]
          | { data?: HazardAssessment[] };
        const parsed = Array.isArray(payload) ? payload : payload.data ?? [];

        if (mounted) {
          setAssessments(parsed);
        }
      } catch (error) {
        if (mounted) {
          setLoadError(error instanceof Error ? error : new Error("Unbekannter Fehler"));
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    void loadAssessments();

    return () => {
      mounted = false;
    };
  }, [featureEnabled]);

  if (!featureEnabled) {
    return (
      <UpgradePrompt
        featureName="Gefährdungsbeurteilung mit KI-Unterstützung"
        price="39€/Monat"
        benefits={[
          "Rechtssichere Struktur nach §5 ArbSchG",
          "KI-gestützte Formulierung von Maßnahmen",
          "Automatische Fälligkeitsüberwachung",
        ]}
        onUpgradeClick={() => {
          if (typeof window !== "undefined") {
            window.location.href = "/billing";
          }
        }}
      />
    );
  }

  if (loadError) {
    throw loadError;
  }

  return (
    <section style={styles.wrapper}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Gefährdungsbeurteilungen</h1>
          <p style={styles.subtitle}>
            Übersicht aller Beurteilungen inkl. Fälligkeiten und Status.
          </p>
        </div>
        <button
          type="button"
          style={styles.primaryButton}
          onClick={() => setShowForm((current) => !current)}
        >
          Neue Beurteilung erstellen
        </button>
      </header>

      {showForm ? <HazardForm /> : null}

      <section style={styles.listSection}>
        {isLoading ? (
          <div style={styles.emptyState}>Gefährdungsbeurteilungen werden geladen ...</div>
        ) : assessments.length === 0 ? (
          <div style={styles.emptyState}>
            Noch keine Gefährdungsbeurteilungen vorhanden.
          </div>
        ) : (
          <ul style={styles.list}>
            {assessments.map((assessment) => {
              const badge = getDueBadge(assessment);
              return (
                <li key={assessment.id} style={styles.item}>
                  <div style={styles.itemMain}>
                    <h3 style={styles.itemTitle}>{assessment.title}</h3>
                    <p style={styles.itemMeta}>
                      Branche: {assessment.industry || "—"} · Letzte Prüfung:{" "}
                      {formatDate(assessment.last_reviewed_at)} · Nächste Prüfung:{" "}
                      {formatDate(assessment.next_review_due)}
                    </p>
                  </div>
                  <span
                    style={{
                      ...styles.badge,
                      ...(badge.variant === "green"
                        ? styles.badgeGreen
                        : badge.variant === "yellow"
                          ? styles.badgeYellow
                          : styles.badgeRed),
                    }}
                  >
                    {badge.label}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </section>
  );
}

export default function HazardModule() {
  return (
    <HazardErrorBoundary>
      <HazardModuleContent />
    </HazardErrorBoundary>
  );
}

const styles = {
  wrapper: {
    width: "100%",
    maxWidth: 1024,
    margin: "0 auto",
    padding: 24,
    borderRadius: 16,
    border: "1px solid #355e8f",
    background:
      "linear-gradient(160deg, rgba(26,37,53,0.98) 0%, rgba(18,28,42,0.98) 100%)",
    boxShadow: "0 16px 38px rgba(10, 18, 28, 0.35)",
    color: "#e8f1fa",
    display: "grid",
    gap: 18,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 14,
    flexWrap: "wrap" as const,
  },
  title: {
    margin: 0,
    color: "#ffffff",
    fontSize: "1.45rem",
  },
  subtitle: {
    margin: "6px 0 0",
    color: "#aac6e2",
    fontSize: "0.95rem",
  },
  primaryButton: {
    border: "1px solid #6bb1f7",
    borderRadius: 10,
    background: "linear-gradient(180deg, #5da9f5 0%, #3a86d1 100%)",
    color: "#0f263d",
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 700,
  },
  listSection: {
    borderTop: "1px solid rgba(122, 166, 213, 0.22)",
    paddingTop: 16,
  },
  emptyState: {
    border: "1px dashed rgba(122, 166, 213, 0.45)",
    borderRadius: 10,
    padding: 18,
    color: "#c8ddf2",
    textAlign: "center" as const,
  },
  list: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "grid",
    gap: 10,
  },
  item: {
    border: "1px solid rgba(122, 166, 213, 0.35)",
    borderRadius: 12,
    padding: "12px 14px",
    backgroundColor: "rgba(30, 45, 64, 0.55)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  itemMain: {
    display: "grid",
    gap: 4,
  },
  itemTitle: {
    margin: 0,
    fontSize: "1rem",
    color: "#f2f8ff",
  },
  itemMeta: {
    margin: 0,
    color: "#bfd9f3",
    fontSize: "0.9rem",
  },
  badge: {
    borderRadius: 999,
    padding: "6px 10px",
    fontSize: "0.82rem",
    fontWeight: 700,
    whiteSpace: "nowrap" as const,
    border: "1px solid transparent",
  },
  badgeGreen: {
    color: "#c8f7dd",
    backgroundColor: "rgba(37, 104, 74, 0.45)",
    borderColor: "rgba(71, 186, 133, 0.5)",
  },
  badgeYellow: {
    color: "#fff1be",
    backgroundColor: "rgba(135, 108, 28, 0.45)",
    borderColor: "rgba(240, 200, 87, 0.55)",
  },
  badgeRed: {
    color: "#ffd3d3",
    backgroundColor: "rgba(132, 43, 43, 0.5)",
    borderColor: "rgba(224, 102, 102, 0.55)",
  },
};
