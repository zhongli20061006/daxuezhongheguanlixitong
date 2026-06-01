<template>
  <div class="app-container">
    <AppNavbar v-if="showNavbar" />
    <router-view />
  </div>
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
body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; }
.app-container { min-height: 100vh; }
</style>
