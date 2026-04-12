type UpgradePromptProps = {
  featureName: string;
  price: string;
  benefits: string[];
  onUpgradeClick: () => void;
};

export default function UpgradePrompt({
  featureName,
  price,
  benefits,
  onUpgradeClick,
}: UpgradePromptProps) {
  const visibleBenefits = benefits.slice(0, 3);

  return (
    <section style={styles.wrapper} aria-label="Premium-Modul Upgrade-Hinweis">
      <div style={styles.badge}>Premium-Modul</div>
      <h2 style={styles.title}>{featureName}</h2>
      <p style={styles.subtitle}>
        Dieses Modul ist in deinem aktuellen Paket nicht enthalten.
      </p>

      <div style={styles.priceBox}>
        <span style={styles.priceLabel}>Monatlicher Preis</span>
        <strong style={styles.priceValue}>{price}</strong>
      </div>

      <div style={styles.benefitSection}>
        <h3 style={styles.benefitTitle}>Deine Vorteile</h3>
        <ul style={styles.benefitList}>
          {visibleBenefits.map((benefit) => (
            <li key={benefit} style={styles.benefitItem}>
              <span style={styles.checkmark}>✓</span>
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
      </div>

      <button type="button" style={styles.button} onClick={onUpgradeClick}>
        Jetzt freischalten
      </button>
    </section>
  );
}

const styles = {
  wrapper: {
    width: "100%",
    maxWidth: 760,
    margin: "0 auto",
    padding: "28px",
    borderRadius: 16,
    border: "1px solid #355e8f",
    background:
      "linear-gradient(160deg, rgba(26,37,53,0.98) 0%, rgba(18,28,42,0.98) 100%)",
    boxShadow: "0 16px 38px rgba(10, 18, 28, 0.35)",
    color: "#e8f1fa",
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    padding: "6px 10px",
    borderRadius: 999,
    backgroundColor: "#2b4f75",
    color: "#c9e2ff",
  },
  title: {
    margin: "14px 0 6px",
    fontSize: "1.55rem",
    lineHeight: 1.25,
    color: "#ffffff",
  },
  subtitle: {
    margin: 0,
    color: "#aac6e2",
    fontSize: "0.98rem",
  },
  priceBox: {
    marginTop: 18,
    padding: "14px 16px",
    borderRadius: 12,
    backgroundColor: "rgba(58, 110, 168, 0.18)",
    border: "1px solid rgba(122, 166, 213, 0.45)",
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 12,
  },
  priceLabel: {
    fontSize: "0.9rem",
    color: "#c1daef",
  },
  priceValue: {
    fontSize: "1.2rem",
    color: "#ffffff",
  },
  benefitSection: {
    marginTop: 20,
  },
  benefitTitle: {
    margin: "0 0 10px",
    fontSize: "1rem",
    color: "#dcecff",
  },
  benefitList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "grid",
    gap: 10,
  },
  benefitItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    color: "#d5e7f8",
    fontSize: "0.95rem",
    lineHeight: 1.45,
  },
  checkmark: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 20,
    height: 20,
    borderRadius: "50%",
    fontSize: 13,
    fontWeight: 700,
    color: "#0f2a44",
    backgroundColor: "#7dc0ff",
    flexShrink: 0,
    marginTop: 1,
  },
  button: {
    marginTop: 24,
    width: "100%",
    border: "1px solid #6bb1f7",
    borderRadius: 12,
    padding: "12px 16px",
    background:
      "linear-gradient(180deg, rgba(93,169,245,1) 0%, rgba(58,134,209,1) 100%)",
    color: "#0f263d",
    fontWeight: 700,
    fontSize: "0.98rem",
    cursor: "pointer",
  },
};
