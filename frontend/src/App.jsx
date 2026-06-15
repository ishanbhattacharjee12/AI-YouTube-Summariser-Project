import { useState } from 'react'
import Hero from './components/Hero.jsx'
import SearchBar from './components/SearchBar.jsx'
import HowItWorks from './components/HowItWorks.jsx'
import Examples from './components/Examples.jsx'
import LoadingState from './components/LoadingState.jsx'
import SummaryCard from './components/SummaryCard.jsx'
import Footer from './components/Footer.jsx'

export default function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(submitUrl) {
    const target = (submitUrl ?? url).trim()
    if (!target) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const res = await fetch(`${apiUrl}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: target }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Something went wrong. Please try again.')
      }
      setResult(data)
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  function handleExample(exampleUrl) {
    setUrl(exampleUrl)
    handleSubmit(exampleUrl)
  }

  function handleReset() {
    setResult(null)
    setError(null)
    setUrl('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const showIntro = !loading && !result
  const wide = !!result && !loading

  return (
    <div style={styles.page}>
      <div className="hero-glow" aria-hidden="true" />

      <main style={{ ...styles.main, maxWidth: wide ? 1200 : 760 }}>
        <Hero />

        <SearchBar
          value={url}
          onChange={setUrl}
          onSubmit={handleSubmit}
          loading={loading}
        />

        {error && (
          <div className="error-box" role="alert">
            <span style={styles.errorIcon}>⚠</span> {error}
          </div>
        )}

        {loading && <LoadingState />}

        {result && !loading && (
          <div className="result-enter">
            <SummaryCard data={result} onReset={handleReset} />
          </div>
        )}

        {showIntro && (
          <>
            <HowItWorks />
            <Examples onPick={handleExample} />
          </>
        )}
      </main>

      <Footer />
    </div>
  )
}

const styles = {
  page: {
    position: 'relative',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  main: {
    position: 'relative',
    zIndex: 1,
    flex: 1,
    width: '100%',
    maxWidth: 760,
    margin: '0 auto',
    padding: '56px 20px 64px',
    display: 'flex',
    flexDirection: 'column',
    gap: 24,
  },
  errorIcon: {
    flexShrink: 0,
    marginTop: 1,
  },
}
