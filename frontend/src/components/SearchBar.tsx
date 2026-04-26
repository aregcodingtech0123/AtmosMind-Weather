import React, { useState, useRef, useEffect, useCallback, useMemo, useId } from 'react';
import { Search, MapPin, Loader2 } from 'lucide-react';
import { cn } from '../utils/cn';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useSettings } from '../context/SettingsContext';
import { geocodeCity, GeoSearchResult } from '../services/api';

// ─── Constants ───────────────────────────────────────────────────────────────
const DEBOUNCE_MS = 300;   // Wait briefly after typing before hitting the API
const MIN_CHARS = 3;     // Don't fetch until the user has typed at least 3 characters
const MAX_CACHE = 200;   // Evict oldest entries after this many unique queries

export interface Suggestion {
  name: string;
  lat: number;
  lon: number;
  country?: string;
  state?: string;
  population?: number;
}

// ─── In-memory LRU-ish cache (Map preserves insertion order) ─────────────────
// Key: lowercase trimmed query string  →  Value: Suggestion[] suggestions
const suggestionCache = new Map<string, Suggestion[]>();

function cacheGet(key: string): Suggestion[] | undefined {
  return suggestionCache.get(key);
}

function cacheSet(key: string, value: Suggestion[]): void {
  // Simple eviction: drop the oldest entry when we hit MAX_CACHE
  if (suggestionCache.size >= MAX_CACHE) {
    const firstKey = suggestionCache.keys().next().value;
    if (firstKey !== undefined) suggestionCache.delete(firstKey);
  }
  suggestionCache.set(key, value);
}

function processAndFilterResults(items: GeoSearchResult[]): Suggestion[] {
  // 2. Hard Filtering for Residential Areas
  const allowedFeatureCodes = ['PPL', 'PPLC', 'PPLA', 'PPLA2', 'PPLA3'];
  const forbiddenKeywords = ['AIRP', 'RSTN', 'MT', 'POST'];

  const filteredItems = items.filter(item => {
    const code = (item.feature_code || '').toUpperCase();
    if (forbiddenKeywords.some(fk => code.includes(fk))) {
      return false;
    }
    // Explicitly discard any result that is not a populated place
    if (!allowedFeatureCodes.includes(code)) {
      return false;
    }
    return true;
  });

  // 1. Strict Deduplication (Logic Upgrade)
  const uniqueMap = new Map<string, GeoSearchResult>();
  for (const item of filteredItems) {
    const uniqueKey = `${item.name}-${item.admin1 || ''}-${item.country_code || ''}`.toLowerCase().trim();

    const existing = uniqueMap.get(uniqueKey);
    const currentPop = item.population || 0;
    const existingPop = existing?.population || 0;

    // Priority Rule: If duplicates exist, keep the one with the highest population.
    if (!existing || currentPop > existingPop) {
      uniqueMap.set(uniqueKey, item);
    }
  }

  // 4. Data Formatting & Conversion
  const finalResults: Suggestion[] = Array.from(uniqueMap.values())
    .map(item => {
      const parts = [item.name];
      // If admin1 (state/province) is identical to name, don't show it twice.
      if (item.admin1 && item.admin1 !== item.name) {
        parts.push(item.admin1);
      }
      if (item.country) {
        parts.push(item.country);
      } else if (item.country_code) {
        parts.push(item.country_code);
      }

      return {
        name: parts.join(', '),
        // Map from GeoSearchResult properties to Suggestion properties
        lat: item.latitude,
        lon: item.longitude,
        country: item.country || item.country_code,
        state: item.admin1,
        population: item.population || 0
      };
    })
    .sort((a, b) => (b.population || 0) - (a.population || 0)); // Priority Ranking

  // 5. Debugging
  console.log("Filtered Results:", finalResults);

  return finalResults;
}

