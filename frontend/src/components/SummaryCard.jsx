import { useState } from 'react'
import KeyPoints from './KeyPoints.jsx'
import Takeaways from './Takeaways.jsx'

function buildNotesText(data) {
  const s = data.summary
  const points = s.key_points
    .map((p) => `- [${p.timestamp}] ${p.point}${p.detail ? ` (${p.detail})` : ''}`)
    .join('\n')
  const takeaways = s.takeaways.map((t, i) => `${i + 1}. ${t}`).join('\n')
  const topics = s.topics.join(', ')
  return (
    `${s.title_guess}\n\n` +
    `${s.one_liner}\n\n` +
    `Difficulty: ${s.difficulty_level} | Sentiment: ${s.sentiment} | ~${s.estimated_read_time_minutes} min read\n\n` +
    `KEY POINTS\n${points}\n\n` +
    `TAKEAWAYS\n${takeaways}\n\n` +
    `TOPICS: ${topics}\n\n` +
    `Source: https://youtube.com/watch?v=${data.video_id}`
  )
}

export default function SummaryCard({ data, onReset }) {
  const [copied, setCopied] = useState(false)
  const s = data.summary

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(buildNotesText(data))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="summary-grid">
      {/* LEFT COLUMN — sticky meta panel */}
      <aside className="summary-left" style={styles.leftCard}>
        <img
          src={data.thumbnail_url}
          alt="Video thumbnail"
          style={styles.thumb}
          loading="lazy"
        />

        <h2 style={styles.title}>{s.title_guess}</h2>
        <p style={styles.oneLiner}>{s.one_liner}</p>

        <div style={styles.chips}>
          <span style={{ ...styles.chip, ...styles.chipAccent }}>{s.sentiment}</span>
          <span style={styles.chip}>{s.difficulty_level}</span>
          <span style={styles.chip}>~{s.estimated_read_time_minutes} min read</span>
        </div>

        <p style={styles.procTime}>Summarized in {data.processing_time_seconds}s</p>

        {s.topics && s.topics.length > 0 && (
          <div style={styles.topicsBlock}>
            <h3 style={styles.topicsHeading}>🏷 Topics Covered</h3>
            <div style={styles.tags}>
              {s.topics.map((topic, i) => (
                <span key={i} style={styles.tag}>{topic}</span>
              ))}
            </div>
          </div>
        )}

        <div style={styles.actions}>
          <button onClick={handleCopy} style={styles.copyBtn}>
            {copied ? '✓ Copied' : 'Copy Notes'}
          </button>
          <button onClick={onReset} style={styles.backBtn}>
            ← Summarize another video
          </button>
        </div>
      </aside>

      {/* RIGHT COLUMN — scrolling content */}
      <div className="summary-right" style={styles.rightCard}>
        <KeyPoints points={s.key_points} videoId={data.video_id} />
        <Takeaways takeaways={s.takeaways} />
      </div>
    </div>
  )
}

const styles = {
  leftCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 14,
    padding: '20px 22px',
    display: 'flex',
    flexDirection: 'column',
  },
  rightCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 14,
    padding: '8px 26px 20px',
  },
  thumb: {
    width: '100%',
    aspectRatio: '16 / 9',
    objectFit: 'cover',
    borderRadius: 10,
    border: '1px solid var(--border)',
    background: '#000',
  },
  title: {
    marginTop: 16,
    fontSize: '1.35rem',
    fontWeight: 600,
    lineHeight: 1.25,
    color: 'var(--text-primary)',
  },
  oneLiner: {
    marginTop: 8,
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
    fontSize: '0.95rem',
    lineHeight: 1.55,
  },
  chips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 14,
  },
  chip: {
    display: 'inline-flex',
    alignItems: 'center',
    height: 26,
    padding: '0 11px',
    background: 'var(--tag-bg)',
    border: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    borderRadius: 999,
    fontSize: '0.78rem',
    fontWeight: 500,
    textTransform: 'capitalize',
  },
  chipAccent: {
    background: 'rgba(88, 166, 255, 0.12)',
    border: '1px solid rgba(88, 166, 255, 0.4)',
    color: 'var(--accent)',
  },
  procTime: {
    marginTop: 12,
    color: 'var(--text-muted)',
    fontSize: '0.8rem',
  },
  topicsBlock: {
    marginTop: 20,
    paddingTop: 20,
    borderTop: '1px solid var(--border)',
  },
  topicsHeading: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: 14,
  },
  tags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    height: 28,
    padding: '0 12px',
    background: 'var(--tag-bg)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    borderRadius: 999,
    fontSize: '0.82rem',
    fontWeight: 500,
  },
  actions: {
    marginTop: 20,
    paddingTop: 20,
    borderTop: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  copyBtn: {
    height: 40,
    padding: '0 14px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    fontSize: '0.88rem',
    fontWeight: 500,
    borderRadius: 8,
  },
  backBtn: {
    height: 40,
    padding: '0 14px',
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: '0.88rem',
    fontWeight: 500,
    borderRadius: 8,
  },
}
