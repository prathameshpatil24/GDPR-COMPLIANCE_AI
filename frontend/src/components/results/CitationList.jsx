const URL_SPLIT = /(https?:\/\/[^\s]+)/g

/**
 * Linkify URLs inside citation strings.
 * @param {string} text
 */
function linkify(text) {
  if (!text) return null
  const parts = text.split(URL_SPLIT)
  return parts.map((part, i) =>
    part.startsWith('http://') || part.startsWith('https://') ? (
      <a
        key={`${i}-${part.slice(0, 12)}`}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        className="text-indigo-600 underline decoration-indigo-500/40 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
      >
        {part}
      </a>
    ) : (
      <span key={`t-${i}`}>{part}</span>
    )
  )
}

/**
 * @param {{ items: string[] }} props
 */
export default function CitationList({ items }) {
  if (!items?.length) return null
  return (
    <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
      {items.map((c, i) => (
        <li key={`${i}-${c.slice(0, 40)}`} className="leading-relaxed">
          {linkify(c)}
        </li>
      ))}
    </ul>
  )
}
