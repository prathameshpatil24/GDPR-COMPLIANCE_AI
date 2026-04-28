/** @param {number | null | undefined} eur */
export const formatCost = (eur) => {
  if (eur == null || Number.isNaN(Number(eur))) return '€0.0000'
  return `€${Number(eur).toFixed(4)}`
}

/** @param {number | null | undefined} ms */
export const formatLatency = (ms) => {
  if (ms == null || Number.isNaN(Number(ms))) return '—'
  const n = Number(ms)
  return n > 1000 ? `${(n / 1000).toFixed(1)}s` : `${Math.round(n)}ms`
}

/** @param {string | null | undefined} iso */
export const formatDate = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

/** @param {number | null | undefined} score */
export const formatConfidence = (score) => {
  if (score == null || Number.isNaN(Number(score))) return '—'
  return `${(Number(score) * 100).toFixed(0)}%`
}

/** @param {string} text @param {number} [maxLength] */
export const truncateText = (text, maxLength = 80) => {
  if (!text) return ''
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}
