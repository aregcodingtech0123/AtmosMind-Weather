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
  const graph = Array.isArray(structuredData)
    ? structuredData
    : structuredData
      ? [structuredData]
      : [];

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
