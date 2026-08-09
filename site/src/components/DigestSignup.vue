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
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="8" cy="8" r="6.5" />
        <path d="M5 8.5l2 2 4-4" />
      </svg>
      You're in — digest lands every Friday.
    </div>
    <template v-else>
      <p class="signup-label">Get the best rates every Friday, in your inbox.</p>
      <form class="signup-form" @submit.prevent="subscribe">
        <input
          v-model="email"
          type="email"
          placeholder="your@email.com"
          required
          autocomplete="email"
          class="signup-input"
          :disabled="state === 'loading'"
        />
        <select v-model="currency" class="signup-select" :disabled="state === 'loading'">
          <option value="USD">USD</option>
          <option value="GBP">GBP</option>
          <option value="EUR">EUR</option>
          <option value="AED">AED</option>
        </select>
        <button type="submit" class="signup-btn" :disabled="state === 'loading'">
          {{ state === "loading" ? "…" : "Subscribe" }}
        </button>
      </form>
      <p v-if="state === 'error'" class="signup-error">{{ errorMsg }}</p>
    </template>
  </div>
</template>

<style scoped lang="scss">
.digest-signup {
  border-top: 1px solid var(--gridline);
  padding: 20px 0 4px;
  margin-top: 8px;
}

.signup-label {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.signup-form {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.signup-input {
  flex: 1;
  min-width: 180px;
  padding: 7px 10px;
  font-size: 13px;
  border: 1px solid var(--gridline);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-primary);
  outline: none;

  &:focus {
    border-color: var(--text-secondary);
  }

  &::placeholder {
    color: var(--text-muted);
  }
}

.signup-select {
  padding: 7px 8px;
  font-size: 13px;
  border: 1px solid var(--gridline);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-primary);
  cursor: pointer;
}

.signup-btn {
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  border-radius: 6px;
  background: var(--text-primary);
  color: var(--surface-1);
  cursor: pointer;
  white-space: nowrap;

  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
}

.signup-success {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: #22a36b;
}

.signup-error {
  margin: 6px 0 0;
  font-size: 12px;
  color: #d84040;
}
</style>
