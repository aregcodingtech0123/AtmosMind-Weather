import React from 'react';
import { Helmet } from 'react-helmet-async';

const SITE_URL = process.env.REACT_APP_SITE_URL ?? 'https://atmosmind.app';

interface SeoProps {
  title: string;
  description: string;
  path: string;
  structuredData?: Record<string, unknown> | Array<Record<string, unknown>>;
}

export const Seo: React.FC<SeoProps> = ({ title, description, path, structuredData }) => {
  const canonicalUrl = `${SITE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const pageGraph = Array.isArray(structuredData)
    ? structuredData
    : structuredData
      ? [structuredData]
      : [];

  const baseGraph: Array<Record<string, unknown>> = [
    {
      '@type': 'Organization',
      '@id': `${SITE_URL}#organization`,
      name: 'AtmosMind',
      url: SITE_URL,
      logo: `${SITE_URL}/AtmosMindLogo.webp`,
    },
    {
      '@type': 'WebSite',
      '@id': `${SITE_URL}#website`,
      url: SITE_URL,
      name: 'AtmosMind',
      description,
      publisher: { '@id': `${SITE_URL}#organization` },
      potentialAction: {
        '@type': 'SearchAction',
        target: `${SITE_URL}/weather/{search_term_string}`,
        'query-input': 'required name=search_term_string',
      },
    },
  ];

  const graph = [...baseGraph, ...pageGraph];

  return (
    <Helmet prioritizeSeoTags>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonicalUrl} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={canonicalUrl} />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      {graph.length > 0 && (
        <script type="application/ld+json">
          {JSON.stringify({ '@context': 'https://schema.org', '@graph': graph })}
        </script>
      )}
    </Helmet>
  );
};
