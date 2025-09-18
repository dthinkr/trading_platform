<template>
  <div class="landing-container">
    <Toaster position="top-center" theme="light" :visibleToasts="3" />

    <!-- Modern gradient background -->
    <div class="gradient-bg"></div>

    <!-- Floating elements for visual interest -->
    <div class="floating-elements">
      <div class="floating-shape floating-shape-1"></div>
      <div class="floating-shape floating-shape-2"></div>
      <div class="floating-shape floating-shape-3"></div>
    </div>

    <v-container fluid class="fill-height pa-0 relative">
      <v-row justify="center" align="center" class="fill-height">
        <v-col cols="12" md="10" lg="8">
          <div v-motion-slide-visible-once-bottom :delay="200" class="modern-card">
            <!-- Progress indicator -->
            <div class="progress-indicator">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${((currentPageIndex + 1) / pages.length) * 100}%` }"
                ></div>
              </div>
              <span class="progress-text"> {{ currentPageIndex + 1 }} of {{ pages.length }} </span>
            </div>

            <!-- Header section with enhanced styling -->
            <div class="modern-header">
              <div v-motion-pop-visible-once :delay="400" class="icon-container">
                <component :is="getCurrentIcon()" :size="40" class="page-icon" />
              </div>
              <h1 v-motion-slide-visible-once-right :delay="600" class="page-title">
                {{ currentPageTitle }}
              </h1>
            </div>

            <!-- Content area with enhanced spacing -->
            <div v-motion-fade-visible-once :delay="800" class="content-area">
              <router-view
                :traderAttributes="traderAttributes"
                :iconColor="deepBlueColor"
                @update:canProgress="handleProgress"
              />
            </div>

            <!-- Enhanced navigation -->
            <div
              v-if="currentRouteName !== 'consent'"
              v-motion-slide-visible-once-bottom
              :delay="1000"
              class="navigation-area"
            >
              <button
                @click="prevPage"
                :disabled="isFirstPage"
                class="nav-btn nav-btn-secondary"
                :class="{ disabled: isFirstPage }"
              >
                <ChevronLeft :size="20" />
                Previous
              </button>

              <button
                v-if="!isLastPage"
                @click="nextPage"
                :disabled="shouldDisableNext"
                class="nav-btn nav-btn-primary"
                :class="{ disabled: shouldDisableNext }"
              >
                Next
                <ChevronRight :size="20" />
              </button>
            </div>
          </div>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTraderStore } from '@/store/app'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import {
  ClipboardCheck,
  Handshake,
  Monitor,
  Settings,
  DollarSign,
  Users,
  HelpCircle,
  GraduationCap,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const traderStore = useTraderStore()
const { traderAttributes } = storeToRefs(traderStore)
const { initializeTrader } = traderStore

const traderUuid = ref(route.params.traderUuid)
const marketId = ref(route.params.marketId)

const pages = [
  { name: 'consent', title: 'Research Participant Consent Form', icon: 'ClipboardCheck' },
  { name: 'welcome', title: 'Welcome', icon: 'Handshake' },
  { name: 'platform', title: 'Trading Platform', icon: 'Monitor' },
  { name: 'setup', title: 'Setup', icon: 'Settings' },
  { name: 'earnings', title: 'Your Earnings', icon: 'DollarSign' },
  { name: 'participants', title: 'Other Participants', icon: 'Users' },
  { name: 'questions', title: 'Control Questions', icon: 'HelpCircle' },
  { name: 'practice', title: 'Practice', icon: 'GraduationCap' },
]

// Icon mapping
const iconComponents = {
  ClipboardCheck,
  Handshake,
  Monitor,
  Settings,
  DollarSign,
  Users,
  HelpCircle,
  GraduationCap,
}

const getCurrentIcon = () => {
  const iconName = pages[currentPageIndex.value]?.icon
  return iconComponents[iconName] || ClipboardCheck
}

const currentPageIndex = computed(() => {
  return pages.findIndex((page) => page.name === route.name)
})

const currentPageTitle = computed(() => {
  return pages[currentPageIndex.value]?.title || ''
})

const isFirstPage = computed(() => currentPageIndex.value === 0)
const isLastPage = computed(() => currentPageIndex.value === pages.length - 1)

const nextPage = () => {
  if (!isLastPage.value) {
    const nextPageName = pages[currentPageIndex.value + 1].name
    router.push({
      name: nextPageName,
      params: { marketId: marketId.value, traderUuid: traderUuid.value },
    })
  }
}

const prevPage = () => {
  if (!isFirstPage.value) {
    const prevPageName = pages[currentPageIndex.value - 1].name
    router.push({
      name: prevPageName,
      params: { marketId: marketId.value, traderUuid: traderUuid.value },
    })
  }
}

const canProgressFromQuestions = ref(false)
const consentGiven = ref(false)
const currentRouteName = computed(() => route.name)

const handleProgress = (value) => {
  if (currentRouteName.value === 'consent') {
    consentGiven.value = value
  } else if (currentRouteName.value === 'questions') {
    canProgressFromQuestions.value = value
  }
}

const shouldDisableNext = computed(() => {
  if (currentRouteName.value === 'consent') {
    return !consentGiven.value
  }
  return currentRouteName.value === 'questions' && !canProgressFromQuestions.value
})

onMounted(async () => {
  if (traderUuid.value && marketId.value) {
    try {
      await initializeTrader(traderUuid.value)
      await traderStore.initializeTradingSystemWithPersistentSettings()
      await traderStore.getTraderAttributes(traderUuid.value)

      if (!route.name || route.name === 'onboarding') {
        const targetRoute = authStore.isPersisted ? 'practice' : 'consent'
        router.push({
          name: targetRoute,
          params: { marketId: marketId.value, traderUuid: traderUuid.value },
        })
      }
    } catch (error) {
      console.error('Error initializing trader:', error)
    }
  } else {
    console.error('Trader UUID or Market ID not provided')
  }
})

watch(currentRouteName, (newRoute, oldRoute) => {
  if (oldRoute === 'questions') {
    canProgressFromQuestions.value = false
  }

  if (newRoute === 'practice' && authStore.user?.isProlific) {
    const prolificUserId = authStore.user.uid
    localStorage.setItem(`prolific_onboarded_${prolificUserId}`, 'true')
    // Marked Prolific user as having completed onboarding
    authStore.prolificUserHasCompletedOnboarding = true
  }
})

const lightBlueColor = ref('light-blue')
const deepBlueColor = ref('deep-blue')
</script>

<style scoped>
.landing-container {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

.gradient-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  opacity: 0.03;
  z-index: -2;
}

.floating-elements {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: -1;
  pointer-events: none;
}

.floating-shape {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(45deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
  animation: float 20s infinite ease-in-out;
}

.floating-shape-1 {
  width: 300px;
  height: 300px;
  top: 10%;
  left: -150px;
  animation-delay: 0s;
}

.floating-shape-2 {
  width: 200px;
  height: 200px;
  top: 60%;
  right: -100px;
  animation-delay: -7s;
}

.floating-shape-3 {
  width: 150px;
  height: 150px;
  bottom: 20%;
  left: 20%;
  animation-delay: -14s;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  33% {
    transform: translateY(-30px) rotate(120deg);
  }
  66% {
    transform: translateY(30px) rotate(240deg);
  }
}

.modern-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
  padding: 2rem;
  position: relative;
  overflow: hidden;
}

.modern-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
  border-radius: 24px 24px 0 0;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-text {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  min-width: fit-content;
}

.modern-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(102, 126, 234, 0.1);
}

.icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 20px;
  box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
}

.page-icon {
  color: white;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  background: linear-gradient(135deg, #1e293b, #475569);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
  margin: 0;
}

.content-area {
  margin-bottom: 2.5rem;
  min-height: 300px;
}

.navigation-area {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(102, 126, 234, 0.1);
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.nav-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.6s;
}

.nav-btn:hover::before {
  left: 100%;
}

.nav-btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.nav-btn-primary:hover:not(.disabled) {
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
  transform: translateY(-2px);
}

.nav-btn-secondary {
  background: rgba(102, 126, 234, 0.1);
  color: #475569;
  border: 1px solid rgba(102, 126, 234, 0.2);
}

.nav-btn-secondary:hover:not(.disabled) {
  background: rgba(102, 126, 234, 0.15);
  transform: translateY(-1px);
}

.nav-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.relative {
  position: relative;
}

/* Responsive design */
@media (max-width: 768px) {
  .modern-card {
    margin: 1rem;
    padding: 1.5rem;
    border-radius: 16px;
  }

  .modern-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .navigation-area {
    flex-direction: column;
    gap: 1rem;
  }

  .nav-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
