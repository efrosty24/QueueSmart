import type { ReactNode } from 'react'
import './PageHeader.css'

type PageHeaderProps = {
  title: string
  description?: ReactNode
  actions?: ReactNode
}

// Title block at the top of each signed-in page.
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  )
}
