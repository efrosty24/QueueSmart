import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { PageHeader } from '../../components/PageHeader'
import { TextArea } from '../../components/TextArea'
import { TextField } from '../../components/TextField'
import { useForm } from '../../hooks/useForm'
import { errorMessage } from '../../lib/api'
import { useAuth } from '../auth/AuthProvider'
import { validateFullName } from '../auth/validation'
import { fetchProfile, updateProfile, type ProfileValues, type UserProfile } from './profileApi'
import './profile.css'

export function ProfilePage() {
  const { user, token } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetchProfile(token)
      .then((saved) => {
        if (!cancelled) setProfile(saved)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err, 'Could not load your profile.'))
      })
    return () => { cancelled = true }
  }, [token, attempt])

  return (
    <div className="profile-page">
      <PageHeader
        title="Your profile"
        description="Keep your personal details and preferences up to date."
        actions={user?.role === 'admin' ? <Link to="/admin" className="btn btn-ghost">Admin dashboard</Link> : undefined}
      />
      {error && (
        <div className="alert alert-error" role="alert">
          <p>{error}</p>
          <button type="button" className="btn btn-ghost" onClick={() => { setError(null); setAttempt((value) => value + 1) }}>
            Try again
          </button>
        </div>
      )}
      {!profile && !error && <p role="status">Loading your profile...</p>}
      {profile && <ProfileForm key={profile.user_id} profile={profile} />}
    </div>
  )
}

function validateProfile(values: ProfileValues) {
  return {
    full_name: validateFullName(values.full_name),
    contact_info: values.contact_info.trim().length > 100 ? 'Use at most 100 characters.' : undefined,
    preferences: values.preferences.trim().length > 1000 ? 'Use at most 1,000 characters.' : undefined,
  }
}

function ProfileForm({ profile }: { profile: UserProfile }) {
  const { token } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const { fieldProps, handleSubmit, submitting } = useForm({
    initialValues: {
      full_name: profile.full_name,
      contact_info: profile.contact_info ?? '',
      preferences: profile.preferences ?? '',
    },
    validate: validateProfile,
    onSubmit: async (values) => {
      setError(null)
      setSaved(false)
      try {
        await updateProfile(values, token)
        setSaved(true)
      } catch (err) {
        setError(errorMessage(err, 'Could not save your profile. Please try again.'))
      }
    },
  })

  return (
    <form className="profile-form glass" onSubmit={handleSubmit} onChange={() => setSaved(false)} noValidate>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {saved && <div className="alert alert-success" role="status">Your profile has been saved.</div>}
      <TextField label="Email" type="email" value={profile.email} readOnly hint="Your email is your account username." />
      <TextField label="Full name" autoComplete="name" maxLength={100} required disabled={submitting} {...fieldProps('full_name')} />
      <TextField
        label="Contact information (optional)"
        hint="A phone number or another way to contact you."
        maxLength={100}
        disabled={submitting}
        {...fieldProps('contact_info')}
      />
      <TextArea
        label="Preferences (optional)"
        hint="For example, how you prefer to be contacted."
        rows={4}
        maxLength={1000}
        disabled={submitting}
        {...fieldProps('preferences')}
      />
      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? 'Saving...' : 'Save profile'}
      </button>
    </form>
  )
}
