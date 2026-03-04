import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCount(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, Math.floor(value)).toLocaleString();
  }

  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return Math.max(0, Math.floor(parsed)).toLocaleString();
    }
  }

  return '0';
}
