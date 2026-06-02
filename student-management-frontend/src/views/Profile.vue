<template>
  <div class="page-container">
    <h2 class="page-title">个人中心</h2>
    <el-skeleton :loading="loading" animated :count="3">
      <div v-if="profile" class="content-card">
        <div class="info-section">
          <div class="avatar-circle">{{ profile.name?.charAt(0) || '?' }}</div>
          <div class="info-main">
            <div class="info-name">{{ profile.name }}</div>
            <div class="info-line"><span class="info-tag">学号/工号</span>{{ profile.user_id }}</div>
            <div class="info-line" v-if="profile.class_name"><span class="info-tag">班级</span>{{ profile.class_name }}</div>
            <div class="info-line" v-if="profile.major"><span class="info-tag">专业</span>{{ profile.major }}</div>
            <div class="info-line" v-if="profile.grade"><span class="info-tag">年级</span>{{ profile.grade }}级</div>
            <div class="info-line" v-if="profile.advisor_name"><span class="info-tag">辅导员</span>{{ profile.advisor_name }}</div>
            <div class="info-line" v-if="profile.department"><span class="info-tag">院系</span>{{ profile.department }}</div>
            <div class="info-line" v-if="profile.title"><span class="info-tag">职称</span>{{ profile.title }}</div>
            <div class="info-line"><span class="info-tag">手机</span>
              <template v-if="profile.phone">
                {{ profile.phone }}
                <el-button text type="primary" size="small" @click="editPhoneVisible=true">修改</el-button>
              </template>
              <el-button v-else text type="primary" size="small" @click="editPhoneVisible=true">绑定手机号</el-button>
            </div>
          </div>
        </div>
        <el-button type="primary" style="margin-top:16px" @click="$router.push('/change-password')">修改密码</el-button>
      </div>
      <el-alert v-else-if="error" :title="error" type="error" show-icon style="margin-bottom:16px" :closable="false" />
    </el-skeleton>

    <div v-if="profile && statEntries.length" class="stat-cards" style="margin-top:24px">
      <div v-for="s in statEntries" :key="s.label" class="stat-card">
        <div class="stat-icon" style="background:#EFF6FF">📊</div>
        <div>
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="editPhoneVisible" title="修改手机号" width="380px">
      <el-form @submit.prevent="updatePhone">
        <el-input v-model="newPhone" placeholder="输入11位手机号" maxlength="11" show-word-limit />
      </el-form>
      <template #footer>
        <el-button @click="editPhoneVisible=false">取消</el-button>
        <el-button type="primary" @click="updatePhone" :loading="phoneLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const profile = ref(null)
const loading = ref(true)
const error = ref('')
const editPhoneVisible = ref(false)
const newPhone = ref('')
const phoneLoading = ref(false)

const statEntries = computed(() => {
  if (!profile.value?.statistics) return []
  const keys = Object.keys(profile.value.statistics)
  return keys.filter(k => profile.value.statistics[k] && profile.value.statistics[k] !== '0')
    .map(k => ({ label: k, value: profile.value.statistics[k] }))
})

async function load() {
  loading.value = true; error.value = ''
  try {
    const { default: request } = await import('../api/index')
    const res = await request.get('/profile')
    profile.value = res
  } catch { error.value = '加载失败' }
  finally { loading.value = false }
}

async function updatePhone() {
  const phone = newPhone.value?.trim()
  if (!phone || !/^1\d{10}$/.test(phone)) { ElMessage.warning('请输入正确的11位手机号'); return }
  phoneLoading.value = true
  try {
    const { default: request } = await import('../api/index')
    await request.put('/profile/phone', { phone })
    ElMessage.success('手机号已更新')
    editPhoneVisible.value = false
    profile.value.phone = phone.slice(0, 3) + '****' + phone.slice(-4)
    profile.value.phone_raw = phone
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '修改失败') }
  finally { phoneLoading.value = false }
}

onMounted(load)
</script>

<style scoped>
.info-section { display:flex; gap:24px; align-items:flex-start; }
.avatar-circle { width:72px; height:72px; border-radius:50%; background:linear-gradient(135deg,#2563EB,#1E3A5F); display:flex; align-items:center; justify-content:center; font-size:28px; color:#fff; flex-shrink:0; }
.info-main { flex:1; }
.info-name { font-size:22px; font-weight:700; margin-bottom:12px; }
.info-line { font-size:14px; color:#4B5563; margin:6px 0; }
.info-tag { display:inline-block; color:#6B7280; font-size:12px; background:#F3F4F6; padding:1px 8px; border-radius:4px; margin-right:8px; min-width:60px; text-align:center; }
@media (max-width:768px) { .info-section { flex-direction:column; align-items:center; text-align:center; } }
</style>
