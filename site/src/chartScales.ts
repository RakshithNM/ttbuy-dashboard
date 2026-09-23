import { scaleLinear, scaleTime } from "d3-scale";
import { area as d3Area, line as d3Line } from "d3-shape";
import { bisector } from "d3-array";

export function createTimeScale(domain: [number, number], range: [number, number]) {
  return scaleTime().domain(domain).range(range);
}

export function createLinearScale(domain: [number, number], range: [number, number]) {
  return scaleLinear().domain(domain).range(range);
}

export function linePathFor<T>(points: T[], x: (d: T) => number, y: (d: T) => number): string {
  return d3Line<T>().x(x).y(y)(points) ?? "";
}

export function areaPathFor<T>(points: T[], x: (d: T) => number, y: (d: T) => number, y0: number): string {
  return d3Area<T>().x(x).y1(y).y0(y0)(points) ?? "";
}

// Generates tick values at a fixed step across [min, max], rounded to 2
// decimals — shared by every chart's y-axis, which each pick their own step
// (rate charts need finer steps than a rupee-spread chart) but all render
// ticks the same way once a step is chosen.
export function ticksAtStep(min: number, max: number, step: number): number[] {
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return ticks;
}

// Thins a sorted array down to ~targetCount evenly-spaced entries (always
// keeping the last one), for x-axis labels on charts where every date would
// otherwise crowd the axis.
export function downsampleDates<T>(items: T[], targetCount = 5): T[] {
  if (!items.length) return [];
  if (items.length <= targetCount + 1) return items;
  const step = Math.floor(items.length / targetCount);
  const picked: T[] = [];
  for (let i = 0; i < items.length; i += step) picked.push(items[i]);
  if (picked[picked.length - 1] !== items[items.length - 1]) picked.push(items[items.length - 1]);
  return picked;
}

// Binary-search for the item whose `time` is closest to `targetTime`, used
// by every chart's hover/tooltip handler to find the nearest data point
// under the pointer without scanning every point on each pointermove.
export function bisectNearest<T>(items: T[], time: (d: T) => number, targetTime: number): T | undefined {
  if (!items.length) return undefined;
  const bisect = bisector(time).left;
  const idx = bisect(items, targetTime);
  const before = items[idx - 1];
  const after = items[idx];
  if (before === undefined) return after;
  if (after === undefined) return before;
  return Math.abs(time(before) - targetTime) <= Math.abs(time(after) - targetTime) ? before : after;
}

// Beyond a normal weekend (3 days) plus a little slack for a weekday holiday
// next to it (4 days), a gap this wide likely means missing/failed scrapes
// rather than an expected closure — connecting a line straight across it, or
// counting it as a single-day move, would treat days we know nothing about
// as if they were a smooth/instant transition.
export const MAX_CONNECTED_GAP_DAYS = 4;
const MS_PER_DAY = 86_400_000;

export function daysBetween(a: string, b: string): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / MS_PER_DAY);
}

// Splits a date-sorted array into runs with no gap wider than maxGapDays —
// used to break a line (and skip spike/delta detection) across genuine gaps
// while still connecting normal weekend/holiday closures.
export function splitByGap<T extends { date: string }>(sorted: T[], maxGapDays = MAX_CONNECTED_GAP_DAYS): T[][] {
  const segments: T[][] = [];
  for (const p of sorted) {
    const current = segments[segments.length - 1];
    if (current && daysBetween(current[current.length - 1].date, p.date) <= maxGapDays) {
      current.push(p);
    } else {
      segments.push([p]);
    }
  }
  return segments;
}
