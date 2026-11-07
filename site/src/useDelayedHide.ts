import { computed, onBeforeUnmount, shallowRef } from "vue";

// Hover state for a tooltip that sits outside its trigger. Moving the pointer
// from the trigger to the tooltip fires "leave" before "enter", so hiding
// waits a short delay that a new show() or cancelHide() can stop.
//
//   hidden ──show(v)──▶ shown ──scheduleHide()──▶ pendingHide ──delay──▶ hidden
//                        ▲                           │
//                        └─── show(v) / cancelHide() ┘
//   any state ──hide()──▶ hidden
export type DelayedHideState<T> =
  | { phase: "hidden" }
  | { phase: "shown"; value: T }
  | { phase: "pendingHide"; value: T };

export function useDelayedHide<T>(delayMs: number) {
  const state = shallowRef<DelayedHideState<T>>({ phase: "hidden" });
  let timer: ReturnType<typeof setTimeout> | null = null;

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function show(value: T) {
    clearTimer();
    state.value = { phase: "shown", value };
  }

  function cancelHide() {
    const s = state.value;
    if (s.phase !== "pendingHide") return;
    clearTimer();
    state.value = { phase: "shown", value: s.value };
  }

  function scheduleHide() {
    const s = state.value;
    if (s.phase === "hidden") return;
    clearTimer();
    state.value = { phase: "pendingHide", value: s.value };
    timer = setTimeout(() => {
      timer = null;
      state.value = { phase: "hidden" };
    }, delayMs);
  }

  function hide() {
    clearTimer();
    state.value = { phase: "hidden" };
  }

  // The value is still shown while a hide is pending.
  const current = computed<T | null>(() => (state.value.phase === "hidden" ? null : state.value.value));

  onBeforeUnmount(clearTimer);

  return { state, current, show, cancelHide, scheduleHide, hide };
}
