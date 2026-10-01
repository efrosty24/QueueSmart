import type { ReactNode } from 'react'
import { AppHeader } from '../../components/AppHeader'
import './auth.css'

type AuthLayoutProps = {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="auth-page">
      <AppHeader />

      <main className="auth-page__main">
        <section className="auth-card glass" aria-labelledby="auth-title">
          <div className="auth-card__heading">
            <h1 id="auth-title">{title}</h1>
            <p>{subtitle}</p>
          </div>
          {children}
          <p className="auth-card__footer">{footer}</p>
        </section>
      </main>
    </div>
  )
}
