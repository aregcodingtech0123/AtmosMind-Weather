import React, { Suspense, lazy } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import './index.css';
import './i18n';
import App from './App';
import ScrollToTop from './components/ScrollToTop';
import AboutUs from './pages/AboutUs';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import Contact from './pages/Contact';
import CookiePolicy from './pages/CookiePolicy';
import { SettingsProvider } from './context/SettingsContext';
import reportWebVitals from './reportWebVitals';
const HumidityGuide = lazy(() => import('./pages/guides/HumidityGuide'));
const WindChillGuide = lazy(() => import('./pages/guides/WindChillGuide'));
const WhatToWearGuide = lazy(() => import('./pages/guides/WhatToWearGuide'));
const ThunderstormSafety = lazy(() => import('./pages/guides/ThunderstormSafety'));
const UvIndexGuide = lazy(() => import('./pages/guides/UvIndexGuide'));

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <HelmetProvider>
      <SettingsProvider>
        <BrowserRouter>
          <ScrollToTop />
          <Suspense fallback={null}>
            <Routes>
              <Route path="/about" element={<AboutUs />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/terms" element={<TermsOfService />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/cookies" element={<CookiePolicy />} />
              <Route path="/guides/humidity" element={<HumidityGuide />} />
              <Route path="/guides/wind-chill" element={<WindChillGuide />} />
              <Route path="/guides/what-to-wear" element={<WhatToWearGuide />} />
              <Route path="/guides/thunderstorm-safety" element={<ThunderstormSafety />} />
              <Route path="/guides/uv-index" element={<UvIndexGuide />} />
              <Route path="*" element={<App />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </SettingsProvider>
    </HelmetProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
