import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function WhatToWearGuide() {
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmindweather.com/' },
      { '@type': 'ListItem', position: 2, name: 'Weather Guides', item: 'https://atmosmindweather.com/guides' },
      { '@type': 'ListItem', position: 3, name: 'What to Wear', item: 'https://atmosmindweather.com/guides/what-to-wear' },
    ],
  };

  const handleSearch = useCallback((cityName: string, lat: number, lng: number) => {
    const encoded = encodeURIComponent(cityName);
    navigate(`/weather/${encoded}`, { state: { cityName, latitude: lat, longitude: lng } });
  }, [navigate]);

  const handleLocationRequest = useCallback(() => {
    navigate('/');
  }, [navigate]);

  return (
    <div
      className={cn(
        'min-h-screen transition-all duration-700 ease-in-out',
        'bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950',
        'text-white'
      )}
    >
      <Seo
        title="What to Wear by Temperature (and Wind/Rain) | AtmosMind"
        description="A practical clothing guide by temperature bands, with adjustments for wind, rain, and humidity. Build comfortable outfits for commuting and travel."
        path="/guides/what-to-wear"
        structuredData={breadcrumbSchema}
      />

      <div className="w-full px-4 pt-10 sm:px-5 md:px-8 lg:px-12">
        <Navbar onSearch={handleSearch} onLocationRequest={handleLocationRequest} />
      </div>

      <div className="max-w-5xl mx-auto px-4 pb-10 sm:px-5 md:px-8 lg:px-12">
        <motion.main
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className={cn(
            'rounded-3xl border border-white/10 bg-black/30 backdrop-blur-md',
            'px-6 py-8 md:px-10 md:py-10'
          )}
        >
          <h1 className="text-3xl md:text-4xl font-semibold text-white/90 font-heading mb-6">
            What to Wear Guide: temperature, wind, rain, and comfort
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>
              “What should I wear today?” is the most practical weather question. A single temperature
              is not enough—wind, humidity, precipitation, and how long you will be outside can change
              the best choice. A good outfit strategy starts with a simple system: a breathable base
              layer, optional insulation, and a protective outer layer for wind and rain. With this
              approach you can adapt quickly as conditions shift through the day.
            </p>

            <p>
              Here are useful temperature bands for most people, assuming light wind and no rain. Above
              25°C: prioritize lightweight, breathable fabrics and sun protection. 18–25°C: a t-shirt
              or light top is often enough; carry a thin layer if evenings cool down. 12–18°C: long
              sleeves or a light jacket becomes comfortable, especially in shade. 5–12°C: add a warmer
              mid-layer (sweater or fleece) and consider a wind-resistant jacket. 0–5°C: insulation
              matters; combine a warm mid-layer with a windproof shell, plus a hat. Below 0°C: aim for
              layered insulation, gloves, and a scarf or neck gaiter—exposed skin cools quickly.
            </p>

            <p>
              Now adjust for conditions. Wind increases heat loss; if it is breezy, treat the day as a
              few degrees colder and use a wind-resistant outer layer. Humidity changes perceived heat:
              high humidity in warm weather makes it feel hotter, so choose moisture-wicking fabrics and
              plan hydration. Rain changes everything: even a light drizzle can make cool temperatures
              feel uncomfortable. If there is any chance of rain, prioritize a packable waterproof shell
              or umbrella. Wet clothing loses insulation and can be dangerous in cold conditions.
            </p>

            <p>
              For commuting and travel, “time outside” is the hidden variable. A 5-minute walk is very
              different from a 45-minute outdoor errand. If you will be outside longer, dress for the
              worst part of the day and build in ventilation options (zippers, removable layers). If you
              transition between indoors and outdoors, avoid overheating: too much insulation can make
              you sweat, and sweat can cool you later when you step back outside.
            </p>

            <p>
              Finally, consider footwear. In rain or snow, waterproof shoes and traction are more
              important than an extra sweater. In hot weather, breathable shoes reduce discomfort. A
              small checklist works well: temperature band, wind, rain chance, and planned time outside.
              Use AtmosMind’s forecasts and AI insights to refine these choices, but keep the layering
              system as your reliable baseline.
            </p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

