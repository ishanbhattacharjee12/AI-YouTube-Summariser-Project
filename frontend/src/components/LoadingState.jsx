import { useEffect, useState } from 'react'

const MESSAGES = [
  'Fetching transcript...',
  'Reading through the video...',
  'Extracting key insights...',
  'Writing your notes...',
  'Almost done...',
]

export default function LoadingState() {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1 < MESSAGES.length ? prev + 1 : prev))
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div style={styles.card} role="status" aria-live="polite">
      <div style={styles.pulseDot} />
      <p style={styles.message}>{MESSAGES[index]}</p>
      <div style={styles.track}>
        <div style={styles.bar} />
      </div>
    </div>
  )
}

const styles = {
  card: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '38px 28px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 18,
    textAlign: 'center',
  },
  pulseDot: {
    width: 44,
    height: 44,
    borderRadius: '50%',
    background: 'var(--accent)',
    animation: 'pulse 1.4s ease-in-out infinite',
  },
  message: {
    color: 'var(--text-primary)',
    fontSize: '1.05rem',
    fontWeight: 500,
    minHeight: 24,
  },
  track: {
    width: '100%',
    maxWidth: 320,
    height: 4,
    background: 'var(--bg-input)',
    borderRadius: 999,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    background: 'var(--accent)',
    borderRadius: 999,
    animation: 'progressBar 9s ease-out forwards',
  },
}
