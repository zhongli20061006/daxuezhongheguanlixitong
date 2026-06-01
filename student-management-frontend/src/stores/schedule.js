import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as scheduleApi from '../api/schedule'

export const useScheduleStore = defineStore('schedule', () => {
  const weeklyCourses = ref({})
  const semester = ref('')
  const loading = ref(false)

  async function fetchMySchedule() {
    loading.value = true
    try {
      const res = await scheduleApi.getMySchedule()
      const grouped = {}
      for (const course of res.schedules || []) {
        const day = course.day_of_week
        if (!grouped[day]) grouped[day] = []
        grouped[day].push(course)
      }
      weeklyCourses.value = grouped
    } finally {
      loading.value = false
    }
  }

  return { weeklyCourses, semester, loading, fetchMySchedule }
})
