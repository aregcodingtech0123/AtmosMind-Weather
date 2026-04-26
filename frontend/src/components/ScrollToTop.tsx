import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Global ScrollToTop component.
 *
 * Placed inside BrowserRouter in the root layout, this component
 * forces every page to start at the top (y=0) whenever the pathname
 * changes. It applies globally to ALL routes, including pages outside
 * of App.tsx (e.g. About Us, Contact, Privacy Policy, Guides, etc.).
 *
 * Behaviour:
 *   - Forward navigation (Link clicks, navigate()): scrolls to top instantly.
 *   - Browser back/forward: lets the browser's native scrollRestoration
 *     handle it when possible, but falls back to scrolling to top for
 *     consistency.
 *
 * Usage in index.tsx:
 *   <BrowserRouter>
 *     <ScrollToTop />
 *     <Routes>…</Routes>
 *   </BrowserRouter>
 */
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    // Scroll to top on every pathname change
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
  }, [pathname]);

  return null; // This component does not render anything
}
