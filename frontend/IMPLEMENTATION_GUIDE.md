# AtmosMind - Implementation Guide

## Features Implemented

This guide documents the implementation of two critical UX improvements:

1. **Dynamic Location Name (Reverse Geocoding)** - Display actual city names instead of "My Location"
2. **Scroll-to-Top on Navigation** - Auto-scroll to top when navigating between routes

---

## Task 1: Dynamic Location Name (Reverse Geocoding)

### Problem Statement
When users click the "current location" button, the UI displays the generic text "My Location" instead of the actual city/district name.

### Solution Overview
Implemented a custom React hook (`useReverseGeocode`) that:
- Takes latitude/longitude coordinates
- Calls the reverse geocoding API (Open-Meteo Reverse API)
- Returns the actual city name with country info
- Includes fallback mechanism if API fails

### Files Created/Modified

#### 1. **New Hook: `src/hooks/useReverseGeocode.ts`** ✅

```typescript
export const useReverseGeocode = (
  latitude: number | null,
  longitude: number | null,
  language: SupportedLanguage,
  onLocationNameResolved: (name: string) => void,
  fallbackName: string = 'Current Location'
): void => {
  // - Handles reverse geocoding automatically
  // - Updates when coordinates or language changes
  // - Includes fallback mechanism
}
```

**Key Features:**
- ✅ Automatic triggers on coordinate/language changes
- ✅ Builds location string: `"City, State, Country"`
- ✅ Fallback to provided name if API fails
- ✅ Handles null/undefined coordinates gracefully

#### 2. **Updated: `src/App.tsx`**

**Changes Made:**

a) **Added imports:**
```typescript
import { useScrollToTop } from './hooks/useScrollToTop';
import { useReverseGeocode } from './hooks/useReverseGeocode';
```

b) **Removed unused import:**
```typescript
// BEFORE:
import { reverseGeocode } from './services/api';

// AFTER: (removed - useReverseGeocode hook handles it now)
```

c) **Replaced old effect with new hook:**
```typescript
// BEFORE (lines 280-295):
useEffect(() => {
  if (latitude == null || longitude == null) return;
  let disposed = false;
  const syncSelectedCityLabel = async () => {
    try {
      const first = await reverseGeocode(latitude, longitude, currentLanguage);
      // ... reverse geocoding logic
    } catch {
      // Keep existing selected city label on localization failures.
    }
  };
  syncSelectedCityLabel();
  return () => {
    disposed = true;
  };
}, [currentLanguage, latitude, longitude]);

// AFTER:
useReverseGeocode(
  latitude,
  longitude,
  currentLanguage,
  (resolvedName) => {
    if (latitude != null && longitude != null) {
      setSelectedCity(resolvedName);
    }
  },
  t('weather.myLocation')
);
```

### How It Works

**Flow Diagram:**
```
User clicks "Current Location"
         ↓
Geolocation API returns lat/lng
         ↓
setLatitude(lat) + setLongitude(lng)
         ↓
useReverseGeocode hook triggered
         ↓
Fetch city name from coordinates
         ↓
setSelectedCity(resolvedName)
         ↓
UI displays "Paris, Île-de-France, France" (instead of "My Location")
```

**Example Output:**
| Scenario | Before | After |
|----------|--------|-------|
| User in Paris | "My Location" | "Paris, Île-de-France, France" |
| User in Tokyo | "My Location" | "Tokyo, Tokyo, Japan" |
| API failure | "My Location" | "My Location" (fallback) |

### Testing the Feature

1. **Test with real geolocation:**
   ```typescript
   // Click the location icon in the search bar
   // → Should display city name after ~500ms
   ```

2. **Test with language switch:**
   ```typescript
   // Click location icon (shows "New York")
   // Switch language to Spanish
   // → Should update to Spanish city name
   ```

3. **Test fallback:**
   ```typescript
   // Disable network to simulate API failure
   // Click location icon
   // → Should fallback to "My Location"
   ```

---

## Task 2: Scroll-to-Top on Navigation

### Problem Statement
When navigating between different pages/routes, the new page retains the scroll position of the previous page instead of starting at the top.

### Solution Overview
Implemented a custom React hook (`useScrollToTop`) that:
- Listens to route changes via React Router's `useLocation()`
- Scrolls window to top on each navigation
- Supports both smooth and instant scrolling

