import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { TextField } from '../../components/TextField'
import { useForm } from '../../hooks/useForm'
import { errorMessage } from '../../lib/api'
import { AuthLayout } from './AuthLayout'
import { useAuth } from './AuthProvider'
import { register } from './authApi'
import { PASSWORD_MIN_LENGTH, validateRegister } from './validation'

export function RegisterPage() {
  const [error, setError] = useState<string | null>(null)
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const { fieldProps, handleSubmit, submitting } = useForm({
    initialValues: { email: '', password: '', confirmPassword: '' },
    validate: validateRegister,
    onSubmit: async ({ email, password }) => {
      setError(null)
      try {
        // New accounts are signed in right away. The server picks the role.
        const session = await register({ email, password })
        signIn(session)
        navigate(session.user.role === 'admin' ? '/admin' : '/dashboard', { replace: true })
      } catch (err) {
        setError(errorMessage(err, 'Could not create your account. Please try again.'))
      }
    },
  })

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Use your campus email. It will be your username."
      footer={
        <>
          Already have an account? <Link to="/login">Sign in</Link>
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
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          hint={`At least ${PASSWORD_MIN_LENGTH} characters, with an uppercase letter and a special character (like ! or #).`}
          {...fieldProps('password')}
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          {...fieldProps('confirmPassword')}
        />
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}
