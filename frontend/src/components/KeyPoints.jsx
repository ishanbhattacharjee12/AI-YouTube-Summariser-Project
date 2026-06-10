function timestampToSeconds(timestamp) {
  const parts = String(timestamp).split(':').map(Number)
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  return 0
}

export default function KeyPoints({ points, videoId }) {
  if (!points || points.length === 0) return null

  return (
    <section style={styles.section}>
      <h3 style={styles.heading}>📌 Key Points</h3>
      <ul style={styles.list}>
        {points.map((item, i) => (
          <li key={i} style={styles.card}>
            <a
              href={`https://youtube.com/watch?v=${videoId}&t=${timestampToSeconds(item.timestamp)}s`}
              target="_blank"
              rel="noreferrer"
              style={styles.timestamp}
            >
              {item.timestamp}
            </a>
            <div style={styles.body}>
              <p style={styles.point}>{item.point}</p>
              {item.detail && <p style={styles.detail}>{item.detail}</p>}
            </div>
          </li>
        ))}
      </ul>
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
  card: {
    display: 'flex',
    gap: 14,
    alignItems: 'flex-start',
    padding: '14px 16px',
    background: 'var(--bg-input)',
    borderRadius: 10,
    borderLeft: '3px solid var(--accent)',
  },
  timestamp: {
    flexShrink: 0,
    display: 'inline-flex',
    alignItems: 'center',
    height: 26,
    padding: '0 10px',
    background: 'var(--timestamp-bg)',
    color: 'var(--timestamp-text)',
    borderRadius: 6,
    fontSize: '0.82rem',
    fontWeight: 600,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    textDecoration: 'none',
  },
  body: {
    display: 'flex',
    flexDirection: 'column',
    gap: 5,
  },
  point: {
    color: 'var(--text-primary)',
    fontSize: '0.95rem',
    lineHeight: 1.55,
  },
  detail: {
    color: 'var(--text-secondary)',
    fontSize: '0.85rem',
    lineHeight: 1.5,
  },
}
