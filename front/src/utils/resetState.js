import { useAuthStore } from '@/stores/auth';
import { useTradingStore } from '@/stores/trading';

export function resetApplicationState() {
  const authStore = useAuthStore();
  const tradingStore = useTradingStore();

  authStore.$reset();
  tradingStore.resetState();  // Use the custom reset method

  // Sign out the user from Firebase
  const auth = getAuth();
  auth.signOut();
}