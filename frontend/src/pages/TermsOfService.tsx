import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../utils/cn';
import { Navbar } from '../components/Navbar';
import { Seo } from '../components/Seo';
import { useTranslation } from 'react-i18next';

export default function TermsOfService() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://atmosmind.app/' },
      { '@type': 'ListItem', position: 2, name: 'Terms of Service', item: 'https://atmosmind.app/terms' },
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
        title={t('terms.seoTitle')}
        description={t('terms.seoDescription')}
        path="/terms"
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
            {t('terms.title')}
          </h1>

          <p className="text-white/70 leading-8 mb-8">
            {t('terms.intro')}
          </p>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.serviceTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.serviceBody')}
            </p>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.aiTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.aiBody')}
            </p>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.noWarrantyTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.noWarrantyBody')}
            </p>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.limitationTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.limitationBody')}
            </p>
          </section>

          <section className="space-y-3 mb-8">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.adsTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.adsBody')}
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl md:text-2xl font-semibold text-white/85">
              {t('terms.changesTitle')}
            </h2>
            <p className="text-white/70 leading-8">
              {t('terms.changesBody')}
            </p>
          </section>
        </motion.main>
      </div>
    </div>
  );
}
