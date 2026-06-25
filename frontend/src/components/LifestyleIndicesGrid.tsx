import React, { useMemo } from 'react';

import { motion } from 'framer-motion';

import { useTranslation } from 'react-i18next';

import { Eye, Flower2, Sun, Wind } from 'lucide-react';

import { useSettings } from '../context/SettingsContext';

import { LifestyleIndices, LifestyleAqiCategory, LifestyleUvCategory } from '../types/weather';

import { cn } from '../utils/cn';

import { isPollenUnavailable, isVisibilityUnavailable } from '../utils/lifestyleUtils';



interface LifestyleIndicesGridProps {

  data: LifestyleIndices | null;

  loading?: boolean;

  error?: string | null;

  className?: string;

}



function formatVisibility(meters: number | null, unit: 'metric' | 'imperial'): string {

  if (meters == null || Number.isNaN(meters)) return '—';

  if (unit === 'imperial') {

    return `${(meters / 1609.344).toFixed(1)}`;

  }

  return `${(meters / 1000).toFixed(1)}`;

}



function formatDewPoint(celsius: number | null, unit: 'metric' | 'imperial'): string {

  if (celsius == null || Number.isNaN(celsius)) return '—';

  if (unit === 'imperial') {

    return `${Math.round((celsius * 9) / 5 + 32)}`;

  }

  return `${Math.round(celsius)}`;

}



function aqiAccent(category: LifestyleAqiCategory): string {

  switch (category) {

    case 'good':

      return 'text-emerald-300 border-emerald-400/30 shadow-emerald-500/10';

    case 'fair':

      return 'text-lime-300 border-lime-400/30 shadow-lime-500/10';

    case 'moderate':

      return 'text-amber-300 border-amber-400/30 shadow-amber-500/10';

    case 'poor':

      return 'text-orange-300 border-orange-400/30 shadow-orange-500/10';

    case 'very_poor':
    case 'hazardous':
      return 'text-rose-300 border-rose-400/30 shadow-rose-500/10';

    default:

      return 'text-white/70 border-white/15 shadow-black/10';

  }

}



function uvAccent(category: LifestyleUvCategory): string {

  switch (category) {

    case 'low':

      return 'text-sky-300 border-sky-400/30';

    case 'moderate':

      return 'text-amber-300 border-amber-400/30';

    case 'high':

      return 'text-orange-300 border-orange-400/30';

    case 'very_high':
    case 'extreme':
      return 'text-rose-300 border-rose-400/30';

    default:

      return 'text-white/70 border-white/15';

  }

}



function pollenAccent(level: LifestyleIndices['pollen']['level']): string {

  switch (level) {

    case 'low':

      return 'text-emerald-300 border-emerald-400/30';

    case 'medium':

      return 'text-amber-300 border-amber-400/30';

    case 'high':

      return 'text-rose-300 border-rose-400/30';

    default:

      return 'text-white/70 border-white/15';

  }

}



interface IndexCardProps {

  title: string;

  value: React.ReactNode;

  helper: string;

  icon: React.ReactNode;

  accent: string;

  testId: string;

  unavailable?: boolean;

}



const IndexCard: React.FC<IndexCardProps> = ({

  title,

  value,

  helper,

  icon,

  accent,

  testId,

  unavailable = false,

}) => (

  <motion.article

    data-testid={testId}

    data-unavailable={unavailable ? 'true' : 'false'}

    whileHover={unavailable ? undefined : { y: -4, scale: 1.01 }}

    transition={{ type: 'spring', stiffness: 380, damping: 28 }}

    className={cn(

      'group relative overflow-hidden rounded-2xl border p-5',

      'bg-white/10 backdrop-blur-xl shadow-lg',

      'transition-colors duration-300',

      unavailable

        ? 'opacity-60 saturate-50 hover:bg-white/10'

        : 'hover:bg-white/15',

      accent

    )}

  >

    <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/5 blur-2xl transition-opacity group-hover:opacity-80" />

    <div className="mb-4 flex items-center justify-between gap-3">

      <h3 className="text-sm font-medium tracking-wide text-white/80">{title}</h3>

      <div className="rounded-xl bg-black/20 p-2 text-white/90">{icon}</div>

    </div>

    <div

      className={cn(

        'mb-2 font-heading tracking-tight',

        unavailable ? 'text-base font-medium italic text-white/45' : 'text-3xl font-bold text-white'

      )}

    >

      {value}

    </div>

    <p className={cn('text-xs leading-relaxed', unavailable ? 'text-white/45' : 'text-white/65')}>

      {helper}

    </p>

  </motion.article>

);



