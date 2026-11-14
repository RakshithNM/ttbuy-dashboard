import Lenis from 'lenis'
import 'lenis/dist/lenis.css'

// One Lenis instance for the whole page. Null during SSG and before mount.
// Lenis turns itself off when the user prefers reduced motion.
let lenis: Lenis | null = null

export function initSmoothScroll(): void {
  if (lenis || typeof window === 'undefined') return
  lenis = new Lenis({
    autoRaf: true,
    // Chart tooltips and data tables scroll on their own; let the wheel
    // reach them instead of moving the page.
    allowNestedScroll: true,
  })
}

// Jump or glide to an element. Honors scroll-margin-top like scrollIntoView.
// Falls back to native scrolling when Lenis is not running.
export function scrollToEl(
  el: HTMLElement,
  { smooth = false, block = 'start' }: { smooth?: boolean; block?: 'start' | 'center' } = {},
): void {
  if (!lenis) {
    el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block })
    return
  }
  const offset = block === 'center' ? -(window.innerHeight - el.offsetHeight) / 2 : 0
  lenis.scrollTo(el, { offset, immediate: !smooth, force: true })
}
