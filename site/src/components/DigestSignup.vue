<script setup lang="ts">
import { ref } from "vue";

const email = ref("");
const currency = ref("USD");
const state = ref<"idle" | "loading" | "success" | "error">("idle");
const errorMsg = ref("");

async function subscribe() {
  const addr = email.value.trim();
  if (!addr) return;
  state.value = "loading";
  try {
    const res = await fetch("/api/email-subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: addr, currency: currency.value }),
    });
    const data = await res.json();
    if (res.ok && data.ok) {
      state.value = "success";
    } else {
      errorMsg.value = data.error ?? "Something went wrong.";
      state.value = "error";
    }
  } catch {
    errorMsg.value = "Network error — please try again.";
    state.value = "error";
  }
}
</script>

<template>
  <div class="digest-signup">
    <div v-if="state === 'success'" class="signup-success">
      <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="8" cy="8" r="6.5"/>
        <path d="M5 8.5l2 2 4-4"/>
      </svg>
      Subscribed. First digest lands this Friday.
    </div>
    <template v-else>
      <div class="signup-header">
        <svg class="signup-icon" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="1.5" y="3.5" width="13" height="9" rx="1.5"/>
          <path d="M1.5 5.5l6.5 4 6.5-4"/>
        </svg>
        <span class="signup-label">Weekly digest</span>
      </div>
      <p class="signup-sub">Best rate, worst rate, weekly spread — in your inbox every Friday.</p>
      <form class="signup-form" @submit.prevent="subscribe">
        <input
          v-model="email"
          type="email"
          placeholder="your@email.com"
          required
          autocomplete="email"
          class="signup-input"
          :disabled="state === 'loading'"
          aria-label="Email address"
        />
        <div class="signup-row">
          <select v-model="currency" class="signup-select" :disabled="state === 'loading'" aria-label="Currency">
            <option value="USD">USD</option>
            <option value="GBP">GBP</option>
            <option value="EUR">EUR</option>
            <option value="AED">AED</option>
          </select>
          <button type="submit" class="signup-btn" :disabled="state === 'loading'">
            <template v-if="state === 'loading'">
              <span class="signup-spinner" aria-hidden="true"></span>
            </template>
            <template v-else>Subscribe</template>
          </button>
        </div>
      </form>
      <p v-if="state === 'error'" class="signup-error" role="alert">{{ errorMsg }}</p>
    </template>
  </div>
</template>

<style scoped lang="scss">
.digest-signup {
  position: relative;
  padding: 28px 0 24px;

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 50%;
    width: 100vw;
    height: 1px;
    background: var(--gridline);
    transform: translateX(-50%);
  }
}

.signup-header {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 5px;
}

.signup-icon {
  color: var(--text-muted);
  flex: none;
}

.signup-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.signup-sub {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  max-width: 42ch;
}

.signup-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 400px;
}

.signup-input {
  width: 100%;
  padding: 8px 10px;
  font-size: 13px;
  border: 1px solid var(--gridline);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-primary);
  outline: none;
  transition: border-color 120ms ease;
  box-sizing: border-box;

  &:focus {
    border-color: var(--text-secondary);
  }

  &::placeholder {
    color: var(--text-muted);
  }

  &:disabled {
    opacity: 0.5;
  }
}

.signup-row {
  display: flex;
  gap: 8px;
}

.signup-select {
  padding: 8px 8px;
  font-size: 13px;
  border: 1px solid var(--gridline);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-secondary);
  cursor: pointer;
  flex: none;

  &:disabled {
    opacity: 0.5;
  }
}

.signup-btn {
  flex: 1;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  border-radius: 6px;
  background: var(--text-primary);
  color: var(--surface-1);
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  transition: opacity 120ms ease;

  &:disabled {
    opacity: 0.5;
    cursor: default;
  }

  &:not(:disabled):active {
    opacity: 0.8;
  }
}

.signup-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;

  @media (prefers-reduced-motion: reduce) {
    animation: none;
    opacity: 0.5;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.signup-success {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #22a36b;
  padding: 4px 0;
}

.signup-error {
  margin: 4px 0 0;
  font-size: 12px;
  color: #d84040;
}
</style>
