import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as selectionApi from '../api/selection'

export const useSelectionStore = defineStore('selection', () => {
  const availableCourses = ref([])
  const myCourses = ref([])
  const loading = ref(false)
  const availLoading = ref(false)

  const selectedCredits = computed(() =>
    myCourses.value.reduce((sum, c) => sum + parseFloat(c.credit || 0), 0)
  )

  async function fetchAvailableCourses() {
    availLoading.value = true
    try {
      const res = await selectionApi.getAvailableCourses()
      availableCourses.value = res.courses || []
    } finally {
      availLoading.value = false
    }
  }

  async function fetchMyCourses() {
    loading.value = true
    try {
      const res = await selectionApi.getMyCourses()
      myCourses.value = res.courses || []
    } finally {
      loading.value = false
    }
  }

  async function enroll(scheduleId) {
    const res = await selectionApi.enroll(scheduleId)
    await Promise.all([fetchMyCourses(), fetchAvailableCourses()])
    return res
  }

  async function drop(scheduleId) {
    const res = await selectionApi.drop(scheduleId)
    await Promise.all([fetchMyCourses(), fetchAvailableCourses()])
    return res
  }

  return { availableCourses, myCourses, loading, availLoading, selectedCredits, fetchAvailableCourses, fetchMyCourses, enroll, drop }
})
