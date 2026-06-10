const STEPS = [
  {
    n: '01',
    icon: '🔗',
    title: 'Paste URL',
    desc: 'Drop any YouTube link into the box above.',
  },
  {
    n: '02',
    icon: '⚡',
    title: 'AI Analysis',
    desc: 'GPT-4o reads and understands the full video.',
  },
  {
    n: '03',
    icon: '📋',
    title: 'Get Notes',
    desc: 'Structured summary with timestamps and takeaways.',
  },
]

export default function HowItWorks() {
  return (
    <section style={styles.section}>
      <h2 style={styles.heading}>How it works</h2>
      <div className="hiw-grid" style={styles.grid}>
        {STEPS.map((step, i) => (
          <div
            key={step.n}
            className="step-card stagger"
            style={{ animationDelay: `${0.1 + i * 0.1}s` }}
          >
            <span style={styles.stepNum}>STEP {step.n}</span>
            <span style={styles.icon}>{step.icon}</span>
            <h3 style={styles.title}>{step.title}</h3>
            <p style={styles.desc}>{step.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

const styles = {
  section: {
    marginTop: 14,
  },
  heading: {
    fontSize: '0.82rem',
    fontWeight: 600,
    letterSpacing: '1.5px',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    textAlign: 'center',
    marginBottom: 18,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 14,
  },
  stepNum: {
    fontSize: '0.7rem',
    fontWeight: 700,
    letterSpacing: '1px',
    color: 'var(--accent)',
  },
  icon: {
    fontSize: '1.7rem',
    lineHeight: 1,
  },
  title: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  desc: {
    fontSize: '0.85rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
  },
}
