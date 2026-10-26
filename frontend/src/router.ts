import { createRouter, createWebHistory } from 'vue-router'
import AuthView from './views/AuthView.vue'
import QuestionView from './views/QuestionView.vue'
import MaterialsView from './views/MaterialsView.vue'
import AnswersView from './views/AnswersView.vue'
import InventoryView from './views/InventoryView.vue'
import { answer, authState, checkAuth } from './stores/tokTalk'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: AuthView, props: { mode: 'login' }, meta: { guestOnly: true } },
    { path: '/signup', name: 'signup', component: AuthView, props: { mode: 'signup' }, meta: { guestOnly: true } },
    { path: '/', name: 'question', component: QuestionView, meta: { requiresAuth: true } },
    { path: '/materials', name: 'materials', component: MaterialsView, meta: { requiresAuth: true } },
    { path: '/answers', name: 'answers', component: AnswersView, meta: { requiresAuth: true } },
    { path: '/inventory/:materialId', name: 'inventory', component: InventoryView, meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: { name: 'question' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const authorized = authState.value === 'signed-in' || await checkAuth()
    if (!authorized) return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'answers' && !answer.value) return { name: 'question' }

  if (to.meta.guestOnly) {
    const authorized = authState.value === 'signed-in' || (authState.value === 'checking' && await checkAuth())
    if (authorized) return { name: 'question' }
  }

  return true
})

export default router