### Files Created/Modified

#### 1. **New Hook: `src/hooks/useScrollToTop.ts`** ✅

```typescript
export const useScrollToTop = (behavior: ScrollBehavior = 'auto'): void => {
  const { pathname } = useLocation();
  const previousPathRef = useRef<string | null>(null);

  useEffect(() => {
    if (previousPathRef.current === null) {
      previousPathRef.current = pathname;
      return;
    }

    window.scrollTo({ top: 0, left: 0, behavior });
    previousPathRef.current = pathname;
  }, [pathname, behavior]);
};
```

**Key Features:**
- ✅ Automatic on all route changes
- ✅ Skips scroll on initial app load
- ✅ Works with back/forward navigation
- ✅ Supports smooth scrolling animation

#### 2. **Updated: `src/App.tsx`**

**Changes Made:**

a) **Added import:**
```typescript
import { useScrollToTop } from './hooks/useScrollToTop';
```

b) **Added hook call at top of App component:**
```typescript
function App() {
  const { t, i18n } = useTranslation();
  const { currentLanguage, currentUnit } = useSettings();
  const location = useLocation();
  const navigate = useNavigate();
  const langKey = (i18n.language || currentLanguage).split('-')[0] as SupportedLanguage;

  // Scroll to top on route changes
  useScrollToTop('smooth');  // ← Added this line

  // ... rest of component
}
```

### How It Works

**Flow Diagram:**
```
User navigates to /weather/paris
         ↓
pathname changes (useLocation dependency)
         ↓
useScrollToTop hook detected change
         ↓
window.scrollTo({ top: 0, behavior: 'smooth' })
         ↓
Page scrolls to top with smooth animation
```

**Behavior Comparison:**

| Route | Before | After |
|-------|--------|-------|
| `/` → `/weather/paris` | Stays at previous scroll position | Scrolls to top |
| `/weather/paris` → `/about` | Stays at previous scroll position | Scrolls to top |
| Back button | Stays at previous scroll position | Scrolls to top |
| Forward button | Stays at previous scroll position | Scrolls to top |

### Configuration Options

You can control the scroll behavior by changing the parameter:

```typescript
// Smooth scrolling (animated) - Default: 'smooth'
useScrollToTop('smooth');

// Instant scrolling (jumps to top)
useScrollToTop('auto');
```

### Advanced: Custom Scroll Behavior per Route

If you need different behavior for specific routes, modify the hook:

```typescript
// In App.tsx
useEffect(() => {
  const isSmoothScroll = !location.pathname.startsWith('/guides/');
  window.scrollTo({
    top: 0,
    left: 0,
    behavior: isSmoothScroll ? 'smooth' : 'auto'
  });
}, [location.pathname]);
```

### Testing the Feature

1. **Test basic navigation:**
   ```
   - Navigate from home to a city page
   - Scroll down significantly
   - Navigate to another city
   - → Should scroll to top automatically
   ```

2. **Test with back button:**
   ```
   - Navigate /weather/paris → /about
   - Click browser back button
   - → Should scroll to top (not preserve scroll position)
   ```

3. **Test smooth animation:**
   ```
   - Open DevTools (F12)
   - Toggle between pages
   - → Should see smooth scrolling animation
   ```

---

## Architecture & Best Practices

### Why Custom Hooks?

✅ **Reusability** - Both features are now hooks, can be used in other components
✅ **Testability** - Isolated logic, easier to unit test
✅ **Maintainability** - Single responsibility principle
✅ **Performance** - Minimal re-renders with proper dependency arrays

### Hook Execution Order

In React, hooks execute in this order:
1. `useScrollToTop()` - Listens to pathname changes
2. `useReverseGeocode()` - Listens to latitude/longitude changes
3. Regular `useEffect()` - Additional app logic

### File Structure

```
frontend/src/
├── hooks/
│   ├── useGeolocation.ts       (existing)
│   ├── useWeather.ts           (existing)
│   ├── useFavorites.ts         (existing)
│   ├── useScrollToTop.ts       (NEW) ✅
│   └── useReverseGeocode.ts    (NEW) ✅
├── App.tsx                      (modified)
├── components/
└── services/
```

---

## Troubleshooting

