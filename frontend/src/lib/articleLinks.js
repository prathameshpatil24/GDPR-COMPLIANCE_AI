/**
 * Map a citation string to an official-style URL, or null if unknown / not linkable (e.g. EDPB).
 * @param {string} reference
 * @returns {string | null}
 */
export function getArticleUrl(reference) {
  const s = String(reference || '').trim()
  if (!s) return null

  const artMatch = s.match(/Art\.?\s*(\d+)/i)
  if (artMatch) return `https://gdpr-info.eu/art-${artMatch[1]}-gdpr/`

  const articleWord = s.match(/Article\s+(\d+)/i)
  if (articleWord) return `https://gdpr-info.eu/art-${articleWord[1]}-gdpr/`

  const recitalMatch = s.match(/Recital\s*(\d+)/i)
  if (recitalMatch) return `https://gdpr-info.eu/recitals/no-${recitalMatch[1]}/`

  const bdsgMatch = s.match(/§\s*(\d+)\s*BDSG/i)
  if (bdsgMatch) return `https://www.gesetze-im-internet.de/bdsg_2018/__${bdsgMatch[1]}.html`

  return null
}
