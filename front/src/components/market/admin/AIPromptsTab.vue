<template>
  <div class="prompts-tab">
    <v-card elevation="1">
      <v-card-title class="compact-title">
        <v-icon left color="deep-purple" size="18">mdi-robot-outline</v-icon>
        AI Agent Prompt Templates
      </v-card-title>

      <v-card-text>
        <v-alert type="info" density="compact" class="mb-4">
          Edit LLM prompts for agentic traders. Changes apply to all markets using the selected template.
        </v-alert>

        <!-- Template Selector -->
        <v-select
          v-model="selectedTemplate"
          :items="templates"
          item-title="name"
          item-value="id"
          label="Select Template"
          variant="outlined"
          density="compact"
          class="mb-4"
          @update:modelValue="loadTemplateYaml"
        >
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <v-icon :color="getTemplateColor(item.raw.id)" size="18">
                  {{ getTemplateIcon(item.raw.id) }}
                </v-icon>
              </template>
            </v-list-item>
          </template>
        </v-select>

        <!-- Template Preview Cards -->
        <div v-if="parsedTemplate" class="template-preview mb-4">
          <v-row dense>
            <v-col cols="6" md="3">
              <div class="preview-stat">
                <div class="stat-label">Goal</div>
                <div class="stat-value" :class="parsedTemplate.goal > 0 ? 'text-success' : 'text-error'">
                  {{ parsedTemplate.goal > 0 ? 'Buy' : 'Sell' }} {{ Math.abs(parsedTemplate.goal) }}
                </div>
              </div>
            </v-col>
            <v-col cols="6" md="3">
              <div class="preview-stat">
                <div class="stat-label">Decision Interval</div>
                <div class="stat-value">{{ parsedTemplate.decision_interval || 5 }}s</div>
              </div>
            </v-col>
            <v-col cols="6" md="3">
              <div class="preview-stat">
                <div class="stat-label">Buy Target</div>
                <div class="stat-value">{{ parsedTemplate.buy_target_price || '-' }}</div>
              </div>
            </v-col>
            <v-col cols="6" md="3">
              <div class="preview-stat">
                <div class="stat-label">Sell Target</div>
                <div class="stat-value">{{ parsedTemplate.sell_target_price || '-' }}</div>
              </div>
            </v-col>
          </v-row>
        </div>

        <!-- YAML Editor -->
        <v-textarea
          v-model="templateYaml"
          :label="`Editing: ${selectedTemplate || 'None'}`"
          rows="18"
          variant="outlined"
          density="compact"
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
        ></v-textarea>
      </v-card-text>

      <v-card-actions class="pa-3">
        <v-btn color="secondary" @click="loadTemplateYaml" :disabled="!serverActive || !selectedTemplate" size="small" variant="outlined">
          <v-icon start size="16">mdi-refresh</v-icon>
          Reload
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn color="deep-purple" @click="saveTemplate" :disabled="!serverActive || !selectedTemplate" :loading="saving" size="small" variant="elevated">
          <v-icon start size="16">mdi-content-save</v-icon>
          Save Template
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Full YAML Editor (Advanced) -->
    <v-card elevation="1" class="mt-4">
      <v-card-title class="compact-title" @click="showFullEditor = !showFullEditor" style="cursor: pointer">
        <v-icon left color="orange" size="18">mdi-code-braces</v-icon>
        Full Templates YAML (Advanced)
        <v-spacer></v-spacer>
        <v-icon>{{ showFullEditor ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-card-title>

      <v-expand-transition>
        <div v-show="showFullEditor">
          <v-card-text>
            <v-alert type="warning" density="compact" class="mb-3">
              Edit all templates at once. Be careful - invalid YAML will break all templates.
            </v-alert>
            
            <v-textarea
              v-model="fullYaml"
              label="All Templates YAML"
              rows="20"
              variant="outlined"
              density="compact"
              class="yaml-editor"
              :error="!!fullYamlError"
              :error-messages="fullYamlError"
            ></v-textarea>
          </v-card-text>

          <v-card-actions class="pa-3">
            <v-btn color="secondary" @click="loadFullYaml" :disabled="!serverActive" size="small" variant="outlined">
              <v-icon start size="16">mdi-refresh</v-icon>
              Reload All
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn color="orange" @click="saveFullYaml" :disabled="!serverActive" :loading="savingFull" size="small" variant="elevated">
              <v-icon start size="16">mdi-content-save</v-icon>
              Save All Templates
            </v-btn>
          </v-card-actions>
        </div>
      </v-expand-transition>
    </v-card>
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

const getTemplateIcon = (id) => {
  if (id.includes('buyer')) return 'mdi-arrow-up-bold'
  if (id.includes('seller')) return 'mdi-arrow-down-bold'
  if (id.includes('speculator')) return 'mdi-chart-line'
  return 'mdi-robot'
}

const getTemplateColor = (id) => {
  if (id.includes('buyer')) return 'success'
  if (id.includes('seller')) return 'error'
  if (id.includes('speculator')) return 'info'
  return 'grey'
}

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

.compact-title {
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  padding: 0.5rem 0.75rem !important;
  background: rgba(248, 250, 252, 0.8);
  border-bottom: 1px solid rgba(203, 213, 225, 0.3);
  display: flex;
  align-items: center;
  color: #1e293b !important;
}

.template-preview {
  background: #f8fafc;
  border-radius: 8px;
  padding: 0.75rem;
}

.preview-stat {
  text-align: center;
  padding: 0.5rem;
}

.stat-label {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}

.yaml-editor :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
  font-size: 0.8rem !important;
  line-height: 1.5 !important;
}
</style>
