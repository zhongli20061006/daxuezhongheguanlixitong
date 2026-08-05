<template>
  <AppNavbar v-if="showNavbar">
    <router-view v-slot="{ Component }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </AppNavbar>
  <router-view v-else v-slot="{ Component }">
    <transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const route = useRoute()
const authStore = useAuthStore()

const showNavbar = computed(() => route.path !== '/login' && route.path !== '/change-password')

onMounted(() => authStore.restoreSession())
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

/* ── Page transition ── */
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
