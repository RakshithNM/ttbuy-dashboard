import type { Directive } from "vue";

// v-reveal: plays a left-to-right "draw-in" on a chart's data group the
// first time it scrolls into view, and replays it whenever the bound value
// changes (pass a key such as `${currency}-${range}` so toggling a single
// series doesn't replay, but switching dataset does).
//
// Classes are added from JS only, so the SSG-prerendered HTML (and any
// no-JS visitor) shows the chart fully drawn. Reduced-motion users get no
// animation — see the .fx-reveal rules in style.scss.
const observers = new WeakMap<Element, IntersectionObserver>();

function play(el: Element) {
  el.classList.remove("is-revealed");
  // Force a style flush so re-adding the class restarts the animation.
  void (el as HTMLElement).getBoundingClientRect();
  el.classList.add("is-revealed");
}

export const vReveal: Directive<Element, unknown> = {
  mounted(el) {
    if (typeof IntersectionObserver === "undefined") return;
    el.classList.add("fx-reveal");
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          play(el);
          io.disconnect();
          observers.delete(el);
        }
      },
      { threshold: 0.25 }
    );
    // Observe the enclosing <svg>, not the group itself: the group starts
    // fully clipped (zero visible area), so it would never count as visible.
    io.observe((el as SVGElement).ownerSVGElement ?? el);
    observers.set(el, io);
  },
  updated(el, binding) {
    if (binding.value === binding.oldValue) return;
    // Still waiting to scroll into view: the observer will play it.
    if (observers.has(el)) return;
    if (el.classList.contains("fx-reveal")) play(el);
  },
  unmounted(el) {
    observers.get(el)?.disconnect();
    observers.delete(el);
  },
};
