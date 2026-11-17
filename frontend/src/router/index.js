import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/room/:code',
    name: 'room',
    component: () => import('@/views/RoomView.vue'),
    props: true,
  },
  {
    path: '/:section(how|variants|personas)',
    redirect: (to) => ({ path: '/', query: { section: to.params.section } }),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})
