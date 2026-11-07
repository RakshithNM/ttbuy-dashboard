<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { currencySymbol } from "../currencies";

// Decorative header scene: foreign-currency notes fly into a bank and
// rupee coins hop out the other side. Pure SVG + CSS keyframes, so it is
// fully present in the SSG prerender and costs no JS per frame.
//
// Timing (all keyframes below are built around these numbers):
// - Bills: 4.2s loop, 3 bills staggered 1.4s apart, so one lands in the
//   roof slot every 1.4s (at 42% of a bill's cycle ≈ 1.76s after its start).
// - Bank "gulp": 1.4s loop, squashes right when a bill lands.
// - Coins: 2.8s loop, 4 coins staggered 0.7s apart, so two coins come out
//   per bill, starting just after the gulp.
const props = defineProps<{ currency: string }>();

const symbol = computed(() => currencySymbol(props.currency).trim());
// "AED" is three glyphs; shrink it so it fits on a 44px-wide note.
const symbolSize = computed(() => (symbol.value.length > 1 ? 9 : 13));

const BILL_DELAYS = [0, 1.4, 2.8];
// Resting x offsets for the reduced-motion (static) frame: a neat row of
// coins to the right of the bank instead of all stacked in the doorway.
const COINS = [0, 1, 2, 3].map((i) => ({ delay: 0.45 + i * 0.7, restX: 40 + i * 24 }));

// Stop the loop while the header is scrolled out of view.
const root = ref<SVGSVGElement | null>(null);
const paused = ref(false);
let io: IntersectionObserver | null = null;
onMounted(() => {
  if (!root.value || typeof IntersectionObserver === "undefined") return;
  io = new IntersectionObserver((entries) => {
    paused.value = !entries.some((e) => e.isIntersecting);
  });
  io.observe(root.value);
});
onBeforeUnmount(() => io?.disconnect());
</script>

<template>
  <svg
    ref="root"
    class="money-flow"
    :class="{ paused }"
    viewBox="0 0 320 150"
    role="img"
    :aria-label="`${currency} notes go into a bank and come out as rupee coins`"
  >
    <defs>
      <radialGradient id="mf-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="var(--mf-coin)" stop-opacity="0.55" />
        <stop offset="100%" stop-color="var(--mf-coin)" stop-opacity="0" />
      </radialGradient>
    </defs>

    <!-- direction of travel -->
    <path class="flow" d="M 40 74 Q 98 6 160 38" />
    <path class="flow" d="M 172 100 Q 236 70 304 104" />

    <!-- static pile the flying notes are taken from -->
    <g transform="translate(34 96) rotate(-6)">
      <g class="bill">
        <rect x="-22" y="-12" width="44" height="24" rx="3" class="bill-body" />
        <rect x="-19" y="-9" width="38" height="18" rx="2" class="bill-inner" />
        <Transition name="mf-sym" mode="out-in">
          <text :key="symbol" class="bill-sym" :font-size="symbolSize">{{ symbol }}</text>
        </Transition>
      </g>
    </g>
    <g transform="translate(40 88) rotate(4)">
      <g class="bill">
        <rect x="-22" y="-12" width="44" height="24" rx="3" class="bill-body" />
        <rect x="-19" y="-9" width="38" height="18" rx="2" class="bill-inner" />
        <Transition name="mf-sym" mode="out-in">
          <text :key="symbol" class="bill-sym" :font-size="symbolSize">{{ symbol }}</text>
        </Transition>
      </g>
    </g>

    <!-- flying notes: outer g = start position, inner g = animated -->
    <g v-for="(d, i) in BILL_DELAYS" :key="`bill-${i}`" transform="translate(36 80)">
      <g class="bill bill-fly" :style="{ animationDelay: `${d}s` }">
        <rect x="-22" y="-12" width="44" height="24" rx="3" class="bill-body" />
        <rect x="-19" y="-9" width="38" height="18" rx="2" class="bill-inner" />
        <Transition name="mf-sym" mode="out-in">
          <text :key="symbol" class="bill-sym" :font-size="symbolSize">{{ symbol }}</text>
        </Transition>
      </g>
    </g>

    <!-- bank -->
    <ellipse class="bank-glow" cx="160" cy="88" rx="46" ry="34" fill="url(#mf-glow)" />
    <g class="bank">
      <polygon points="108,54 160,24 212,54" class="bank-part" />
      <rect x="148" y="38" width="24" height="5" rx="2.5" class="slot" />
      <rect x="110" y="54" width="100" height="8" rx="1.5" class="bank-part" />
      <rect x="118" y="62" width="9" height="38" class="bank-part" />
      <rect x="134" y="62" width="9" height="38" class="bank-part" />
      <rect x="177" y="62" width="9" height="38" class="bank-part" />
      <rect x="193" y="62" width="9" height="38" class="bank-part" />
      <path d="M 150 100 V 78 a 10 10 0 0 1 20 0 V 100 Z" class="door" />
      <rect x="106" y="100" width="108" height="6" rx="1.5" class="bank-part" />
      <rect x="100" y="106" width="120" height="6" rx="1.5" class="bank-part" />
    </g>
    <text x="160" y="130" class="bank-label">Your bank</text>

    <!-- rupee coins: outer g = door position, middle = hop path, inner = flip -->
    <g v-for="(c, i) in COINS" :key="`coin-${i}`" transform="translate(164 95)">
      <g class="coin-hop" :style="{ animationDelay: `${c.delay}s`, '--rest-x': `${c.restX}px` }">
        <g class="coin-flip" :style="{ animationDelay: `${c.delay}s` }">
          <circle r="9" class="coin-body" />
          <circle r="6.5" class="coin-ring" />
          <text class="coin-sym">₹</text>
        </g>
      </g>
    </g>
  </svg>
