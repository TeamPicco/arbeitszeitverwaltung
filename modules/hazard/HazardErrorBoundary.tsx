"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type HazardErrorBoundaryProps = {
  children: ReactNode;
};

type HazardErrorBoundaryState = {
  hasError: boolean;
};

export default class HazardErrorBoundary extends Component<
  HazardErrorBoundaryProps,
  HazardErrorBoundaryState
> {
  public state: HazardErrorBoundaryState = {
    hasError: false,
  };

  public static getDerivedStateFromError(): HazardErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Isoliertes Logging: Fehler bleibt im Modul eingeschlossen.
    // eslint-disable-next-line no-console
    console.error("Fehler im Gefährdungsbeurteilungs-Modul:", error, errorInfo);
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <section style={styles.wrapper} role="alert" aria-live="polite">
          <h2 style={styles.title}>Modul vorübergehend nicht verfügbar</h2>
          <p style={styles.text}>
            Im Modul „Gefährdungsbeurteilung“ ist ein Fehler aufgetreten. Die
            übrige App läuft weiter wie gewohnt.
          </p>
          <p style={styles.textSecondary}>
            Bitte lade die Seite neu oder versuche es in wenigen Minuten erneut.
          </p>
        </section>
      );
    }

    return this.props.children;
  }
}

const styles = {
  wrapper: {
    width: "100%",
    maxWidth: 920,
    margin: "0 auto",
    padding: 20,
    borderRadius: 12,
    border: "1px solid #8f3c3c",
    backgroundColor: "#2f1818",
    color: "#ffd9d9",
  },
  title: {
    margin: "0 0 10px",
    color: "#ffd0d0",
    fontSize: "1.2rem",
  },
  text: {
    margin: "0 0 8px",
    lineHeight: 1.5,
  },
  textSecondary: {
    margin: 0,
    color: "#ffb3b3",
    lineHeight: 1.45,
    fontSize: "0.95rem",
  },
};
