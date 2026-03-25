import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../utils/cn';
import { Navbar } from '../components/Navbar';
import { Seo } from '../components/Seo';
import { useTranslation } from 'react-i18next';

export default function CookiePolicy() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmind.app/' },
      { '@type': 'ListItem', position: 2, name: 'Cookie Policy', item: 'https://atmosmind.app/cookies' },
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
        title={String(t('cookies.seoTitle', { defaultValue: 'Cookie Policy - AtmosMind' }))}
        description={String(
          t('cookies.seoDescription', {
            defaultValue: 'Learn how AtmosMind uses cookies and similar technologies for analytics and advertising.',
          })
        )}
        path="/cookies"
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
          <h1 className="text-3xl md:text-4xl font-semibold text-white/90 font-heading mb-8">
            {String(t('cookies.title', { defaultValue: 'Cookie Policy' }))}
          </h1>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {String(t('cookies.whatTitle', { defaultValue: 'What are cookies?' }))}
            </h2>
            <p className="text-white/70 leading-8">
              {String(
                t('cookies.whatBody', {
                  defaultValue:
                    'Cookies are small text files stored on your device. Similar technologies include local storage and device identifiers. They help websites remember preferences and measure performance.',
                })
              )}
            </p>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {String(t('cookies.whyTitle', { defaultValue: 'Why we use cookies' }))}
            </h2>
            <ul className="list-disc pl-6 space-y-2 text-white/70 leading-8">
              <li>{String(t('cookies.whyItem1', { defaultValue: 'To store language and unit preferences.' }))}</li>
              <li>{String(t('cookies.whyItem2', { defaultValue: 'To understand usage and improve performance.' }))}</li>
              <li>{String(t('cookies.whyItem3', { defaultValue: 'To support advertising, including Google AdSense.' }))}</li>
            </ul>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {String(t('cookies.adsTitle', { defaultValue: 'Advertising and Google AdSense' }))}
            </h2>
            <p className="text-white/70 leading-8">
              {String(
                t('cookies.adsBody', {
                  defaultValue:
                    'We may use Google AdSense to serve ads. Google and its partners may use cookies or device identifiers to show ads, measure ad performance, and (where permitted) personalize ads.',
                })
              )}
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {String(t('cookies.controlsTitle', { defaultValue: 'Your choices' }))}
            </h2>
            <p className="text-white/70 leading-8">
              {String(
                t('cookies.controlsBody', {
                  defaultValue:
                    'You can manage cookies through your browser settings. Where required, you can accept or reject advertising cookies using the consent banner.',
                })
              )}
            </p>
          </section>
        </motion.main>
      </div>
    </div>
  );
}
