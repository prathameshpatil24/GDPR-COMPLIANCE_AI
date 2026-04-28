import * as TooltipPrimitive from '@radix-ui/react-tooltip'

import { cn } from '@/lib/utils'

/**
 * @param {{ children: import('react').ReactNode, delayDuration?: number }} props
 */
export function TooltipProvider({ children, delayDuration = 200 }) {
  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration} skipDelayDuration={200}>
      {children}
    </TooltipPrimitive.Provider>
  )
}

/**
 * @param {{
 *   content: import('react').ReactNode,
 *   children: import('react').ReactNode,
 *   side?: 'top' | 'right' | 'bottom' | 'left',
 *   className?: string,
 * }} props
 */
export function SimpleTooltip({ content, children, side = 'right', className }) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn(
            'z-[100] max-w-xs rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 shadow-lg',
            'dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100',
            className
          )}
        >
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}
