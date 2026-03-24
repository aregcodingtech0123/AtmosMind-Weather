import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../utils/cn';
import { Navbar } from '../components/Navbar';
import { Seo } from '../components/Seo';
import { useTranslation } from 'react-i18next';

export default function AboutUs() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const faqSchema = {
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'What is AtmosMind?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'AtmosMind is an AI-powered weather intelligence platform that combines real-time forecast data with actionable insights for daily planning and travel.',
        },
      },
      {
        '@type': 'Question',
        name: 'How does AI help in AtmosMind?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'AtmosMind uses AI to interpret weather signals and transform raw temperature, wind, humidity, and precipitation trends into practical recommendations.',
        },
      },
      {
        '@type': 'Question',
        name: 'Who should use AtmosMind?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'AtmosMind is designed for commuters, travelers, and weather-conscious users who need trustworthy and fast climate-aware guidance.',
        },
      },
      {
        '@type': 'Question',
        name: 'Where does AtmosMind weather data come from?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'AtmosMind integrates trusted weather data providers and presents them through a user-friendly AI-assisted forecasting interface.',
        },
      },
    ],
  };
  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Home',
        item: 'https://atmosmind.app/',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'About Us',
        item: 'https://atmosmind.app/about',
      },
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
        title={t('about.seoTitle')}
        description={t('about.seoDescription')}
        path="/about"
        structuredData={[breadcrumbSchema, faqSchema]}
      />
      {/* Full-width navbar so logo / search / controls are not squeezed inside max-w-5xl */}
      <div className="w-full px-4 pt-10 sm:px-5 md:px-8 lg:px-12">
        <Navbar onSearch={handleSearch} onLocationRequest={handleLocationRequest} />
      </div>

      <div className="max-w-5xl mx-auto px-4 pb-10 sm:px-5 md:px-8 lg:px-12">
        <motion.main
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className={cn(
            'rounded-3xl border border-white/10 bg-black/30 backdrop-blur-md',
            'px-6 py-10 md:px-10 md:py-12'
          )}
        >
          <h1 className="text-center text-3xl md:text-4xl font-semibold text-white/90 font-heading mb-8">
            {t('about.title')}
          </h1>
          <p className="mx-auto max-w-3xl text-base md:text-lg leading-8 text-white/75">
            {t('about.mainParagraph')}
          </p>

          <div className="mt-10 space-y-6">
            <section className="rounded-2xl border border-white/10 bg-black/20 p-5">
              <h2 className="text-xl font-semibold text-white/90 mb-2">{t('about.qa1Q')}</h2>
              <p className="text-white/70 leading-7">
                {t('about.qa1A')}
              </p>
            </section>

            <section className="rounded-2xl border border-white/10 bg-black/20 p-5">
              <h2 className="text-xl font-semibold text-white/90 mb-2">{t('about.qa2Q')}</h2>
              <p className="text-white/70 leading-7">
                {t('about.qa2A')}
              </p>
            </section>

            <section className="rounded-2xl border border-white/10 bg-black/20 p-5">
              <h2 className="text-xl font-semibold text-white/90 mb-2">{t('about.qa3Q')}</h2>
              <p className="text-white/70 leading-7">
                {t('about.qa3A')}
              </p>
            </section>
          </div>
        </motion.main>
      </div>
    </div>
  );
}