// ─── Component ────────────────────────────────────────────────────────────────
interface SearchBarProps {
  onSearch: (cityName: string, lat: number, lng: number) => void;
  onLocationRequest: () => void;
  locationLoading?: boolean;
  /** Merged onto the outer wrapper (width / shrink in flex layouts) */
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onLocationRequest,
  locationLoading = false,
  className,
}) => {
  const { t } = useTranslation();
  const { currentLanguage } = useSettings();
  const searchId = useId();
  const listboxId = `${searchId}-suggestions`;
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [rawSuggestions, setRawSuggestions] = useState<Suggestion[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  // Holds the pending debounce timer so we can clear it on each new keystroke
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Holds the latest fetch AbortController so we can cancel in-flight requests
  const controllerRef = useRef<AbortController | null>(null);

  // ── Fetch suggestions from backend ─────────────────────────────────────────
  const fetchSuggestions = useCallback(async (q: string) => {
    // Cache key includes the language so switching UI language invalidates stale
    // entries and fetches fresh, correctly-localized results.
    const cacheKey = `${q.toLocaleLowerCase(currentLanguage)}::${currentLanguage}`;

    // 1️⃣  Cache hit — return immediately, zero network cost
    const cached = cacheGet(cacheKey);
    if (cached) {
      setRawSuggestions(cached);
      return;
    }

    // 2️⃣  Cancel any previous in-flight request
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsSearching(true);
    try {
      // Fetch more than needed so we have enough after strict filtering
      const rawData = await geocodeCity(q, currentLanguage, 20);
      const processedResults = processAndFilterResults(rawData).slice(0, 8); // Keep top 8

      cacheSet(cacheKey, processedResults);   // store in cache for future keystrokes
      setRawSuggestions(processedResults);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setRawSuggestions([]);
      }
      // AbortErrors are intentional — silently ignore them
    } finally {
      setIsSearching(false);
    }
  }, [currentLanguage]);

  // ── Debounced effect: fires 250 ms after the query stops changing ───────────
  useEffect(() => {
    const trimmed = query.trim();

    // Guard: clear list if query too short
    if (trimmed.length < MIN_CHARS) {
      setRawSuggestions([]);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (controllerRef.current) controllerRef.current.abort();
      return;
    }

    // Clear the previous timer on every new keystroke
    if (debounceRef.current) clearTimeout(debounceRef.current);

    // Check cache synchronously — if hit, show instantly without even waiting
    // Cache key includes language to avoid returning stale English entries
    // after the user switches UI language.
    const cacheKey = `${trimmed.toLocaleLowerCase(currentLanguage)}::${currentLanguage}`;
    if (cacheGet(cacheKey)) {
      setRawSuggestions(cacheGet(cacheKey)!);
      return;
    }

    // Schedule the network call after DEBOUNCE_MS of silence
    debounceRef.current = setTimeout(() => {
      fetchSuggestions(trimmed);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchSuggestions, currentLanguage]);

  // We already deduplicated, sorted, and formatted during fetch.
  const suggestions = rawSuggestions;

  // ── Click-outside handler to close dropdown ─────────────────────────────────
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        dropdownRef.current && !dropdownRef.current.contains(target) &&
        inputRef.current && !inputRef.current.contains(target)
      ) {
        setIsFocused(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Resolve city name / handle Enter with no explicit selection ────────────
  // Prefer already-loaded suggestion[0] so no redundant API call is needed and
  // the user sees the exact localized label visible in the dropdown.
  // Fallback: geocode the raw query with the active UI language so multilingual
  // inputs like "Münih" or "中文" resolve to the correct city.
  const runSearch = useCallback(async (fullNameOrQuery: string) => {
    if (suggestions.length > 0) {
      handleSelect(suggestions[0]);
      return;
    }

    const rawQuery = fullNameOrQuery.trim();
    if (!rawQuery) return;

    const displayName = rawQuery.split(',')[0].trim();
    setQuery(displayName);
    setRawSuggestions([]);
    setIsFocused(false);

    try {
      const results = await geocodeCity(rawQuery, currentLanguage, 10);
      const pplResults = processAndFilterResults(results);
      const best = pplResults[0];
      if (best) onSearch(displayName, best.lat, best.lon);
    } catch {
      // Non-fatal: geocoding errors don't break the UI
    }
  }, [suggestions, currentLanguage, onSearch]);


  const handleSelect = (suggestion: Suggestion) => {
    const baseName = suggestion.name.split(',')[0].trim();
    setQuery(baseName);
    setRawSuggestions([]);
    setIsFocused(false);
    onSearch(baseName, suggestion.lat, suggestion.lon);
  };

  const triggerSearch = useCallback(() => {
    if (suggestions.length > 0) { handleSelect(suggestions[0]); return; }
    if (query.trim()) { runSearch(query.trim()); return; }
  }, [suggestions, query, runSearch]);

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); triggerSearch(); };

  // Explicit Enter handler — needed for CJK/IME keyboards where the form submit
  // may not fire reliably during composition.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
      e.preventDefault();
      triggerSearch();
    }
  };

  const showDropdown = isFocused && suggestions.length > 0;

  return (
    <div className={cn('relative z-10 w-full min-w-0 shrink', className)}>
      <form onSubmit={handleSubmit} className="block w-full">
        <div
          className={cn(
            'flex items-center gap-3',
            'bg-black/20 backdrop-blur-md border border-white/10',
            'rounded-full px-5 py-3',
            'transition-all duration-300',
            isFocused && 'bg-black/30 border-white/30 shadow-lg'
          )}
        >
          {/* Search / loading icon */}
          <button
            type="button"
            onClick={triggerSearch}
            className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-white/20 active:scale-95 focus:outline-none focus:ring-2 focus:ring-white/60 cursor-pointer"
            aria-label={String(t('search.searchCity'))}
          >
            {isSearching ? (
              <Loader2 className="w-5 h-5 text-white/60 animate-spin" strokeWidth={1.5} aria-hidden />
            ) : (
              <Search className="w-5 h-5 text-white/60" strokeWidth={1.5} aria-hidden />
            )}
          </button>

          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onKeyDown={handleKeyDown}
            placeholder={String(t('search.placeholder'))}
            autoComplete="off"
            spellCheck={false}
            role="combobox"
            aria-label={String(t('search.searchForCity'))}
            aria-autocomplete="list"
            aria-controls={showDropdown ? listboxId : undefined}
            aria-expanded={showDropdown}
            className="flex-1 bg-transparent text-white placeholder:text-white/50 outline-none text-base"
            data-testid="search-input"
          />

          {/* Geolocation button */}
          <button
            type="button"
            onClick={onLocationRequest}
            disabled={locationLoading}
            className={cn(
              'p-2 rounded-full transition-all duration-200',
              'hover:bg-white/20 active:scale-95',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            title={String(t('search.useMyLocation'))}
            aria-label={String(t('search.useMyCurrentLocation'))}
            data-testid="location-button"
          >
            {locationLoading ? (
              <Loader2 className="w-5 h-5 text-white/80 animate-spin" strokeWidth={1.5} aria-hidden />
            ) : (
              <MapPin className="w-5 h-5 text-white/80" strokeWidth={1.5} aria-hidden />
            )}
          </button>
        </div>
      </form>

      {/* ── Suggestions dropdown ─────────────────────────────────────────── */}
      <AnimatePresence>
        {showDropdown && (
          <motion.div
            ref={dropdownRef}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className={cn(
              'absolute top-full left-0 right-0 mt-2 z-50',
              'bg-black/60 backdrop-blur-xl border border-white/10',
              'rounded-2xl overflow-hidden shadow-xl'
            )}
            id={listboxId}
            role="listbox"
            aria-label={String(t('search.citySuggestions'))}
            data-testid="search-suggestions"
          >
            {suggestions.map((city, index) => (
              <button
                key={`${city.name}-${city.lat}-${city.lon}`}
                role="option"
                aria-selected={false}
                onClick={() => handleSelect(city)}
                className={cn(
                  'w-full px-5 py-3 text-left text-white',
                  'hover:bg-white/10 transition-colors duration-150',
                  index !== suggestions.length - 1 && 'border-b border-white/5'
                )}
                data-testid={`suggestion-${city.name.toLocaleLowerCase(currentLanguage).replace(/\s/g, '-')}`}
              >
                <div className="flex items-center gap-3">
                  <MapPin className="w-4 h-4 text-white/50 flex-shrink-0" strokeWidth={1.5} aria-hidden />
                  <span>{city.name}</span>
                </div>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