</template>

<style scoped lang="scss">
.money-flow {
  --mf-bill-fill: light-dark(#e3f4e8, #1b3a27);
  --mf-bill-edge: light-dark(#3f9d5f, #4fb874);
  --mf-bill-ink: light-dark(#1f6b3a, #a6e3bb);
  --mf-coin: light-dark(#f3b733, #e9ab2b);
  --mf-coin-edge: light-dark(#c4870f, #b47e14);
  --mf-coin-ink: light-dark(#7a4f00, #4a3000);

  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

// ── static parts ──
.flow {
  fill: none;
  stroke: var(--baseline);
  stroke-width: 1.5;
  stroke-dasharray: 2 6;
  stroke-linecap: round;
}

.bill-body {
  fill: var(--mf-bill-fill);
  stroke: var(--mf-bill-edge);
  stroke-width: 1.5;
}
.bill-inner {
  fill: none;
  stroke: var(--mf-bill-edge);
  stroke-width: 0.75;
  opacity: 0.6;
}
.bill-sym {
  fill: var(--mf-bill-ink);
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: central;
}

.bank-part {
  fill: var(--surface-1);
  stroke: var(--text-secondary);
  stroke-width: 1.75;
  stroke-linejoin: round;
}
.slot {
  fill: var(--text-primary);
}
.door {
  fill: color-mix(in srgb, var(--mf-coin) 30%, var(--surface-1));
  stroke: var(--text-secondary);
  stroke-width: 1.75;
}
.bank-label {
  fill: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-anchor: middle;
}
.bank-glow {
  opacity: 0.35;
}

.coin-body {
  fill: var(--mf-coin);
  stroke: var(--mf-coin-edge);
  stroke-width: 1.5;
}
.coin-ring {
  fill: none;
  stroke: var(--mf-coin-edge);
  stroke-width: 0.75;
  opacity: 0.7;
}
.coin-sym {
  fill: var(--mf-coin-ink);
  font-size: 10px;
  font-weight: 800;
  text-anchor: middle;
  dominant-baseline: central;
}

// Reduced motion / no-animation frame: coins sit in a row to the right.
.coin-hop {
  transform: translate(var(--rest-x), 8px);
}

.bill-fly,
.coin-hop,
.coin-flip,
.bank,
.bank-glow {
  transform-box: fill-box;
  transform-origin: center;
}
.bank {
  transform-origin: 50% 100%;
}

// Symbol swap when the currency tab changes.
.mf-sym-enter-active,
.mf-sym-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
  transform-box: fill-box;
  transform-origin: center;
}
.mf-sym-enter-from,
.mf-sym-leave-to {
  opacity: 0;
  transform: scale(0.4);
}

// ── motion ──
@media (prefers-reduced-motion: no-preference) {
  .flow {
    animation: mf-flow 1.2s linear infinite;
  }

  // Animated notes start hidden on the pile; the keyframes bring them in.
  .bill-fly {
    opacity: 0;
    animation: mf-bill 4.2s cubic-bezier(0.45, 0, 0.55, 1) infinite both;
  }

  .bank {
    animation: mf-gulp 1.4s ease-out infinite;
    animation-delay: 0.36s;
  }
  .bank-glow {
    animation: mf-glow 1.4s ease-out infinite;
    animation-delay: 0.36s;
  }

  .coin-hop {
    opacity: 0;
    animation: mf-coin-hop 2.8s linear infinite both;
  }
  .coin-flip {
    animation: mf-coin-flip 0.7s linear infinite;
  }

  .paused,
  .paused * {
    animation-play-state: paused !important;
  }
}

@keyframes mf-flow {
  to { stroke-dashoffset: -16; }
}

// Pile (36,80) → arc over → roof slot (160,40) = translate(124,-40).
@keyframes mf-bill {
  0%   { opacity: 0; transform: translate(0, 0) rotate(-8deg) scale(0.9); }
  8%   { opacity: 1; transform: translate(0, -4px) rotate(-8deg) scale(1); }
  18%  { opacity: 1; transform: translate(0, -4px) rotate(-8deg) scale(1); }
  30%  { opacity: 1; transform: translate(62px, -58px) rotate(12deg) scale(0.95); }
  38%  { opacity: 1; transform: translate(118px, -44px) rotate(2deg) scale(0.6); }
  42%  { opacity: 0; transform: translate(124px, -38px) rotate(0deg) scale(0.25); }
  100% { opacity: 0; transform: translate(124px, -38px) rotate(0deg) scale(0.25); }
}

@keyframes mf-gulp {
  0%, 100% { transform: scale(1, 1); }
  12%      { transform: scale(1.025, 0.965); }
  30%      { transform: scale(0.99, 1.01); }
  45%      { transform: scale(1, 1); }
}

@keyframes mf-glow {
  0%, 100% { opacity: 0.2; transform: scale(0.9); }
  15%      { opacity: 0.75; transform: scale(1.08); }
  60%      { opacity: 0.3; transform: scale(1); }
}

// From the door (164,95): pop up, two shrinking bounces, roll off, fade.
@keyframes mf-coin-hop {
  0%   { opacity: 0; transform: translate(0, 0) scale(0.3); }
  6%   { opacity: 1; transform: translate(10px, -16px) scale(1); }
  18%  { transform: translate(42px, -32px) scale(1); }
  30%  { transform: translate(74px, 8px) scale(1.05, 0.9); }
  40%  { transform: translate(96px, -10px) scale(1); }
  50%  { transform: translate(114px, 8px) scale(1.03, 0.94); }
  56%  { transform: translate(122px, 2px) scale(1); }
  62%  { opacity: 1; transform: translate(130px, 8px) scale(1); }
  78%  { opacity: 0; transform: translate(146px, 8px) scale(1); }
  100% { opacity: 0; transform: translate(146px, 8px) scale(1); }
}

// Fake a coin spinning about its vertical axis.
@keyframes mf-coin-flip {
  0%, 100% { transform: scaleX(1); }
  50%      { transform: scaleX(0.15); }
}
</style>
