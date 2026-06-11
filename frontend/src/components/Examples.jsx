const EXAMPLES = [
  {
    label: 'Why Apple’s M Series Chips Changed Laptops',
    url: 'https://youtu.be/eFwilHG7L34',
  },
  {
    label: 'The Art Of Winning In Tech',
    url: 'https://youtu.be/4MAupwjl3pc',
  },
  {
    label: 'Why You Are Losing Control Of Your Brain',
    url: 'https://youtu.be/H86iO0mtsDI',
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
