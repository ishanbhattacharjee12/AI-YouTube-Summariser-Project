export default function Takeaways({ takeaways }) {
  if (!takeaways || takeaways.length === 0) return null

  return (
    <section style={styles.section}>
      <h3 style={styles.heading}>✅ Takeaways</h3>
      <ol style={styles.list}>
        {takeaways.map((item, i) => (
          <li key={i} style={styles.item}>
            <span style={styles.check} aria-hidden="true">✓</span>
            <span style={styles.text}>{item}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}

const styles = {
  section: {
    padding: '24px 0',
    borderTop: '1px solid var(--border)',
  },
  heading: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: 16,
  },
  list: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  item: {
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start',
  },
  check: {
    flexShrink: 0,
    width: 22,
    height: 22,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '50%',
    background: 'rgba(63, 185, 80, 0.15)',
    color: 'var(--success)',
    fontSize: '0.8rem',
    fontWeight: 700,
    marginTop: 1,
  },
  text: {
    color: 'var(--text-primary)',
    fontSize: '0.95rem',
    lineHeight: 1.55,
  },
}
