"use client";

import { useMemo, useState } from "react";

type Industry =
  | "gastronomie"
  | "einzelhandel"
  | "handwerk"
  | "buero"
  | "sonstiges";

type HazardStep = {
  stepNumber: 1 | 2 | 3 | 4 | 5;
  stepName: string;
};

type HazardFormPayload = {
  industry: Industry | "";
  steps: Array<{
    stepNumber: number;
    stepName: string;
    content: string;
    completed: boolean;
  }>;
};

type HazardFormProps = {
  onSave?: (payload: HazardFormPayload) => void;
};

const HAZARD_STEPS: HazardStep[] = [
  { stepNumber: 1, stepName: "Gefährdungen ermitteln" },
  { stepNumber: 2, stepName: "Gefährdungen beurteilen" },
  { stepNumber: 3, stepName: "Maßnahmen festlegen" },
  { stepNumber: 4, stepName: "Maßnahmen durchführen" },
  { stepNumber: 5, stepName: "Wirksamkeit überprüfen" },
];

const INDUSTRY_LABELS: Record<Industry, string> = {
  gastronomie: "Gastronomie",
  einzelhandel: "Einzelhandel",
  handwerk: "Handwerk",
  buero: "Büro",
  sonstiges: "Sonstiges",
};

export default function HazardForm({ onSave }: HazardFormProps) {
  const [industry, setIndustry] = useState<Industry | "">("");
  const [openStep, setOpenStep] = useState<number>(1);
  const [stepContents, setStepContents] = useState<string[]>(
    Array.from({ length: 5 }, () => ""),
  );
  const [aiLoadingStep, setAiLoadingStep] = useState<number | null>(null);

  const completedSteps = useMemo(
    () => stepContents.filter((item) => item.trim().length > 0).length,
    [stepContents],
  );

  const progressPercent = Math.round((completedSteps / HAZARD_STEPS.length) * 100);

  const updateStepContent = (stepIndex: number, value: string) => {
    setStepContents((prev) => {
      const next = [...prev];
      next[stepIndex] = value;
      return next;
    });
  };

  const generateSuggestion = (stepIndex: number, step: HazardStep) => {
    setAiLoadingStep(stepIndex);

    setTimeout(() => {
      const industryLabel =
        industry === "" ? "dem ausgewählten Betrieb" : INDUSTRY_LABELS[industry];
      const suggestion =
        `KI-Vorschlag für Schritt ${step.stepNumber} (${step.stepName}) in ${industryLabel}: ` +
        "Beschreibe typische Risiken, priorisiere sie nach Eintrittswahrscheinlichkeit " +
        "und dokumentiere klare Verantwortlichkeiten.";

      setStepContents((prev) => {
        const next = [...prev];
        next[stepIndex] = next[stepIndex].trim().length > 0 ? next[stepIndex] : suggestion;
        return next;
      });

      setAiLoadingStep(null);
    }, 450);
  };

  const buildPayload = (): HazardFormPayload => ({
    industry,
    steps: HAZARD_STEPS.map((step, index) => ({
      stepNumber: step.stepNumber,
      stepName: step.stepName,
      content: stepContents[index],
      completed: stepContents[index].trim().length > 0,
    })),
  });

  const handleSave = () => {
    const payload = buildPayload();
    if (onSave) {
      onSave(payload);
      return;
    }

    // eslint-disable-next-line no-console
    console.log("Gefährdungsbeurteilung gespeichert:", payload);
  };

  const handleExportPdf = () => {
    const payload = buildPayload();
    const exportWindow = window.open("", "_blank", "noopener,noreferrer");
    if (!exportWindow) {
      return;
    }

    const stepsHtml = payload.steps
      .map(
        (step) => `
          <h3>Schritt ${step.stepNumber}: ${step.stepName}</h3>
          <p>${step.content.trim().length > 0 ? step.content : "Nicht ausgefüllt"}</p>
        `,
      )
      .join("");

    exportWindow.document.write(`
      <!DOCTYPE html>
      <html lang="de">
      <head>
        <meta charset="utf-8" />
        <title>Gefährdungsbeurteilung</title>
        <style>
          body { font-family: Arial, sans-serif; color: #111; padding: 24px; line-height: 1.45; }
          h1 { margin-top: 0; }
          h3 { margin-bottom: 4px; margin-top: 18px; }
          p { margin-top: 0; white-space: pre-wrap; }
        </style>
      </head>
      <body>
        <h1>Gefährdungsbeurteilung (§5 ArbSchG)</h1>
        <p><strong>Branche:</strong> ${payload.industry || "Nicht gewählt"}</p>
        ${stepsHtml}
      </body>
      </html>
    `);
    exportWindow.document.close();
    exportWindow.focus();
    exportWindow.print();
  };

  return (
    <section style={styles.wrapper}>
      <header style={styles.header}>
        <h2 style={styles.title}>Gefährdungsbeurteilung erstellen</h2>
        <p style={styles.subtitle}>Pflichtschritte nach §5 ArbSchG</p>
      </header>

      <div style={styles.progressSection}>
        <div style={styles.progressLabelRow}>
          <span style={styles.progressLabel}>Fortschritt</span>
          <strong style={styles.progressValue}>
            {completedSteps}/{HAZARD_STEPS.length} Schritte
          </strong>
        </div>
        <div style={styles.progressTrack}>
          <div style={{ ...styles.progressFill, width: `${progressPercent}%` }} />
        </div>
      </div>

      <div style={styles.fieldGroup}>
        <label htmlFor="hazard-industry" style={styles.fieldLabel}>
          Schritt 1: Branche auswählen
        </label>
        <select
          id="hazard-industry"
          value={industry}
          onChange={(event) => setIndustry(event.target.value as Industry)}
          style={styles.select}
        >
          <option value="">Bitte wählen</option>
          {Object.entries(INDUSTRY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div style={styles.accordion}>
        {HAZARD_STEPS.map((step, index) => {
          const isOpen = openStep === step.stepNumber;
          return (
            <article key={step.stepNumber} style={styles.stepCard}>
              <button
                type="button"
                style={styles.stepHeaderButton}
                onClick={() =>
                  setOpenStep((current) =>
                    current === step.stepNumber ? 0 : step.stepNumber,
                  )
                }
              >
                <span style={styles.stepHeaderText}>
                  Schritt {step.stepNumber}: {step.stepName}
                </span>
                <span style={styles.stepHeaderArrow}>{isOpen ? "▾" : "▸"}</span>
              </button>

              {isOpen ? (
                <div style={styles.stepContent}>
                  <textarea
                    value={stepContents[index]}
                    onChange={(event) => updateStepContent(index, event.target.value)}
                    placeholder="Dokumentation für diesen Schritt eingeben ..."
                    style={styles.textArea}
                  />
                  <button
                    type="button"
                    style={styles.aiButton}
                    onClick={() => generateSuggestion(index, step)}
                    disabled={aiLoadingStep === index}
                  >
                    {aiLoadingStep === index
                      ? "KI-Vorschlag wird erstellt ..."
                      : "KI-Vorschlag generieren"}
                  </button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      <footer style={styles.footer}>
        <button type="button" style={styles.secondaryButton} onClick={handleExportPdf}>
          Als PDF exportieren
        </button>
        <button type="button" style={styles.primaryButton} onClick={handleSave}>
          Speichern
        </button>
      </footer>
    </section>
  );
}

const styles = {
  wrapper: {
    width: "100%",
    maxWidth: 980,
    margin: "0 auto",
    borderRadius: 16,
    border: "1px solid #355e8f",
    background:
      "linear-gradient(160deg, rgba(26,37,53,0.98) 0%, rgba(18,28,42,0.98) 100%)",
    boxShadow: "0 14px 34px rgba(10, 18, 28, 0.32)",
    padding: 22,
    color: "#e8f1fa",
    display: "grid",
    gap: 18,
  },
  header: {
    display: "grid",
    gap: 4,
  },
  title: {
    margin: 0,
    fontSize: "1.35rem",
    color: "#ffffff",
  },
  subtitle: {
    margin: 0,
    color: "#aac6e2",
    fontSize: "0.95rem",
  },
  progressSection: {
    display: "grid",
    gap: 8,
  },
  progressLabelRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  progressLabel: {
    fontSize: "0.92rem",
    color: "#c1daef",
  },
  progressValue: {
    fontSize: "0.9rem",
    color: "#e9f4ff",
  },
  progressTrack: {
    width: "100%",
    height: 10,
    borderRadius: 999,
    overflow: "hidden",
    backgroundColor: "rgba(58, 110, 168, 0.3)",
  },
  progressFill: {
    height: "100%",
    borderRadius: 999,
    background: "linear-gradient(90deg, #4e9de4 0%, #75c3ff 100%)",
    transition: "width 0.2s ease",
  },
  fieldGroup: {
    display: "grid",
    gap: 8,
  },
  fieldLabel: {
    fontSize: "0.94rem",
    color: "#dcecff",
  },
  select: {
    border: "1px solid #4c7aac",
    borderRadius: 10,
    backgroundColor: "#1a2a3c",
    color: "#f2f8ff",
    padding: "10px 12px",
    fontSize: "0.95rem",
  },
  accordion: {
    display: "grid",
    gap: 10,
  },
  stepCard: {
    border: "1px solid rgba(122, 166, 213, 0.35)",
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "rgba(29, 44, 62, 0.55)",
  },
  stepHeaderButton: {
    width: "100%",
    border: "none",
    background: "rgba(55, 92, 130, 0.26)",
    color: "#eef6ff",
    textAlign: "left" as const,
    padding: "12px 14px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    cursor: "pointer",
  },
  stepHeaderText: {
    fontWeight: 600,
    fontSize: "0.96rem",
  },
  stepHeaderArrow: {
    color: "#b8d8f7",
    fontSize: "0.9rem",
  },
  stepContent: {
    padding: 14,
    display: "grid",
    gap: 10,
  },
  textArea: {
    width: "100%",
    minHeight: 120,
    resize: "vertical" as const,
    border: "1px solid #4c7aac",
    borderRadius: 10,
    backgroundColor: "#182536",
    color: "#f2f8ff",
    padding: 12,
    fontSize: "0.94rem",
    lineHeight: 1.5,
  },
  aiButton: {
    justifySelf: "flex-start" as const,
    border: "1px solid #6bb1f7",
    borderRadius: 10,
    background: "rgba(70, 142, 214, 0.22)",
    color: "#d7ecff",
    padding: "9px 12px",
    fontWeight: 600,
    cursor: "pointer",
  },
  footer: {
    display: "flex",
    justifyContent: "flex-end",
    flexWrap: "wrap" as const,
    gap: 10,
    paddingTop: 4,
  },
  secondaryButton: {
    border: "1px solid #5e88b4",
    borderRadius: 10,
    backgroundColor: "transparent",
    color: "#d7ebff",
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 600,
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
};
