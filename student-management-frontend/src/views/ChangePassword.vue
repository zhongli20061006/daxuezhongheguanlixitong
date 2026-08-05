<template>
  <div class="pwd-wrapper">
    <div class="pwd-card">
      <h2 style="text-align:center;margin-bottom:20px">修改密码</h2>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg=''" style="margin-bottom:12px" />
      <el-form @submit.prevent="handleChange">
        <el-form-item><el-input v-model="oldPwd" type="password" show-password placeholder="旧密码" size="large" @keyup.enter="handleChange" /></el-form-item>
        <el-form-item><el-input v-model="newPwd" type="password" show-password placeholder="新密码（至少6位）" size="large" @keyup.enter="handleChange" /></el-form-item>
        <el-form-item><el-input v-model="confirmPwd" type="password" show-password placeholder="确认新密码" size="large" @keyup.enter="handleChange" /></el-form-item>
        <el-form-item><el-button type="primary" size="large" :loading="loading" @click="handleChange" style="width:100%;height:44px">{{ loading?'提交中...':'确认修改' }}</el-button></el-form-item>
      </el-form>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const router=useRouter(); const authStore=useAuthStore()
const oldPwd=ref(''); const newPwd=ref(''); const confirmPwd=ref(''); const loading=ref(false); const errorMsg=ref('')
async function handleChange(){if(newPwd.value.length<6){errorMsg.value='新密码至少6位';return}if(newPwd.value!==confirmPwd.value){errorMsg.value='两次输入不一致';return}loading.value=true;errorMsg.value='';try{await authStore.changePassword(oldPwd.value,newPwd.value);const d={student:'/schedule',teacher:'/scores/input',staff:'/repairs/manage',admin:'/admin'};router.push(d[authStore.role]||'/')}catch{errorMsg.value='旧密码不正确'}finally{loading.value=false}}
</script>
<style scoped>
/* ── Page Wrapper (full-screen centered) ── */
.pwd-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
    background: var(--color-bg);
  padding: 24px;
}

/* ── Password Card ── */
.pwd-card {
  width: 400px;
  max-width: 100%;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: 36px 32px 28px;
  box-shadow: var(--shadow-xl);
  border: 1px solid rgba(255,255,255,0.1);
  animation: fadeInUp 0.4s ease-out;
  position: relative;
  overflow: hidden;
}

/* Decorative accent bar at top of card */
.pwd-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
}

/* ── Card Title ── */
.pwd-card h2 {
  text-align: center;
  margin-bottom: 24px;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.3px;
}

/* ── Input Enhancement ── */
.pwd-card .el-input__wrapper {
  border-radius: var(--radius-md);
  padding: 4px 12px;
}

/* ── Button Enhancement ── */
.pwd-card .el-button--primary {
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--radius-md);
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35);
  transition: all var(--transition-base);
}
.pwd-card .el-button--primary:hover {
    box-shadow: 0 6px 20px rgba(14, 165, 233, 0.45);
  transform: translateY(-1px);
}

/* ── Alert Enhancement ── */
.pwd-card .el-alert {
  border-radius: var(--radius-md);
}

/* ── Responsive ── */
@media (max-width: 480px) {
  .pwd-card {
    padding: 28px 20px 24px;
  }
  .pwd-card h2 {
    font-size: 20px;
  }
}
</style>
