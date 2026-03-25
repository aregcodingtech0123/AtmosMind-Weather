import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function WindChillGuide() {
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmindweather.com/' },
      { '@type': 'ListItem', position: 2, name: 'Weather Guides', item: 'https://atmosmindweather.com/guides' },
      { '@type': 'ListItem', position: 3, name: 'Wind Chill Guide', item: 'https://atmosmindweather.com/guides/wind-chill' },
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
        title="Wind Chill Guide: Why Wind Feels Colder | AtmosMind"
        description="Understand wind chill, when it matters, and how to dress for windy cold weather. Practical planning tips for commuting, travel, and outdoor time."
        path="/guides/wind-chill"
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
            Wind Chill Guide: the “feels colder” effect
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>
              Wind chill describes how cold conditions feel on exposed skin when wind increases heat
              loss. The air temperature is one part of the story; your body constantly warms a thin
              layer of air next to your skin. Wind disrupts that warm layer, replacing it with colder
              air and accelerating heat transfer. The result is a faster rate of cooling, which your
              nervous system interprets as “colder,” even though the thermometer did not change.
            </p>

            <p>
              A key point: wind chill is most relevant when temperatures are cool to cold, typically
              below about 10°C, and especially near or below freezing. In warm weather, wind does not
              create wind chill in the same way—it can still feel cooler, but the risk profile is
              different. Wind chill formulas estimate equivalent cooling on bare skin, not what a
              jacket or insulated clothing will feel like. Think of it as guidance for exposure risk
              and comfort, not a precise temperature measurement.
            </p>

            <p>
              For daily planning, wind chill affects how you dress and how long you can stay outside.
              If the air temperature is -2°C and the wind is strong, your face and hands can lose heat
              quickly. That is why wind protection often matters more than adding a thicker sweater.
              A wind-resistant outer layer blocks convection, allowing your inner insulation to do its
              job. If you feel cold even with warm clothing, check whether your outer layer is
              windproof and whether gaps at the neck, cuffs, or waist are letting wind in.
            </p>

            <p>
              Wind also increases the risk of frostbite in very cold conditions because exposed skin
              cools faster. Even moderate wind can shorten safe exposure times. Protecting extremities
              is the priority: gloves or mittens, a hat, and a face covering when needed. For commuting,
              plan for wind at bridges, open areas, or coastal streets where gusts can be much stronger
              than sheltered readings.
            </p>

            <p>
              Use wind chill as an action trigger. If wind speeds are high and temperatures are low,
              choose layers that combine insulation with wind protection, and consider warming breaks.
              If your plans involve long outdoor time, the “feels like” value is often more practical
              than the raw temperature. In other words, wind chill isn’t just a number—it’s a hint that
              the environment can pull heat from you faster than you expect.
            </p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

