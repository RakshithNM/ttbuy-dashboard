<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { shortName } from "../bankPalette";

const props = defineProps<{
  bank: string;
  currency: string;
  currentRate: number;
}>();

const VAPID_KEY = "BEFtQ5_k0qteRW-1Udl62eHhyNwBvg43EXp61vkl1yDveOFRqqJq4JOyMLDzT_C-cC0XlppDC5oF_OkaAqIUIQo";

function vapidKeyBuffer(b64: string): ArrayBuffer {
  const padding = "=".repeat((4 - (b64.length % 4)) % 4);
  const base64 = (b64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr.buffer;
}

const supported = ref(false);
const open = ref(false);
const threshold = ref(0);
const direction = ref<"above" | "below">("above");
const status = ref<"idle" | "loading" | "subscribed" | "error">("idle");
const errorMsg = ref("");
const alertedBank = ref("");
const alertedCurrency = ref("");
const alertedThreshold = ref(0);
const alertedDirection = ref<"above" | "below">("above");

// Set threshold default once when rate becomes available
watch(
  () => props.currentRate,
  (v) => { if (v > 0 && threshold.value === 0) threshold.value = parseFloat(v.toFixed(2)); },
  { immediate: true }
);

// Reset when bank changes so stale subscription state doesn't carry over
watch(() => props.bank, async () => {
  open.value = false;
  status.value = "idle";
  threshold.value = 0; // allow rate watch to repopulate if no stored alert
  await checkExisting();
});

async function checkExisting() {
  if (!supported.value) return;
  try {
    const reg = await navigator.serviceWorker.getRegistration("/sw.js");
    const sub = reg ? await reg.pushManager.getSubscription() : null;
    if (!sub) { status.value = "idle"; alertedBank.value = ""; return; }
    const res = await fetch(`/.netlify/functions/subscribe?endpoint=${encodeURIComponent(sub.endpoint)}`);
    if (res.ok) {
      const { alerts } = await res.json();
      const active = alerts[0] as { bank: string; currency: string; threshold: number; direction: string } | undefined;
      if (active) {
        alertedBank.value = active.bank;
        alertedCurrency.value = active.currency;
        alertedThreshold.value = active.threshold;
        alertedDirection.value = active.direction as "above" | "below";
        status.value = "subscribed";
        if (active.bank === props.bank && active.currency === props.currency) {
          threshold.value = active.threshold;
          direction.value = active.direction as "above" | "below";
        }
      } else {
        status.value = "idle";
        alertedBank.value = "";
      }
    } else {
      status.value = "subscribed";
      alertedBank.value = "";
    }
  } catch {
    status.value = "idle";
  }
}

onMounted(async () => {
  supported.value = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  await checkExisting();
});

async function enable() {
  if (!VAPID_KEY) { errorMsg.value = "Push not configured (missing VITE_VAPID_PUBLIC_KEY)"; status.value = "error"; return; }
  status.value = "loading";
  errorMsg.value = "";
  try {
    const perm = await Notification.requestPermission();
    if (perm !== "granted") throw new Error("Notification permission denied");

    let reg = await navigator.serviceWorker.getRegistration("/sw.js");
    if (!reg) reg = await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidKeyBuffer(VAPID_KEY),
    });

    const res = await fetch("/.netlify/functions/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subscription: sub.toJSON(),
        alerts: [{ bank: props.bank, currency: props.currency, threshold: threshold.value, direction: direction.value }],
      }),
    });
    if (!res.ok) throw new Error("Server error saving subscription");

    status.value = "subscribed";
    alertedBank.value = props.bank;
    alertedCurrency.value = props.currency;
    alertedThreshold.value = threshold.value;
    alertedDirection.value = direction.value;
    open.value = false;
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : "Something went wrong";
    status.value = "error";
  }
}

