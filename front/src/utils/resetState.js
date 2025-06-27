import { useAuthStore } from '@/store/auth'
import { useTraderStore } from '@/store/app'

export function resetApplicationState() {
  const authStore = useAuthStore()
  const traderStore = useTraderStore()

  authStore.$reset()
  traderStore.resetState() // Use the custom reset method

  // Sign out the user from Firebase
  const auth = getAuth()
  auth.signOut()
}