export const LifestyleIndicesGrid: React.FC<LifestyleIndicesGridProps> = ({

  data,

  loading = false,

  error = null,

  className,

}) => {

  const { t } = useTranslation();

  const { currentUnit } = useSettings();

  const unavailableLabel = String(t('lifestyleIndices.unavailable'));



  const visibilityUnitLabel =

    currentUnit === 'imperial'

      ? String(t('lifestyleIndices.miles'))

      : String(t('lifestyleIndices.km'));

  const dewUnitLabel = currentUnit === 'imperial' ? '°F' : '°C';



  const cards = useMemo(() => {

    if (!data) return null;



    const aqiUnavailable = data.aqi_value == null;

    const uvUnavailable = data.uv_index == null;

    const pollenUnavailable = isPollenUnavailable(data);

    const visibilityUnavailable = isVisibilityUnavailable(data);



    const aqiDisplay = aqiUnavailable

      ? unavailableLabel

      : `${data.aqi_value}${data.aqi_standard === 'us' ? ' US' : data.aqi_standard === 'european' ? ' EU' : ''}`;



    const uvDisplay = uvUnavailable ? unavailableLabel : data.uv_index!.toFixed(1);



    const pollenLabel = pollenUnavailable

      ? unavailableLabel

      : String(

          t(`lifestyleIndices.pollen.level.${data.pollen.level}`, {

            defaultValue: data.pollen.level,

          })

        );



    return {

      aqiUnavailable,

      uvUnavailable,

      pollenUnavailable,

      visibilityUnavailable,

      aqiDisplay,

      uvDisplay,

      pollenLabel,

      visibility: visibilityUnavailable

        ? unavailableLabel

        : formatVisibility(data.visibility_meters, currentUnit),

      dewPoint: visibilityUnavailable

        ? unavailableLabel

        : formatDewPoint(data.dew_point_celsius, currentUnit),

    };

  }, [data, currentUnit, t, unavailableLabel]);



  const sectionHeader = (

    <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">

      <div>

        <h2 className="text-xl font-semibold text-white font-heading tracking-tight">

          {t('lifestyleIndices.title')}

        </h2>

        <p className="text-sm text-white/60">{t('lifestyleIndices.subtitle')}</p>

      </div>

    </div>

  );



  if (loading && !data) {

    return (

      <section

        className={cn('col-span-12', className)}

        aria-busy="true"

        aria-label={String(t('lifestyleIndices.title'))}

        data-testid="lifestyle-indices-grid"

      >

        {sectionHeader}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

          {Array.from({ length: 4 }).map((_, i) => (

            <div key={i} className="h-40 animate-pulse rounded-2xl bg-white/10" />

          ))}

        </div>

      </section>

    );

  }



  if (!data || !cards) {

    return (

      <section

        className={cn('col-span-12', className)}

        data-testid="lifestyle-indices-grid"

        aria-label={String(t('lifestyleIndices.title'))}

      >

        {sectionHeader}

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center opacity-70">

          <p className="text-sm text-white/70">

            {error || String(t('messages.failedToLoadLifestyleIndices'))}

          </p>

        </div>

      </section>

    );

  }



  const aqiHelper = cards.aqiUnavailable

    ? String(t('lifestyleIndices.aqi.helper.unknown'))

    : String(

        t(`lifestyleIndices.aqi.helper.${data.aqi_category}`, {

          defaultValue: t('lifestyleIndices.aqi.helper.unknown'),

        })

      );



  const uvHelper = cards.uvUnavailable

    ? String(t('lifestyleIndices.uv.helper.unknown'))

    : String(

        t(`lifestyleIndices.uv.helper.${data.uv_category}`, {

          defaultValue: t('lifestyleIndices.uv.helper.unknown'),

        })

      );



  const pollenHelper = cards.pollenUnavailable

    ? String(t('lifestyleIndices.pollen.helper.unknown'))

    : String(

        t(`lifestyleIndices.pollen.helper.${data.pollen.level}`, {

          defaultValue: t('lifestyleIndices.pollen.helper.unknown'),

        })

      );



  const visibilityHelper = cards.visibilityUnavailable

    ? String(t('lifestyleIndices.visibility.helperUnavailable'))

    : String(t('lifestyleIndices.visibility.helper'));



  return (

    <section className={cn('col-span-12', className)} data-testid="lifestyle-indices-grid">

      {sectionHeader}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <IndexCard

          testId="lifestyle-card-aqi"

          title={String(t('lifestyleIndices.aqi.title'))}

          value={cards.aqiDisplay}

          helper={aqiHelper}

          icon={<Wind className="h-5 w-5" strokeWidth={1.5} />}

          accent={aqiAccent(data.aqi_category)}

          unavailable={cards.aqiUnavailable}

        />



        <IndexCard

          testId="lifestyle-card-uv"

          title={String(t('lifestyleIndices.uv.title'))}

          value={cards.uvDisplay}

          helper={uvHelper}

          icon={<Sun className="h-5 w-5" strokeWidth={1.5} />}

          accent={uvAccent(data.uv_category)}

          unavailable={cards.uvUnavailable}

        />



        <IndexCard

          testId="lifestyle-card-pollen"

          title={String(t('lifestyleIndices.pollen.title'))}

          value={cards.pollenLabel}

          helper={pollenHelper}

          icon={<Flower2 className="h-5 w-5" strokeWidth={1.5} />}

          accent={pollenAccent(data.pollen.level)}

          unavailable={cards.pollenUnavailable}

        />



        <IndexCard

          testId="lifestyle-card-visibility"

          title={String(t('lifestyleIndices.visibility.title'))}

          value={

            cards.visibilityUnavailable ? (

              cards.visibility

            ) : (

              <div className="space-y-2">

                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">

                  <span>{cards.visibility}</span>

                  <span className="text-lg font-semibold text-white/75">{visibilityUnitLabel}</span>

                </div>

                <p className="text-sm font-medium text-white/75">

                  {String(t('lifestyleIndices.visibility.dewPoint'))}: {cards.dewPoint}

                  {dewUnitLabel}

                </p>

              </div>

            )

          }

          helper={visibilityHelper}

          icon={<Eye className="h-5 w-5" strokeWidth={1.5} />}

          accent="text-cyan-200 border-cyan-400/25 shadow-cyan-500/10"

          unavailable={cards.visibilityUnavailable}

        />

      </div>

    </section>

  );

};


