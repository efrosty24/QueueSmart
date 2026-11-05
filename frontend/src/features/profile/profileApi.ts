import { apiRequest } from '../../lib/api'

export type UserProfile = {
  user_id: string
  email: string
  full_name: string
  contact_info: string | null
  preferences: string | null
}

export type ProfileValues = {
  full_name: string
  contact_info: string
  preferences: string
}

export function fetchProfile(token: string | null): Promise<UserProfile> {
  return apiRequest<UserProfile>('/auth/profile', { token })
}

export function updateProfile(values: ProfileValues, token: string | null): Promise<UserProfile> {
  return apiRequest<UserProfile>('/auth/profile', { method: 'PUT', body: values, token })
}
