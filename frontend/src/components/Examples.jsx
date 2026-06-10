const EXAMPLES = [
  {
    label: '3Blue1Brown — Neural Networks',
    url: 'https://www.youtube.com/watch?v=aircAruvnKk',
  },
  {
    label: 'Fireship — JavaScript in 100 Seconds',
    url: 'https://www.youtube.com/watch?v=DHjqpvDnNGE',
  },
  {
    label: 'Lex Fridman — AI Podcast Clip',
    url: 'https://www.youtube.com/watch?v=cdiD-9MMpb0',
  },
]

export default function Examples({ onPick }) {
  return (
    <section style={styles.section}>
      <p style={styles.label}>Try an example →</p>
      <div style={styles.chips}>
        {EXAMPLES.map((example) => (
          <button
            key={example.url}
            type="button"
            className="example-chip"
            onClick={() => onPick(example.url)}
          >
            {example.label}
          </button>
        ))}
      </div>
    </section>
  )
}

const styles = {
  section: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    marginTop: 8,
  },
  label: {
    fontSize: '0.85rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  chips: {
    display: 'flex',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
  },
}
