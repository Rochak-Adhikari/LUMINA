// frontend/utils/cn.js — className combiner (clsx + tailwind-merge)
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default cn;
