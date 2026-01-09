<template>
  <div class="prompts-tab">
    <section class="tp-card">
      <header class="tp-card-header">
        <h2 class="tp-card-title">AI Agent Prompt Templates</h2>
      </header>

      <div class="tp-card-body">
        <p class="text-sm text-secondary mb-4">
          Edit LLM prompts for agentic traders. Changes apply to all markets using the selected template.
        </p>

        <!-- Template Selector -->
        <v-select
          v-model="selectedTemplate"
          :items="templates"
          item-title="name"
          item-value="id"
          label="Select Template"
          class="mb-4"
          @update:modelValue="loadTemplateYaml"
        />

        <!-- Template Preview Cards -->
        <div v-if="parsedTemplate" class="template-preview mb-4">
          <div class="preview-grid">
            <div class="preview-stat">
              <span class="tp-label">Goal</span>
              <span class="stat-value" :class="parsedTemplate.goal > 0 ? 'text-success' : 'text-error'">
                {{ parsedTemplate.goal > 0 ? 'Buy' : 'Sell' }} {{ Math.abs(parsedTemplate.goal) }}
              </span>
            </div>
            <div class="preview-stat">
              <span class="tp-label">Decision Interval</span>
              <span class="stat-value">{{ parsedTemplate.decision_interval || 5 }}s</span>
            </div>
            <div class="preview-stat">
              <span class="tp-label">Buy Target</span>
              <span class="stat-value">{{ parsedTemplate.buy_target_price || '-' }}</span>
            </div>
            <div class="preview-stat">
              <span class="tp-label">Sell Target</span>
              <span class="stat-value">{{ parsedTemplate.sell_target_price || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- YAML Editor -->
        <v-textarea
          v-model="templateYaml"
          :label="`Editing: ${selectedTemplate || 'None'}`"
          rows="18"
          class="yaml-editor"
          :error="!!yamlError"
          :error-messages="yamlError"
          placeholder="name: 'Template Name'
goal: 20
decision_interval: 5.0
buy_target_price: 110
sell_target_price: 90
penalty_multiplier_buy: 1.5
penalty_multiplier_sell: 0.5
prompt: |
  You are a trading agent..."
        />
      </div>

      <footer class="tp-card-footer">
        <button class="tp-btn tp-btn-secondary" @click="loadTemplateYaml" :disabled="!serverActive || !selectedTemplate">
          Reload
        </button>
        <button class="tp-btn tp-btn-primary" @click="saveTemplate" :disabled="!serverActive || !selectedTemplate || saving">
          {{ saving ? 'Saving...' : 'Save Template' }}
        </button>
      </footer>
    </section>

    <!-- Full YAML Editor (Advanced) -->
    <section class="tp-card mt-4">
      <header 
        class="tp-card-header tp-card-header-collapsible"
        @click="showFullEditor = !showFullEditor"
      >
        <h2 class="tp-card-title">Full Templates YAML (Advanced)</h2>
        <v-icon size="20">{{ showFullEditor ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </header>

      <v-expand-transition>
        <div v-show="showFullEditor">
          <div class="tp-card-body">
            <p class="text-sm text-warning mb-3">
              Edit all templates at once. Be careful - invalid YAML will break all templates.
            </p>
            
            <v-textarea
              v-model="fullYaml"
              label="All Templates YAML"
              rows="20"
              class="yaml-editor"
              :error="!!fullYamlError"
              :error-messages="fullYamlError"
            />
          </div>

          <footer class="tp-card-footer">
            <button class="tp-btn tp-btn-secondary" @click="loadFullYaml" :disabled="!serverActive">
              Reload All
            </button>
            <button class="tp-btn tp-btn-primary" @click="saveFullYaml" :disabled="!serverActive || savingFull">
              {{ savingFull ? 'Saving...' : 'Save All Templates' }}
            </button>
          </footer>
        </div>
      </v-expand-transition>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from '@/api/axios'
import { useUIStore } from '@/store/ui'
import * as yaml from 'js-yaml'

const props = defineProps({
  serverActive: { type: Boolean, required: true },
})

const uiStore = useUIStore()

const templates = ref([])
const selectedTemplate = ref('')
const templateYaml = ref('')
const yamlError = ref('')
const saving = ref(false)

const showFullEditor = ref(false)
const fullYaml = ref('')
const fullYamlError = ref('')
const savingFull = ref(false)

const parsedTemplate = computed(() => {
  if (!templateYaml.value) return null
  try {
    return yaml.load(templateYaml.value)
  } catch {
    return null
  }
})

const loadTemplates = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/agentic_templates`)
    templates.value = response.data.templates || []
    if (templates.value.length > 0 && !selectedTemplate.value) {
      selectedTemplate.value = templates.value[0].id
      await loadTemplateYaml()
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
  }
}

const loadTemplateYaml = async () => {
  if (!selectedTemplate.value) return
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/agentic_template/${selectedTemplate.value}`)
    templateYaml.value = response.data.yaml_content || ''
    yamlError.value = ''
  } catch (error) {
    yamlError.value = 'Failed to load template'
  }
}

const saveTemplate = async () => {
  if (!selectedTemplate.value) return
  saving.value = true
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/agentic_template/${selectedTemplate.value}`, {
      yaml_content: templateYaml.value
    })
    yamlError.value = ''
    await loadTemplates()
    uiStore.showSuccess('Template saved')
  } catch (error) {
    yamlError.value = error.response?.data?.detail || 'Failed to save'
  } finally {
    saving.value = false
  }
}

const loadFullYaml = async () => {
  try {
    const response = await axios.get(`${import.meta.env.VITE_HTTP_URL}admin/agentic_prompts_yaml`)
    fullYaml.value = response.data.yaml_content || ''
    fullYamlError.value = ''
  } catch (error) {
    fullYamlError.value = 'Failed to load'
  }
}

const saveFullYaml = async () => {
  savingFull.value = true
  try {
    await axios.post(`${import.meta.env.VITE_HTTP_URL}admin/update_agentic_prompts`, {
      yaml_content: fullYaml.value
    })
    fullYamlError.value = ''
    await loadTemplates()
    await loadTemplateYaml()
    uiStore.showSuccess('All templates saved')
  } catch (error) {
    fullYamlError.value = error.response?.data?.detail || 'Failed to save'
  } finally {
    savingFull.value = false
  }
}

onMounted(() => {
  if (props.serverActive) {
    loadTemplates()
  }
})

watch(() => props.serverActive, (newVal) => {
  if (newVal) loadTemplates()
})

watch(showFullEditor, (newVal) => {
  if (newVal && props.serverActive && !fullYaml.value) {
    loadFullYaml()
  }
})
</script>

<style scoped>
.prompts-tab {
  max-width: 900px;
}

.mb-3 { margin-bottom: var(--space-3); }
.mb-4 { margin-bottom: var(--space-4); }
.mt-4 { margin-top: var(--space-4); }

/* Template Preview */
.template-preview {
  background: var(--color-bg-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.preview-stat {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-top: var(--space-1);
}

.text-success { color: var(--color-success); }
.text-error { color: var(--color-error); }
.text-warning { color: var(--color-warning); }

/* YAML Editor */
.yaml-editor :deep(textarea) {
  font-family: var(--font-mono) !important;
  font-size: var(--text-xs) !important;
  line-height: 1.5 !important;
}

@media (max-width: 600px) {
  .preview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
