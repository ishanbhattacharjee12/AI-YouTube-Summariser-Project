import { useState } from 'react'

function isLikelyYouTubeUrl(value) {
  const trimmed = value.trim()
  return trimmed.includes('youtube.com') || trimmed.includes('youtu.be')
}

export default function SearchBar({ value, onChange, onSubmit, loading }) {
  const [localError, setLocalError] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const trimmed = value.trim()

    if (!trimmed) {
      setLocalError('Please paste a YouTube URL first.')
      return
    }
    if (!isLikelyYouTubeUrl(trimmed)) {
      setLocalError('That doesn’t look like a YouTube link. It should contain youtube.com or youtu.be.')
      return
    }

    setLocalError('')
    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form} className="stagger" >
      <div style={styles.row}>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste a YouTube URL..."
          aria-label="YouTube URL"
          autoComplete="off"
          spellCheck="false"
          disabled={loading}
          className="search-input"
        />
        <button type="submit" disabled={loading} className="search-button">
          {loading ? (
            <span style={styles.btnContent}>
              <span style={styles.spinner} aria-hidden="true" />
              Summarizing
            </span>
          ) : (
            'Summarize'
          )}
        </button>
      </div>

      {localError ? (
        <p style={styles.error}>{localError}</p>
      ) : (
        <p style={styles.hint}>Try: any educational video, podcast, lecture, or tutorial</p>
      )}
    </form>
  )
}

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  row: {
    display: 'flex',
    gap: 12,
  },
  btnContent: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 9,
  },
  spinner: {
    width: 15,
    height: 15,
    border: '2px solid rgba(13, 17, 23, 0.35)',
    borderTopColor: '#0d1117',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 700ms linear infinite',
  },
  error: {
    color: 'var(--error-text)',
    fontSize: '0.85rem',
    paddingLeft: 4,
    textAlign: 'center',
  },
  hint: {
    color: 'var(--text-muted)',
    fontSize: '0.85rem',
    textAlign: 'center',
  },
}
