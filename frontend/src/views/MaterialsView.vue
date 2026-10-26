<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { clearResult, loadMaterials, materialQuery, materials, materialsBusy, materialsSearched, pageError, selectedMaterial } from '../stores/tokTalk'
import type { Material } from '../stores/tokTalk'

const router = useRouter()

async function search() {
  await loadMaterials()
}

function choose(material: Material) {
  selectedMaterial.value = material
  clearResult()
  void router.push({ name: 'question' })
}

onMounted(() => {
  if (!materialsSearched.value && materials.value.length === 0) void loadMaterials()
})
</script>

<template>
  <main class="workspace route-workspace">
    <div class="route-heading">
      <div>
        <RouterLink class="back-link" :to="{ name: 'question' }">← 질문으로 돌아가기</RouterLink>
        <p class="eyebrow">MATERIAL CATALOG</p>
        <h1>물질 검색·선택</h1>
        <p class="welcome-copy">이름이나 동의어로 자료가 등록된 물질을 찾아 질문에 지정합니다.</p>
      </div>
      <span class="step-number">01</span>
    </div>

    <section class="query-card material-page-card">
      <form class="material-search-form" @submit.prevent="search">
        <label for="material-search">물질명 또는 동의어</label>
        <div class="picker-row">
          <input id="material-search" v-model="materialQuery" placeholder="예: 아세톤, ethanol" />
          <button class="button button-primary search-button" type="submit" :disabled="materialsBusy">{{ materialsBusy ? '찾는 중…' : '물질 찾기' }}</button>
        </div>
      </form>
      <div v-if="pageError" class="error-banner" role="alert"><span>!</span>{{ pageError }}</div>
      <div v-if="materials.length" class="material-grid" aria-label="검색된 물질 목록">
        <article v-for="item in materials" :key="item.material_id" class="material-result-card">
          <div class="material-result-main">
            <span class="chemical-symbol">{{ item.name.slice(0, 1) }}</span>
            <div class="material-details"><strong>{{ item.name }}</strong><small>CAS {{ item.cas_number || '정보 없음' }}</small></div>
          </div>
          <p v-if="item.aliases?.length" class="material-aliases">동의어: {{ item.aliases.join(', ') }}</p>
          <p v-if="item.source_title" class="material-source">자료: {{ item.source_title }}</p>
          <button class="button button-soft select-material-button" type="button" @click="choose(item)">이 물질로 질문하기 <span>→</span></button>
        </article>
      </div>
      <div v-else-if="!materialsBusy && materialsSearched && !pageError" class="empty-state">
        <span class="empty-symbol">⌕</span><strong>일치하는 물질이 없습니다</strong><p>물질명이나 영문 동의어를 바꿔 검색해 주세요.</p>
      </div>
      <div v-else-if="!materialsBusy && !materialsSearched && !pageError" class="empty-state">
        <span class="empty-symbol">⌕</span><strong>물질명을 검색해 주세요</strong><p>검색된 후보 중 하나를 선택하면 질문 화면으로 돌아갑니다.</p>
      </div>
      <div v-else-if="materialsBusy" class="route-loading"><span class="spinner" aria-hidden="true"></span><span>물질 목록을 불러오고 있습니다</span></div>
    </section>
  </main>
</template>
