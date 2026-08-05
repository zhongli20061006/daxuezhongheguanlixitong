<template>
  <div class="agent-logo" aria-hidden="true">
    <div class="logo-ring"></div>
    <div class="logo-orbit"><span class="orbit-dot"></span></div>
    <div class="logo-core">
      <span class="logo-char">智</span>
    </div>
  </div>
</template>

<style scoped>
.agent-logo {
  position: relative;
  width: 120px;
  height: 120px;
}

.logo-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(from 0deg, #0F766E, #3E9A91, #0F766E);
  animation: logo-spin 6s linear infinite;
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
  mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
}

.logo-orbit {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  animation: logo-spin 9s linear infinite reverse;
}

.orbit-dot {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 9px;
  height: 9px;
  margin-left: -4.5px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 10px rgba(15, 118, 110, 0.7);
}

.logo-core {
  position: absolute;
  inset: 22px;
  border-radius: 50%;
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 14px 30px rgba(15, 118, 110, 0.32);
  animation: logo-breathe 3.2s ease-in-out infinite;
}

.logo-char {
  font-size: 44px;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.14);
}

@keyframes logo-spin {
  to { transform: rotate(360deg); }
}

@keyframes logo-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
</style>
