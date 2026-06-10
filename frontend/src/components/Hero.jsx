const FEATURES = [
  '📝 Note-Ready Summaries',
  '⏱ Timestamp Navigation',
  '🎯 Key Takeaways',
]

function YouTubeLogo() {
  return (
    <svg
      width="46"
      height="32"
      viewBox="0 0 28 20"
      role="img"
      aria-label="YouTube"
      style={{ flexShrink: 0 }}
    >
      <path
        d="M27.4 3.12a3.52 3.52 0 0 0-2.48-2.49C22.74 0 14 0 14 0S5.26 0 3.08.63A3.52 3.52 0 0 0 .6 3.12 36.7 36.7 0 0 0 0 10a36.7 36.7 0 0 0 .6 6.88 3.52 3.52 0 0 0 2.48 2.49C5.26 20 14 20 14 20s8.74 0 10.92-.63a3.52 3.52 0 0 0 2.48-2.49A36.7 36.7 0 0 0 28 10a36.7 36.7 0 0 0-.6-6.88Z"
        fill="#FF0000"
      />
      <path d="M11.2 14.29 18.47 10 11.2 5.71v8.58Z" fill="#fff" />
    </svg>
  )
}

export default function Hero() {
  return (
    <header style={styles.hero}>
      <div className="hero-title-row" style={styles.titleRow}>
        <YouTubeLogo />
        <h1 style={styles.title}>YT Summarizer</h1>
      </div>

      <p className="hero-tagline" style={styles.tagline}>
        Turn any YouTube video into structured notes — instantly.
      </p>

      <div style={styles.chips}>
        {FEATURES.map((feature, i) => (
          <span
            key={feature}
            className="feature-chip stagger"
            style={{ animationDelay: `${0.15 + i * 0.1}s` }}
          >
            {feature}
          </span>
        ))}
      </div>
    </header>
  )
}

const styles = {
  hero: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    gap: 18,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  title: {
    fontSize: 'clamp(2rem, 6vw, 3.1rem)',
    fontWeight: 700,
    letterSpacing: '-1px',
    color: 'var(--text-primary)',
    lineHeight: 1,
  },
  tagline: {
    fontSize: 'clamp(1.05rem, 3vw, 1.35rem)',
    color: 'var(--text-secondary)',
    maxWidth: 520,
    lineHeight: 1.45,
  },
  chips: {
    display: 'flex',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
    marginTop: 2,
  },
}