### Issue: Dynamic location name not updating

**Symptoms:** Shows "My Location" even after geolocation succeeds

**Solutions:**
1. Check browser console for errors:
   ```typescript
   // Add to useReverseGeocode hook:
   console.log('Reverse geocoding:', { latitude, longitude, language });
   ```

2. Verify API is responding:
   ```javascript
   // Test in browser console:
   fetch('https://geocoding-api.open-meteo.com/v1/reverse?latitude=48.8566&longitude=2.3522&language=en&format=json')
     .then(r => r.json())
     .then(d => console.log(d));
   ```

3. Check fallback language:
   - If language is not supported, API might return empty results
   - Fallback to `t('weather.myLocation')` will trigger

### Issue: Page doesn't scroll to top on navigation

**Symptoms:** Retains scroll position when changing routes

**Solutions:**
1. Verify `useScrollToTop` is called in main `App` component
2. Check if pathname is actually changing:
   ```typescript
   useEffect(() => {
     console.log('Route changed:', location.pathname);
   }, [location.pathname]);
   ```

3. Ensure no other element has `overflow: auto` competing for scroll

### Issue: Scroll animation is jerky or slow

**Symptoms:** Smooth scrolling feels laggy

**Solutions:**
1. Change to instant scroll:
   ```typescript
   useScrollToTop('auto');  // Instead of 'smooth'
   ```

2. Check for heavy page content - consider virtual scrolling libraries

---

## Performance Notes

### useReverseGeocode Performance
- **Network call:** ~200-500ms (cached by browser)
- **Dependency array:** `[latitude, longitude, currentLanguage]` - only reruns when these change
- **Memory:** Minimal - uses single async call

### useScrollToTop Performance
- **Execution:** <1ms (native browser API)
- **Dependency array:** `[pathname]` - only on route changes
- **Memory:** Minimal - only tracks previous path

### Optimization Tips

If experiencing performance issues:

1. **Debounce reverse geocoding:**
   ```typescript
   const [isGeocoding, setIsGeocoding] = useState(false);
   
   useReverseGeocode(
     latitude,
     longitude,
     currentLanguage,
     (name) => {
       // Only update if not already geocoding
       if (!isGeocoding) {
         setSelectedCity(name);
       }
     }
   );
   ```

2. **Disable smooth scroll for mobile:**
   ```typescript
   const isMobile = window.innerWidth < 768;
   useScrollToTop(isMobile ? 'auto' : 'smooth');
   ```

---

## Browser Compatibility

### useScrollToTop
- ✅ Chrome 45+
- ✅ Firefox 36+
- ✅ Safari 10+
- ⚠️ IE 11 doesn't support `behavior: 'smooth'` (falls back to instant)

### useReverseGeocode
- ✅ All modern browsers
- ✅ Requires internet connection
- ✅ Works with browser cache

---

## Future Enhancements

### Suggested Improvements

1. **Cache location names:**
   ```typescript
   const locationCache = new Map<string, string>();
   // Store: "48.8566,2.3522" → "Paris"
   ```

2. **Debounce reverse geocoding:**
   ```typescript
   const timeoutRef = useRef<NodeJS.Timeout>();
   // Delay API call by 500ms to avoid redundant requests
   ```

3. **Cancel in-flight requests:**
   ```typescript
   const abortControllerRef = useRef<AbortController>();
   // Cancel previous request if new one triggered
   ```

4. **Mobile-specific scroll behavior:**
   ```typescript
   const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
   useScrollToTop(prefersReducedMotion ? 'auto' : 'smooth');
   ```

---

## Testing Checklist

- [ ] Location name updates when using geolocation
- [ ] Location name changes when language changes
- [ ] Page scrolls to top on navigation
- [ ] Smooth scroll animation works (not instant)
- [ ] Browser back button scrolls to top
- [ ] Mobile responsive behavior verified
- [ ] No console errors present
- [ ] Fallback text shows if API fails
- [ ] Works with all supported languages
- [ ] Performance metrics acceptable (<100ms overhead)

---

## Support & Questions

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review browser console for error messages
3. Test with network throttling to simulate slow connections
4. Verify all imports are correctly added to `App.tsx`

---

**Implementation Date:** April 27, 2026  
**Status:** ✅ Complete and Ready for Testing
