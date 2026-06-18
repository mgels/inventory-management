<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Set your available budget and we'll recommend forecast-driven items to restock.</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error && !recommendations.length" class="error">{{ error }}</div>
    <div v-else>
      <!-- Success banner -->
      <div v-if="submittedOrder" class="success-banner">
        <strong>Order {{ submittedOrder.order_number }} submitted.</strong>
        Expected delivery: {{ submittedOrder.expected_delivery }}.
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <!-- Budget card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Available Budget</h3>
        </div>
        <div class="budget-body">
          <div class="budget-display">
            {{ currencySymbol }}{{ budget.toLocaleString() }}
          </div>
          <input
            type="range"
            min="0"
            :max="maxBudget"
            step="250"
            v-model.number="budget"
            class="budget-slider"
          />
          <div class="slider-labels">
            <span>{{ currencySymbol }}0</span>
            <span>{{ currencySymbol }}{{ maxBudget.toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <!-- Recommendations card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommended Restock Items</h3>
          <div class="recommendations-summary">
            <span class="summary-count">{{ recommendations.length }} item{{ recommendations.length !== 1 ? 's' : '' }}</span>
            <span class="summary-divider">|</span>
            <span>
              Total: <strong>{{ currencySymbol }}{{ totalCost.toLocaleString() }}</strong>
              of {{ currencySymbol }}{{ budget.toLocaleString() }} budget
            </span>
          </div>
        </div>

        <div v-if="loading" class="loading">Loading recommendations...</div>
        <div v-else>
          <div class="table-container">
            <table class="restock-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Trend</th>
                  <th>Quantity</th>
                  <th>Unit Cost</th>
                  <th>Line Total</th>
                  <th>Lead Time</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="recommendations.length === 0">
                  <td colspan="6" class="empty-state">
                    No items fit this budget — increase the budget to see recommendations.
                  </td>
                </tr>
                <tr v-for="item in recommendations" :key="item.sku">
                  <td>
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-sku">{{ item.sku }}</div>
                  </td>
                  <td>
                    <span :class="['badge', getTrendClass(item.trend)]">{{ item.trend }}</span>
                  </td>
                  <td><strong>{{ item.quantity }}</strong></td>
                  <td>{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                  <td><strong>{{ currencySymbol }}{{ item.line_total.toLocaleString() }}</strong></td>
                  <td>{{ item.lead_time_days }} days</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card-footer">
            <button
              class="po-button create"
              :disabled="recommendations.length === 0 || submitting"
              @click="placeOrder"
            >
              {{ submitting ? 'Placing Order...' : 'Place Order' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(5000)
    const maxBudget = ref(10000)
    const recommendations = ref([])
    const totalCost = ref(0)
    const loading = ref(false)
    const error = ref(null)
    const submitting = ref(false)
    const submittedOrder = ref(null)

    let debounceTimer = null

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        const response = await api.getRestockingRecommendations(budget.value)
        recommendations.value = response.recommendations
        totalCost.value = response.total_cost
        if (response.max_budget && response.max_budget > 0) {
          maxBudget.value = response.max_budget
        }
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    const getTrendClass = (trend) => {
      const map = {
        'increasing': 'info',
        'stable': 'success',
        'decreasing': 'warning'
      }
      return map[trend] || 'info'
    }

    const placeOrder = async () => {
      submitting.value = true
      error.value = null
      try {
        const items = recommendations.value.map(r => ({
          sku: r.sku,
          name: r.name,
          quantity: r.quantity,
          unit_cost: r.unit_cost,
          lead_time_days: r.lead_time_days
        }))
        const order = await api.createRestockingOrder({ items })
        submittedOrder.value = order
        await loadRecommendations()
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 300)
    })

    onMounted(() => loadRecommendations())

    return {
      currencySymbol,
      budget,
      maxBudget,
      recommendations,
      totalCost,
      loading,
      error,
      submitting,
      submittedOrder,
      getTrendClass,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-body {
  padding: 1.5rem 1.5rem 1.25rem;
}

.budget-display {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin-bottom: 1.25rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #2563eb;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
  transition: background 0.2s;
}

.budget-slider::-moz-range-thumb:hover {
  background: #2563eb;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.recommendations-summary {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.875rem;
  color: #64748b;
}

.summary-count {
  font-weight: 600;
  color: #0f172a;
}

.summary-divider {
  color: #cbd5e1;
}

.restock-table {
  width: 100%;
}

.item-name {
  font-weight: 500;
  color: #0f172a;
  font-size: 0.875rem;
}

.item-sku {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.125rem;
}

.empty-state {
  text-align: center;
  color: #64748b;
  padding: 2rem 0.75rem;
  font-size: 0.875rem;
}

.card-footer {
  padding: 1rem 0 0.25rem;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #e2e8f0;
  margin-top: 0.75rem;
}

.po-button.create {
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.625rem 1.5rem;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.po-button.create:hover:not(:disabled) {
  background: #2563eb;
}

.po-button.create:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.success-banner {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}
</style>
