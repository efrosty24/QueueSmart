import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { TextField } from '../../components/TextField'
import { AuthLayout } from './AuthLayout'
import { useAuth } from './AuthProvider'
import { login } from './authApi'
import { useAuthForm } from './useAuthForm'
import { validateLogin } from './validation'

export function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Send people back to the page they tried to open before being asked to sign in.
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const { fieldProps, handleSubmit, submitting } = useAuthForm({
    initialValues: { email: '', password: '' },
    validate: validateLogin,
    onSubmit: async (values) => {
      setError(null)
      try {
        signIn(await login(values))
        navigate(redirectTo, { replace: true })
      } catch {
        setError('Could not sign in. Check your email and password.')
      }
    },
  })

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to join a queue or check your place in line."
      footer={
        <>
          New to QueueSmart? <Link to="/register">Create an account</Link>
        </>
      }
    >
      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        <TextField
          label="Email"
          type="email"
          autoComplete="username"
          inputMode="email"
          placeholder="name@university.edu"
          {...fieldProps('email')}
        />
        <TextField label="Password" type="password" autoComplete="current-password" {...fieldProps('password')} />
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </AuthLayout>
  )
}
