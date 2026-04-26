import React from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';
import { useTranslation } from 'react-i18next';
import { Navbar } from '../../components/Navbar';
import { Seo } from '../../components/Seo';

export default function UvIndexGuide() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: t('navbar.goHome'), item: 'https://atmosmind.app/' },
      { '@type': 'ListItem', position: 2, name: t('footer.sections.guides'), item: 'https://atmosmind.app/guides' },
      { '@type': 'ListItem', position: 3, name: t('footer.guides.uvIndex'), item: 'https://atmosmind.app/guides/uv-index' },
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
        title={t('guides.uvIndex.seoTitle')}
        description={t('guides.uvIndex.seoDescription')}
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
            {t('guides.uvIndex.title')}
          </h1>

          <div className="space-y-6 text-white/75 leading-8">
            <p>{t('guides.uvIndex.p1')}</p>
            <p>{t('guides.uvIndex.p2')}</p>
            <p>{t('guides.uvIndex.p3')}</p>
            <p>{t('guides.uvIndex.p4')}</p>
            <p>{t('guides.uvIndex.p5')}</p>
          </div>
        </motion.main>
      </div>
    </div>
  );
}