async function disable() {
  status.value = "loading";
  errorMsg.value = "";
  try {
    const reg = await navigator.serviceWorker.getRegistration("/sw.js");
    const sub = reg ? await reg.pushManager.getSubscription() : null;
    if (sub) {
      await fetch("/.netlify/functions/subscribe", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
      await sub.unsubscribe();
    }
    status.value = "idle";
    alertedBank.value = "";
    alertedCurrency.value = "";
    alertedThreshold.value = 0;
    alertedDirection.value = "above";
    open.value = false;
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : "Failed to disable";
    status.value = "error";
  }
}
</script>

<template>
  <div v-if="supported" class="as-strip">
    <div class="as-bar">
      <!-- Bell icon -->
      <svg class="as-bell" :class="{ active: status === 'subscribed' }" viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M8 1.5a4.5 4.5 0 0 1 4.5 4.5c0 2.5.8 3.5 1.2 4H2.3c.4-.5 1.2-1.5 1.2-4A4.5 4.5 0 0 1 8 1.5z"/>
        <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0"/>
      </svg>

      <button class="as-toggle" @click="open = !open" :aria-expanded="open">
        <span v-if="status === 'subscribed' && alertedBank === props.bank && alertedCurrency === props.currency">Alert on</span>
        <span v-else-if="status === 'subscribed'">Alert for {{ shortName(alertedBank) }} when rate goes {{ alertedDirection }} ₹{{ alertedThreshold.toFixed(2) }}</span>
        <span v-else>Set alert</span>
        <svg class="as-chevron" :class="{ rotated: open }" viewBox="0 0 10 6" width="9" height="6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
          <path d="M1 1l4 4 4-4"/>
        </svg>
      </button>

      <button v-if="status === 'subscribed'" class="as-off" @click="disable" aria-label="Disable alert">
        Disable
      </button>
    </div>

    <div v-if="open" class="as-panel">
      <div class="as-row">
        <span class="as-label">Notify me when {{ props.bank.toUpperCase() }} rate goes</span>
        <select v-model="direction" class="as-dir">
          <option value="above">above</option>
          <option value="below">below</option>
        </select>
        <span class="as-prefix">₹</span>
        <input
          v-model.number="threshold"
          type="number"
          step="0.01"
          min="0"
          class="as-thresh"
          aria-label="Rate threshold"
        />
      </div>
      <div class="as-actions">
        <button
          class="as-enable"
          :disabled="status === 'loading'"
          @click="enable"
        >
          {{ status === "loading" ? "Enabling..." : (status === "subscribed" && alertedBank === props.bank && alertedCurrency === props.currency) ? "Update" : "Enable" }}
        </button>
        <span v-if="status === 'error'" class="as-err">{{ errorMsg }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.as-strip {
  border-top: 1px solid var(--border);
  padding-top: 8px;
  margin-top: 8px;
}

.as-bar {
  display: flex;
  align-items: center;
  gap: 5px;
}

.as-bell {
  color: var(--text-muted);
  flex: none;

  &.active {
    color: var(--accent);
    fill: color-mix(in srgb, var(--accent) 20%, transparent);
  }
}

.as-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  flex: 1;

  &:hover {
    color: var(--text-secondary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

.as-chevron {
  transition: transform 150ms ease;
  &.rotated { transform: rotate(180deg); }
}

.as-off {
  background: none;
  border: none;
  font-size: 11px;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 3px;

  &:hover {
    color: var(--status-serious);
    background: color-mix(in srgb, var(--status-serious) 10%, transparent);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
  }

  &:disabled { opacity: 0.5; cursor: default; }
}

.as-panel {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 8px 0 2px;
}

.as-row {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.as-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.as-dir {
  font-size: 12px;
  font-family: inherit;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 4px;
  background: var(--surface-1);
  color: var(--text-primary);
  cursor: pointer;

  &:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
}

.as-prefix {
  font-size: 12px;
  color: var(--text-muted);
}

.as-thresh {
  width: 72px;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 12px;
  font-family: "Menlo", "Monaco", "Consolas", monospace;
  background: var(--surface-1);
  color: var(--text-primary);

  &:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }

  &::-webkit-inner-spin-button,
  &::-webkit-outer-spin-button {
    -webkit-appearance: none;
  }
}

.as-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.as-enable {
  font-size: 12px;
  font-family: inherit;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 5px;
  border: none;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  transition: opacity 100ms;

  &:hover { opacity: 0.85; }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  &:disabled { opacity: 0.5; cursor: default; }
}

.as-err {
  font-size: 11px;
  color: var(--status-serious);
}
</style>
