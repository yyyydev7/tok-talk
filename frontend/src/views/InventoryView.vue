<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { answer, inventory, inventoryBusy, inventoryError, loadInventory, selectedMaterial } from '../stores/tokTalk'
import { tr, uiLanguage } from '../stores/uiSettings'

const route = useRoute()
const materialId = computed(() => String(route.params.materialId ?? ''))
const materialName = computed(() => answer.value?.material?.name ?? selectedMaterial.value?.name ?? String(route.query.name ?? materialId.value))
const casNumber = computed(() => answer.value?.material?.cas_number ?? selectedMaterial.value?.cas_number ?? String(route.query.cas ?? ''))

function formatDateTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(uiLanguage.value === 'ko' ? 'ko-KR' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

watch(materialId, (id) => { if (id) void loadInventory(id) }, { immediate: true })
</script>

<template>
  <main class="workspace route-workspace">
    <div class="route-heading">
      <div>
        <RouterLink class="back-link" :to="answer ? { name: 'answers' } : { name: 'question' }">{{ tr(answer ? '← 질문 결과로 돌아가기' : '← 질문 화면으로 돌아가기') }}</RouterLink>
        <h1>{{ tr('시연용 재고') }}</h1>
        <p class="welcome-copy">{{ materialName }}<template v-if="casNumber"> · CAS {{ casNumber }}</template></p>
      </div>
      <span class="demo-tag large-demo-tag">{{ tr('시연용 데이터') }}</span>
    </div>

    <section class="inventory-page-card">
      <div class="inventory-head"><div class="inventory-icon">▤</div><div><h2>{{ materialName }} {{ tr('재고') }}</h2></div><span v-if="inventory?.is_demo" class="demo-tag">{{ tr('시연용') }}</span></div>
      <p class="inventory-caption">{{ tr('안전정보 답변과 별도로 재고 저장소에서 조회한 가상 데이터입니다.') }}</p>
      <div v-if="inventoryBusy" class="inventory-state route-inventory-state"><span class="spinner" aria-hidden="true"></span><p>{{ tr('재고를 조회하고 있습니다') }}</p></div>
      <div v-else-if="inventoryError" class="inventory-state inventory-error route-inventory-state"><span>!</span><div><strong>{{ tr('재고를 불러오지 못했어요') }}</strong><p>{{ tr(inventoryError) }}</p><button class="button button-soft retry-button" type="button" @click="loadInventory(materialId)">{{ tr('다시 조회') }}</button></div></div>
      <div v-else-if="inventory && inventory.items.length === 0" class="inventory-state empty-inventory route-inventory-state"><span>—</span><div><strong>{{ tr('등록된 시연 재고가 없습니다') }}</strong><p>{{ tr('빈 목록은 보유량 0을 의미하지 않습니다.') }}</p></div></div>
      <div v-else-if="inventory" class="stock-list inventory-page-list"><article v-for="item in inventory.items" :key="item.item_id" class="stock-item"><div class="stock-top"><strong>{{ item.display_name }}</strong><span class="stock-demo">{{ tr('시연용') }}</span></div><div class="stock-quantity">{{ item.quantity }}<small>{{ item.unit }}</small></div><div class="stock-meta"><span>⌖ {{ item.location }}</span><span>{{ tr('갱신') }} {{ formatDateTime(item.updated_at) }}</span></div></article></div>
      <div class="inventory-disclaimer">{{ tr('가상 데이터 · 실제 연구실 재고가 아닙니다') }}</div>
    </section>
  </main>
</template>
