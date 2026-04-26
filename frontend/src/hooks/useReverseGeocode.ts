import { useEffect, useRef } from 'react';
import { reverseGeocode } from '../services/api';
import { SupportedLanguage } from '../context/SettingsContext';

/**
 * Custom hook to reverse geocode coordinates and return the city name.
 *
 * Handles coordinate-to-city-name conversion with fallback mechanism.
 * Automatically updates when coordinates or language change.
 * Uses a deduplication key to avoid redundant API calls for the same
 * coordinate + language combination.
 *
 * @param latitude - User's latitude or null if not available
 * @param longitude - User's longitude or null if not available
 * @param language - Current UI language for localized results
 * @param onLocationNameResolved - Callback when city name is successfully resolved
 * @param fallbackName - Fallback name if reverse geocoding fails (e.g., "Current Location")
 *
 * Usage:
 *   useReverseGeocode(lat, lng, language, (name) => setLocation(name), "Current Location")
 */
export const useReverseGeocode = (
  latitude: number | null,
  longitude: number | null,
  language: SupportedLanguage,
  onLocationNameResolved: (name: string) => void,
  fallbackName: string = 'Current Location'
): void => {
  // Track the last resolved key to avoid duplicate calls
  const lastKeyRef = useRef<string>('');
  // Track whether a request is in flight
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Exit early if coordinates are not available
    if (latitude == null || longitude == null) {
      return;
    }

    // Build deduplication key (round to 4 decimal places ≈ 11m accuracy)
    const key = `${latitude.toFixed(4)}_${longitude.toFixed(4)}_${language}`;

    // Skip if we already resolved this exact coordinate + language combo
    if (key === lastKeyRef.current) {
      return;
    }

    // Cancel any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const performReverseGeocode = async () => {
      try {
        const result = await reverseGeocode(latitude, longitude, language);

        // If this request was aborted, don't update state
        if (controller.signal.aborted) return;

        // Build location name with country/state info
        if (result?.name) {
          const parts = [result.name];

          // Add state/province if different from name
          if (result.admin1 && result.admin1 !== result.name) {
            parts.push(result.admin1);
          }

          // Add country
          if (result.country) {
            parts.push(result.country);
          } else if (result.country_code) {
            parts.push(result.country_code);
          }

          const localizedLocationName = parts.join(', ');
          lastKeyRef.current = key;
          onLocationNameResolved(localizedLocationName);
        } else {
          // Fallback: Use provided fallback name if result is empty
          lastKeyRef.current = key;
          onLocationNameResolved(fallbackName);
        }
      } catch (error) {
        // Don't report aborted requests
        if (controller.signal.aborted) return;

        // Fallback: Use provided fallback name on error
        console.warn(`Reverse geocoding failed for [${latitude}, ${longitude}]:`, error);
        lastKeyRef.current = key;
        onLocationNameResolved(fallbackName);
      }
    };

    performReverseGeocode();

    return () => {
      controller.abort();
    };
    // Note: onLocationNameResolved and fallbackName are intentionally excluded
    // from deps to prevent infinite re-render loops. The hook only re-fires
    // when coordinates or language change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latitude, longitude, language]);
};
