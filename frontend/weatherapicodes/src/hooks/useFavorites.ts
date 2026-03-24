import { useState, useEffect, useCallback } from 'react';
import { FavoriteCity } from '../types/weather';
import { useSettings } from '../context/SettingsContext';
import { reverseGeocode } from '../services/api';

const STORAGE_KEY = 'weather-favorites';

interface UseFavoritesReturn {
  favorites: FavoriteCity[];
  addFavorite: (city: FavoriteCity) => void;
  removeFavorite: (cityId: string) => void;
  isFavorite: (latitude: number, longitude: number) => boolean;
}

export const useFavorites = (): UseFavoritesReturn => {
  const { currentLanguage } = useSettings();
  const [favorites, setFavorites] = useState<FavoriteCity[]>([]);

  // Load favorites from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as FavoriteCity[];
        const migrated = parsed.map((city) => {
          const id = city.id ?? `${Number(city.latitude).toFixed(4)},${Number(city.longitude).toFixed(4)}`;
          const namesByLanguage = city.namesByLanguage ?? { en: city.name };
          return { ...city, id, namesByLanguage };
        });
        setFavorites(migrated);
      }
    } catch (error) {
      console.error('Error loading favorites:', error);
    }
  }, []);

  // Save favorites to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
    } catch (error) {
      console.error('Error saving favorites:', error);
    }
  }, [favorites]);

  const addFavorite = useCallback((city: FavoriteCity) => {
    setFavorites(prev => {
      if (prev.some(c => c.id === city.id)) {
        return prev;
      }
      return [...prev, city];
    });
  }, []);

  const removeFavorite = useCallback((cityId: string) => {
    setFavorites(prev => 
      prev.filter(c => c.id !== cityId)
    );
  }, []);

  const isFavorite = useCallback((latitude: number, longitude: number) => {
    const id = `${Number(latitude).toFixed(4)},${Number(longitude).toFixed(4)}`;
    return favorites.some(c => c.id === id);
  }, [favorites]);

  useEffect(() => {
    let disposed = false;
    const updates: Promise<void>[] = [];

    favorites.forEach((city) => {
      if (city.namesByLanguage?.[currentLanguage]) return;
      const task = reverseGeocode(city.latitude, city.longitude, currentLanguage)
        .then((result) => {
          const localizedName = result?.name
            ? result.country
              ? `${result.name}, ${result.country}`
              : result.name
            : null;
          if (!localizedName || disposed) return;
          setFavorites((prev) =>
            prev.map((item) =>
              item.id === city.id
                ? {
                    ...item,
                    name: item.namesByLanguage?.[currentLanguage] ?? localizedName,
                    namesByLanguage: {
                      ...(item.namesByLanguage ?? {}),
                      [currentLanguage]: localizedName,
                    },
                  }
                : item
            )
          );
        })
        .catch(() => undefined);
      updates.push(task);
    });

    return () => {
      disposed = true;
    };
  }, [favorites, currentLanguage]);

  return { favorites, addFavorite, removeFavorite, isFavorite };
};
