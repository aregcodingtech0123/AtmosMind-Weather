import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Custom hook to automatically scroll to top when route changes.
 * Skips initial render to avoid jarring scroll on first load.
 *
 * @param behavior - Scroll behavior: 'smooth' for animated, 'auto' for instant
 * 
 * Usage:
 *   useScrollToTop('smooth');
 */
export const useScrollToTop = (behavior: ScrollBehavior = 'auto'): void => {
  const { pathname } = useLocation();
  const previousPathRef = useRef<string | null>(null);

  useEffect(() => {
    // Skip scroll on first load (initialization)
    if (previousPathRef.current === null) {
      previousPathRef.current = pathname;
      return;
    }

    // Only scroll when path actually changes
    if (previousPathRef.current !== pathname) {
      window.scrollTo({ top: 0, left: 0, behavior });
      previousPathRef.current = pathname;
    }
  }, [pathname, behavior]);
};
