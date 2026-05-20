import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Bot, X, Send } from 'lucide-react';
import { cn } from '../utils/cn';
import {
  motion,
  AnimatePresence,
  useAnimation,
  useReducedMotion,
  type Variants,
} from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useSettings } from '../context/SettingsContext';
import { apiUrl } from '../services/api';
import { MarkdownMessage } from './MarkdownMessage';

const TOOLTIP_MOUNT_DELAY_MS = 2000;
const TOOLTIP_VISIBLE_MS = 4000;
const TOOLTIP_FADE_MS = 450;

const CHAT_TOOLTIP_KEYS = ['chat.tooltipWear', 'chat.tooltipRainTomorrow'] as const;

/** GPU-friendly translateY keyframes — 3 attention bounces, then rest. */
const LAUNCHER_BOUNCE_VARIANTS: Variants = {
  rest: { y: 0, scale: 1 },
  bounce: {
    y: [0, -12, 0, -8, 0, -4, 0],
    transition: {
      duration: 0.9,
      ease: [0.22, 1, 0.36, 1],
      times: [0, 0.17, 0.33, 0.5, 0.66, 0.83, 1],
    },
  },
};

type TooltipPhase = 'idle' | 'visible' | 'exit' | 'done';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const FloatingChatbot: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { currentLanguage, currentUnit } = useSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tooltipPhase, setTooltipPhase] = useState<TooltipPhase>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const tooltipPlayedRef = useRef(false);
  const launcherControls = useAnimation();
  const reduceMotion = useReducedMotion();

  const tooltipVariantIndex = useMemo(
    () => Math.floor(Math.random() * CHAT_TOOLTIP_KEYS.length),
    []
  );

  const tooltipMessage = useMemo(() => {
    const key = CHAT_TOOLTIP_KEYS[tooltipVariantIndex % CHAT_TOOLTIP_KEYS.length];
    return t(key);
  }, [t, i18n.language, tooltipVariantIndex]);

  const showTooltip = tooltipPhase === 'visible' || tooltipPhase === 'exit';

  useEffect(() => {
    if (isOpen) {
      setTooltipPhase('done');
      tooltipPlayedRef.current = true;
      return;
    }
    if (tooltipPlayedRef.current) return;

    let hideTimer: ReturnType<typeof setTimeout>;
    let doneTimer: ReturnType<typeof setTimeout>;

    const showTimer = setTimeout(() => {
      setTooltipPhase('visible');
      if (!reduceMotion) {
        void launcherControls.start('bounce').then(() => launcherControls.start('rest'));
      }
      hideTimer = setTimeout(() => {
        setTooltipPhase('exit');
        doneTimer = setTimeout(() => {
          setTooltipPhase('done');
          tooltipPlayedRef.current = true;
        }, TOOLTIP_FADE_MS);
      }, TOOLTIP_VISIBLE_MS);
    }, TOOLTIP_MOUNT_DELAY_MS);

    return () => {
      clearTimeout(showTimer);
      clearTimeout(hideTimer);
      clearTimeout(doneTimer);
    };
  }, [isOpen, launcherControls, reduceMotion]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMessage: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const nextHistory = [...messages, userMessage].map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const response = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept-Charset': 'utf-8' },
        body: JSON.stringify({ messages: nextHistory, language: currentLanguage, unit: currentUnit }),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data: { reply: string } = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: t('chat.errorFallback') },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 flex flex-col items-end max-w-[calc(100vw-1rem)]">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'mb-3 w-[340px] sm:w-[380px] rounded-2xl overflow-hidden',
              'bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl',
              'flex flex-col max-h-[420px]'
            )}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-black/20">
              <span className="font-semibold text-white flex items-center gap-2">
                <Bot className="w-5 h-5 text-cyan-400" strokeWidth={1.5} />
                {t('chat.title')}
              </span>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className={cn(
                  'p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/10',
                  'transition-colors focus:outline-none focus:ring-2 focus:ring-white/40'
                )}
                aria-label={String(t('chat.close'))}
              >
                <X className="w-5 h-5" strokeWidth={2} />
              </button>
            </div>
            <div className="px-4 py-2 border-b border-white/10 bg-black/10">
              <p className="text-[11px] leading-5 text-white/60">
                {String(
                  t('disclaimer.aiGenerated', {
                    defaultValue: 'AI-generated content. May be inaccurate—verify for critical decisions.',
                  })
                )}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[280px]">
              {messages.length === 0 && (
                <p className="text-sm text-white/70 text-center py-4 leading-relaxed">
                  {t('chat.welcome')}
                </p>
              )}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    'rounded-xl px-3 py-2 text-sm max-w-[90%]',
                    msg.role === 'user'
                      ? 'ml-auto bg-cyan-500/20 text-white'
                      : 'mr-auto bg-white/10 text-white/90'
                  )}
                >
                  {msg.role === 'assistant' ? (
                    <MarkdownMessage content={msg.content} />
                  ) : (
                    msg.content
                  )}
                </div>
              ))}
              {loading && (
                <div className="mr-auto rounded-xl px-3 py-2 text-sm bg-white/10 text-white/60">
                  {t('chat.thinking')}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-3 border-t border-white/10 flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={String(t('chat.placeholder'))}
                disabled={loading}
                className={cn(
                  'flex-1 bg-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/40',
                  'border border-white/10 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-transparent',
                  'disabled:opacity-60'
                )}
              />
              <button
                type="button"
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className={cn(
                  'p-2.5 rounded-xl bg-cyan-500/30 hover:bg-cyan-500/50 text-white',
                  'transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-400/50',
                  'disabled:opacity-50 disabled:pointer-events-none'
                )}
                aria-label={String(t('chat.send'))}
              >
                <Send className="w-5 h-5" strokeWidth={1.5} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col-reverse items-end gap-2 sm:flex-row-reverse sm:items-center sm:gap-3">
        <motion.button
          type="button"
          initial="rest"
          animate={launcherControls}
          variants={LAUNCHER_BOUNCE_VARIANTS}
          whileHover={reduceMotion ? undefined : { scale: 1.04 }}
          whileTap={reduceMotion ? undefined : { scale: 0.97 }}
          onClick={() => {
            setTooltipPhase('done');
            tooltipPlayedRef.current = true;
            void launcherControls.start('rest');
            setIsOpen((o) => !o);
          }}
          style={{ willChange: 'transform' }}
          className={cn(
            'shrink-0 relative isolate',
            'inline-flex items-center justify-center rounded-full',
            'touch-manipulation select-none',
            /* Mobile: 64px thumb-zone touch target */
            'size-16 min-h-[64px] min-w-[64px]',
            /* Desktop: 56px balanced footprint (48–56px range) */
            'md:size-14 md:min-h-[56px] md:min-w-[56px]',
            'bg-cyan-500 hover:bg-cyan-400 active:bg-cyan-600 text-white',
            'transform-gpu',
            /* Layered elevation — reads on dark glass UI */
            'shadow-[0_6px_20px_rgba(0,0,0,0.45),0_2px_8px_rgba(6,182,212,0.35)]',
            'ring-1 ring-inset ring-white/25',
            'md:shadow-[0_8px_28px_rgba(0,0,0,0.5),0_4px_12px_rgba(6,182,212,0.3)]',
            'hover:shadow-[0_10px_32px_rgba(0,0,0,0.55),0_6px_16px_rgba(34,211,238,0.4)]',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300',
            'focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950'
          )}
          aria-label={String(isOpen ? t('chat.close') : t('chat.open'))}
          aria-describedby={showTooltip ? 'chat-launcher-tooltip' : undefined}
        >
          <Bot
            className="size-8 md:size-7 shrink-0 pointer-events-none"
            strokeWidth={1.5}
            aria-hidden
          />
        </motion.button>

        <AnimatePresence>
          {showTooltip && (
            <motion.div
              id="chat-launcher-tooltip"
              role="status"
              aria-live="polite"
              initial={{ opacity: 0, y: 6, scale: 0.92 }}
              animate={
                tooltipPhase === 'visible'
                  ? { opacity: 1, y: 0, scale: 1 }
                  : { opacity: 0, y: 4, scale: 0.88 }
              }
              exit={{ opacity: 0, y: 4, scale: 0.88 }}
              transition={{
                duration: tooltipPhase === 'exit' ? TOOLTIP_FADE_MS / 1000 : 0.35,
                ease: 'easeOut',
              }}
              className={cn(
                'pointer-events-none relative',
                'max-w-[min(16rem,calc(100vw-5rem))] sm:max-w-[14rem] md:max-w-[14rem]',
                'rounded-2xl px-3.5 py-2.5',
                'bg-slate-900/95 text-white backdrop-blur-xl',
                'border border-cyan-400/25 shadow-lg shadow-cyan-500/15',
                'text-xs sm:text-sm font-medium leading-snug'
              )}
            >
              <p className="pr-0.5">{tooltipMessage}</p>
              <span
                className={cn(
                  'absolute block h-0 w-0 border-[7px] border-transparent',
                  'bottom-[-13px] right-6 border-t-slate-900/95 md:hidden'
                )}
                aria-hidden
              />
              <span
                className={cn(
                  'absolute hidden sm:block h-0 w-0 border-[7px] border-transparent',
                  'right-[-13px] top-1/2 -translate-y-1/2 border-l-slate-900/95'
                )}
                aria-hidden
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
