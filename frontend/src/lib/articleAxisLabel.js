/**
 * Compact Y-axis label for legal references (full string in tooltip).
 * @param {string} full
 * @returns {string}
 */
export function shortArticleAxisLabel(full) {
  const s = String(full || '').trim()
  if (!s) return '—'

  const artLead = s.match(/^Art\.\s*(\d+[a-z]?)\b/i)
  if (artLead) return `Art. ${artLead[1]}`

  const articleLead = s.match(/^Article\s+(\d+[a-z]?)\b/i)
  if (articleLead) return `Art. ${articleLead[1]}`

  const artMid = s.match(/\bArt\.\s*(\d+[a-z]?)\b/i)
  if (artMid) return `Art. ${artMid[1]}`

  const rec = s.match(/\bRecital\s+(\d+)\b/i)
  if (rec) return `Recital ${rec[1]}`

  const edpb = s.match(/\bEDPB\s*(?:[Gg]uidelines?\s+)?(\d+\s*\/\s*\d+)/i)
  if (edpb) return `EDPB ${edpb[1].replace(/\s/g, '')}`

  const sec = s.match(/§\s*(\d+[a-z]?)/)
  if (sec) return `§${sec[1]}`

  if (s.length <= 30) return s
  return `${s.slice(0, 27)}…`
}
