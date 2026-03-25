import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function ThunderstormSafety() {
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmindweather.com/' },
      { '@type': 'ListItem', position: 2, name: 'Weather Guides', item: 'https://atmosmindweather.com/guides' },
      { '@type': 'ListItem', position: 3, name: 'Thunderstorm Safety', item: 'https://atmosmindweather.com/guides/thunderstorm-safety' },
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
        title="Thunderstorm Safety: Lightning, Wind, and Flooding | AtmosMind"
        description="A practical thunderstorm safety guide: lightning precautions, what to avoid outdoors, and how to plan for gusts, hail, and flash flooding."
        path="/guides/thunderstorm-safety"
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
            Thunderstorm Safety Guide
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>
              Thunderstorms can develop quickly and bring multiple hazards at once: lightning, sudden
              wind gusts, heavy rain, hail, and localized flooding. The safest strategy is to treat a
              thunderstorm forecast as a planning signal. If you have outdoor activities, commuting by
              bike or scooter, or travel plans, look at timing and intensity and choose safer windows
              for movement. A few minutes of preparation can prevent hours of disruption or serious risk.
            </p>

            <p>
              Lightning is the most dangerous thunderstorm hazard for people outdoors. If you can hear
              thunder, you are close enough to be struck by lightning. Move to a substantial building or
              a fully enclosed metal vehicle. Avoid open fields, hilltops, isolated trees, and water. If
              you cannot reach shelter, minimize your exposure: spread out from others, avoid being the
              tallest object, and move away from metal fences or poles. Do not lie flat; instead, reduce
              contact with the ground and protect your head.
            </p>

            <p>
              Wind and hail can cause injuries and property damage. Secure loose items (balcony furniture,
              lightweight planters, outdoor decorations) before storms arrive. When gusts are expected,
              avoid parking under trees and keep distance from weak branches. Hail can shatter windows and
              damage vehicles; if hail is possible, prioritize covered parking or indoor shelter. For
              pedestrians, a hard surface like a helmet or bag can provide limited protection while you
              move quickly toward shelter.
            </p>

            <p>
              Heavy rain can produce flash flooding even if the broader forecast looks moderate. Flooding
              is most dangerous in underpasses, low-lying streets, and small streams. Never drive through
              flooded roads; water depth and current are hard to judge and can move a vehicle. If you are
              on foot, avoid walking through fast-moving water. In urban areas, drainage can be overwhelmed
              quickly, so treat intense rainfall as a reason to delay travel when possible.
            </p>

            <p>
              After a storm passes, hazards may remain. Downed lines, debris, and slippery surfaces are
              common. Use a cautious route and watch for updated alerts. Thunderstorms are a normal part
              of weather, but the best outcomes come from simple rules: seek shelter early, respect wind
              and water, and adjust your plans rather than trying to “push through.” AtmosMind’s forecasts
              and insights can help you time your day to stay safe and comfortable.
            </p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

