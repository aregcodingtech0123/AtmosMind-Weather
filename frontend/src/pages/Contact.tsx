import React, { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import emailjs from '@emailjs/browser';
import { cn } from '../utils/cn';
import { Navbar } from '../components/Navbar';
import { Seo } from '../components/Seo';
import { useTranslation } from 'react-i18next';
import {
  ADMIN_CONTACT_MAIL,
  EMAILJS_PUBLIC_KEY,
  EMAILJS_SERVICE_ID,
  EMAILJS_TEMPLATE_ID,
  isEmailJsConfigured,
} from '../config/emailjs';

const SITE_URL = process.env.REACT_APP_SITE_URL ?? 'https://atmosmindweather.com';

export default function Contact() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [formStatus, setFormStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const contactEmail = useMemo(
    () => ADMIN_CONTACT_MAIL || 'support@atmosmindweather.com',
    []
  );

  const breadcrumbSchema = {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Contact', item: `${SITE_URL}/contact` },
    ],
  };

  const handleSearch = useCallback(
    (cityName: string, lat: number, lng: number) => {
      const encoded = encodeURIComponent(cityName);
      navigate(`/weather/${encoded}`, { state: { cityName, latitude: lat, longitude: lng } });
    },
    [navigate]
  );

  const handleLocationRequest = useCallback(() => {
    navigate('/');
  }, [navigate]);

  const resetStatusOnChange = useCallback(() => {
    setFormStatus((s) => (s === 'idle' ? s : 'idle'));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormStatus('idle');

    if (!isEmailJsConfigured()) {
      setFormStatus('error');
      return;
    }

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedMessage = message.trim();
    if (!trimmedName || !trimmedEmail || !trimmedMessage) {
      setFormStatus('error');
      return;
    }

    setSending(true);
    try {
      await emailjs.send(
        EMAILJS_SERVICE_ID,
        EMAILJS_TEMPLATE_ID,
        {
          from_name: trimmedName,
          from_email: trimmedEmail,
          message: trimmedMessage,
          to_email: ADMIN_CONTACT_MAIL,
          reply_to: trimmedEmail,
        },
        { publicKey: EMAILJS_PUBLIC_KEY }
      );
      setFormStatus('success');
      setName('');
      setEmail('');
      setMessage('');
    } catch (err) {
      console.error(err);
      setFormStatus('error');
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className={cn(
        'min-h-screen transition-all duration-700 ease-in-out',
        'bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950',
        'text-white'
      )}
    >
      <Seo
        title={String(t('contact.seoTitle', { defaultValue: 'Contact - AtmosMind' }))}
        description={String(
          t('contact.seoDescription', { defaultValue: 'Get in touch with the AtmosMind team.' })
        )}
        path="/contact"
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
          <h1 className="text-3xl md:text-4xl font-semibold text-white/90 font-heading mb-3">
            {String(t('contact.title', { defaultValue: 'Contact' }))}
          </h1>
          <p className="text-white/70 leading-8 mb-8">
            {String(
              t('contact.subtitle', {
                defaultValue:
                  'Have a question, feedback, or a support request? Send us a message and we’ll get back to you.',
              })
            )}
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <section className="lg:col-span-2 rounded-2xl border border-white/10 bg-black/20 p-5">
              <h2 className="text-lg font-semibold text-white/90 mb-2">
                {String(t('contact.emailTitle', { defaultValue: 'Email' }))}
              </h2>
              <p className="text-sm text-white/70 leading-7">
                {String(
                  t('contact.emailBody', {
                    defaultValue:
                      'For privacy requests, AdSense policy questions, or general support, email us at:',
                  })
                )}
              </p>
              <a
                href={`mailto:${contactEmail}`}
                className="mt-3 inline-flex text-sm font-medium text-cyan-200 hover:text-cyan-100 transition-colors"
              >
                {contactEmail}
              </a>
            </section>

            <section className="lg:col-span-3 rounded-2xl border border-white/10 bg-black/20 p-5">
              <h2 className="text-lg font-semibold text-white/90 mb-4">
                {String(t('contact.formTitle', { defaultValue: 'Send a message' }))}
              </h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="space-y-2">
                    <span className="text-sm text-white/75">
                      {String(t('contact.nameLabel', { defaultValue: 'Name' }))}
                    </span>
                    <input
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        resetStatusOnChange();
                      }}
                      required
                      disabled={sending}
                      className="w-full rounded-xl bg-black/20 border border-white/15 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/50 disabled:opacity-60"
                      placeholder={String(t('contact.namePlaceholder', { defaultValue: 'Your name' }))}
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm text-white/75">
                      {String(t('contact.emailLabel', { defaultValue: 'Email' }))}
                    </span>
                    <input
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        resetStatusOnChange();
                      }}
                      required
                      disabled={sending}
                      type="email"
                      className="w-full rounded-xl bg-black/20 border border-white/15 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/50 disabled:opacity-60"
                      placeholder={String(t('contact.emailPlaceholder', { defaultValue: 'you@example.com' }))}
                    />
                  </label>
                </div>

                <label className="space-y-2 block">
                  <span className="text-sm text-white/75">
                    {String(t('contact.messageLabel', { defaultValue: 'Message' }))}
                  </span>
                  <textarea
                    value={message}
                    onChange={(e) => {
                      setMessage(e.target.value);
                      resetStatusOnChange();
                    }}
                    required
                    disabled={sending}
                    rows={6}
                    className="w-full rounded-xl bg-black/20 border border-white/15 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-white/50 resize-y disabled:opacity-60"
                    placeholder={String(
                      t('contact.messagePlaceholder', { defaultValue: 'Tell us how we can help…' })
                    )}
                  />
                </label>

                {formStatus === 'success' && (
                  <p
                    className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100"
                    role="status"
                  >
                    {String(t('contact.success', { defaultValue: 'Message sent successfully.' }))}
                  </p>
                )}
                {formStatus === 'error' && (
                  <p
                    className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-100"
                    role="alert"
                  >
                    {String(
                      isEmailJsConfigured()
                        ? t('contact.error', {
                            defaultValue: "We couldn't send your message. Please try again later.",
                          })
                        : t('contact.configError', {
                            defaultValue:
                              'Contact form is not configured. Set REACT_APP_EMAILJS_* and REACT_APP_ADMIN_CONTACT_MAIL.',
                          })
                    )}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={sending}
                  className={cn(
                    'inline-flex items-center justify-center rounded-xl px-5 py-3 min-w-[140px]',
                    'bg-white/15 hover:bg-white/25 text-white font-medium',
                    'transition-colors focus:outline-none focus:ring-2 focus:ring-white/60',
                    'disabled:opacity-60 disabled:cursor-not-allowed'
                  )}
                >
                  {sending
                    ? String(t('contact.sending', { defaultValue: 'Sending...' }))
                    : String(t('contact.send', { defaultValue: 'Send' }))}
                </button>
              </form>

              <p className="mt-4 text-xs text-white/50 leading-6">
                {String(
                  t('contact.note', {
                    defaultValue:
                      'Messages are delivered securely via EmailJS. We use your email only to respond to this inquiry.',
                  })
                )}
              </p>
            </section>
          </div>
        </motion.main>
      </div>
    </div>
  );
}
