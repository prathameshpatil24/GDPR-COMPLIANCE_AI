export const APP_NAME = 'GDPR AI'
export const APP_VERSION = '3.0.0'

export const MODES = {
  VIOLATION: 'violation',
  COMPLIANCE: 'compliance',
}

export const PLACEHOLDERS = {
  [MODES.VIOLATION]:
    'Describe a privacy scenario…\n\nExample: "A German hospital accidentally emails patient test results to the wrong patient."',
  [MODES.COMPLIANCE]:
    'Describe your system architecture…\n\nExample: "I am building a SaaS that collects email addresses from a web form and sends weekly newsletters via Mailchimp. Data stored in PostgreSQL on AWS eu-central-1."',
}

export const NAV_ITEMS = [
  { label: 'Analyze', path: '/', icon: 'Search' },
  { label: 'History', path: '/history', icon: 'Clock' },
  { label: 'Stats', path: '/stats', icon: 'BarChart3' },
  { label: 'Settings', path: '/settings', icon: 'Settings' },
]
