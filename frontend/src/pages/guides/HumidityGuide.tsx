import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function HumidityGuide() {
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmindweather.com/' },
      { '@type': 'ListItem', position: 2, name: 'Weather Guides', item: 'https://atmosmindweather.com/guides' },
      { '@type': 'ListItem', position: 3, name: 'Humidity Guide', item: 'https://atmosmindweather.com/guides/humidity' },
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
        title="Humidity Explained: Comfort, Dew Point, and Health | AtmosMind"
        description="A practical humidity guide: relative humidity vs dew point, why humid air feels hotter, and how to plan for comfort, sleep, and outdoor activities."
        path="/guides/humidity"
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
            Humidity Guide: What it means and why it matters
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>
              Humidity is one of the most misunderstood weather numbers. Two cities can show the same
              temperature, yet feel completely different: one crisp and comfortable, the other sticky
              and exhausting. The reason is moisture in the air. When we talk about humidity, we are
              usually seeing <strong>relative humidity</strong> (RH), expressed as a percentage. RH is
              not “how much water is in the air” by itself—it is how close the air is to being saturated
              at the current temperature. Warm air can hold more water vapor than cold air, so the same
              amount of moisture can produce very different RH values as the temperature changes.
            </p>

            <p>
              Because RH depends on temperature, the best “how it feels” companion metric is often the{' '}
              <strong>dew point</strong>. Dew point is the temperature at which the air becomes saturated
              and condensation begins. Higher dew points mean more water vapor in the air. As a practical
              rule of thumb: dew points below about 10°C feel dry and comfortable; 10–16°C feel pleasant;
              16–20°C can feel noticeably humid; above 20°C often feels muggy, and above 24°C can feel
              oppressive for many people. If your weather app shows only RH, combine it with temperature:
              70% RH at 10°C is not the same experience as 70% RH at 30°C.
            </p>

            <p>
              Humidity also affects your body’s ability to cool itself. Sweating works by evaporation.
              When the air is already full of moisture, sweat evaporates more slowly, so you retain more
              heat. That is why humid days can feel hotter than the thermometer suggests, and why “feels
              like” temperatures often rise during muggy conditions. For exercise and outdoor work, high
              humidity increases perceived exertion and can raise the risk of heat stress. Plan breaks,
              hydration, and shade more aggressively on high-dew-point days.
            </p>

            <p>
              Indoors, humidity influences sleep quality, allergies, and even how a room smells. Very
              low humidity can dry out skin and airways, while very high humidity supports mold growth.
              Many homes target an indoor RH around 40–60% for a balance of comfort and health. In cold
              climates, keeping indoor humidity too high can cause condensation on windows. In hot
              climates, dehumidification can dramatically improve comfort even without lowering the
              temperature much.
            </p>

            <p>
              When using AtmosMind, treat humidity as an action signal. If humidity is high and
              temperatures are warm, prioritize breathable clothing, avoid heavy midday activity, and
              consider a slower pace. If humidity is low, protect your skin and lips, and stay mindful
              of dehydration—dry air can mask how much fluid you are losing. In short: humidity is not
              just a number; it is a key driver of comfort, safety, and daily planning.
            </p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

