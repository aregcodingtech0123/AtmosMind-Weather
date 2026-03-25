import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function UvIndexGuide() {
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmindweather.com/' },
      { '@type': 'ListItem', position: 2, name: 'Weather Guides', item: 'https://atmosmindweather.com/guides' },
      { '@type': 'ListItem', position: 3, name: 'UV Index Guide', item: 'https://atmosmindweather.com/guides/uv-index' },
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
        title="UV Index Guide: Sun Safety and Planning | AtmosMind"
        description="Learn what the UV Index means, how it changes through the day, and practical sun protection tips for commuting, sports, and travel."
        path="/guides/uv-index"
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
            UV Index Guide: understanding sun exposure
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>
              The UV Index is a simple scale that estimates the intensity of ultraviolet radiation at
              the Earth’s surface. UV is invisible, but its effects are real: sunburn, skin aging, eye
              damage, and increased long-term skin cancer risk. A common misconception is that UV only
              matters on hot days. In reality, UV can be high even when the air feels cool, especially
              at high altitude or during clear spring days. That is why UV Index is a planning metric,
              not a “beach only” number.
            </p>

            <p>
              The scale typically groups values as low (0–2), moderate (3–5), high (6–7), very high
              (8–10), and extreme (11+). As the number rises, the time to sunburn shortens. The safest
              habit is to treat UV 3+ as a cue to use protection if you will be outside for any length
              of time. UV peaks around solar noon, so midday outdoor activity has the highest exposure
              even if morning and evening feel comfortable.
            </p>

            <p>
              Clouds reduce UV sometimes, but not always. Thin clouds can still allow significant UV
              through, and bright surfaces like sand, water, and snow reflect UV, increasing exposure.
              Snow reflection is especially important in winter sports settings. In cities, UV risk can
              still be meaningful during commutes, outdoor lunches, and long walks—especially if you
              spend time in open areas with limited shade.
            </p>

            <p>
              Practical protection is straightforward: seek shade during peak hours, wear sunglasses
              with UV protection, and cover skin with a hat and long sleeves when feasible. Sunscreen is
              most effective when applied generously and re-applied; many people under-apply. Choose a
              broad-spectrum product and reapply after sweating or water exposure. Eye protection matters
              too—UV can contribute to irritation and long-term issues, so sunglasses are not just a style
              accessory.
            </p>

            <p>
              Use the UV Index as a small daily decision tool. If UV is high, adjust outdoor exercise to
              earlier or later, bring a hat, and plan hydration. If you are traveling, remember that UV
              increases with altitude and can remain strong near the equator year-round. When combined with
              AtmosMind’s weather and AI insights, UV awareness helps you avoid surprises and protects you
              over the long term.
            </p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

