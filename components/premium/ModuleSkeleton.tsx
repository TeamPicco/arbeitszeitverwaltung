const skeletonCss = `
@keyframes premiumSkeletonPulse {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.premium-skeleton-shimmer {
  background: linear-gradient(
    90deg,
    rgba(53, 78, 106, 0.35) 0%,
    rgba(122, 166, 213, 0.45) 50%,
    rgba(53, 78, 106, 0.35) 100%
  );
  background-size: 200% 100%;
  animation: premiumSkeletonPulse 1.4s ease-in-out infinite;
}
`;

export default function ModuleSkeleton() {
  return (
    <section style={styles.wrapper} aria-label="Modul wird geladen">
      <style>{skeletonCss}</style>

      <div className="premium-skeleton-shimmer" style={styles.title} />

      <div style={styles.card}>
        <div className="premium-skeleton-shimmer" style={styles.lineLarge} />
        <div className="premium-skeleton-shimmer" style={styles.lineMedium} />
        <div className="premium-skeleton-shimmer" style={styles.lineSmall} />
      </div>

      <div style={styles.grid}>
        <div style={styles.card}>
          <div className="premium-skeleton-shimmer" style={styles.blockTitle} />
          <div className="premium-skeleton-shimmer" style={styles.lineMedium} />
          <div className="premium-skeleton-shimmer" style={styles.lineSmall} />
        </div>
        <div style={styles.card}>
          <div className="premium-skeleton-shimmer" style={styles.blockTitle} />
          <div className="premium-skeleton-shimmer" style={styles.lineMedium} />
          <div className="premium-skeleton-shimmer" style={styles.lineSmall} />
        </div>
      </div>
    </section>
  );
}

const styles = {
  wrapper: {
    width: "100%",
    maxWidth: 980,
    minHeight: 420,
    margin: "0 auto",
    padding: 24,
    borderRadius: 16,
    border: "1px solid #355e8f",
    background:
      "linear-gradient(160deg, rgba(26,37,53,0.9) 0%, rgba(18,28,42,0.92) 100%)",
    boxShadow: "0 14px 36px rgba(10, 18, 28, 0.34)",
    display: "grid",
    gap: 18,
  },
  title: {
    height: 28,
    width: "42%",
    borderRadius: 10,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: 16,
  },
  card: {
    border: "1px solid rgba(122, 166, 213, 0.28)",
    borderRadius: 12,
    padding: 16,
    display: "grid",
    gap: 10,
    backgroundColor: "rgba(30, 45, 64, 0.55)",
  },
  blockTitle: {
    height: 18,
    width: "55%",
    borderRadius: 8,
  },
  lineLarge: {
    height: 18,
    width: "100%",
    borderRadius: 8,
  },
  lineMedium: {
    height: 14,
    width: "84%",
    borderRadius: 8,
  },
  lineSmall: {
    height: 14,
    width: "62%",
    borderRadius: 8,
  },
};
