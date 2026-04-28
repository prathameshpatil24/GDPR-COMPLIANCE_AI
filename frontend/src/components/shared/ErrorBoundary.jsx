import { Component } from 'react'

import { Button } from '@/components/ui/button'

/**
 * Catches render errors in the main content tree.
 */
export default class ErrorBoundary extends Component {
  /** @param {{ children: import('react').ReactNode }} props */
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="mx-auto max-w-lg rounded-xl border border-rose-500/20 bg-white p-8 text-center dark:bg-slate-900"
        >
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Something went wrong</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            The UI hit an unexpected error. You can reload to try again.
          </p>
          {this.state.error && typeof this.state.error?.message === 'string' ? (
            <pre className="mt-4 max-h-32 overflow-auto rounded-lg bg-slate-100 p-3 text-left text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              {this.state.error.message}
            </pre>
          ) : null}
          <Button type="button" className="mt-6" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
