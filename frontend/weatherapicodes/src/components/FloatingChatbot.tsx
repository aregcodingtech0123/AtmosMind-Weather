import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, Send } from 'lucide-react';
import { cn } from '../utils/cn';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useSettings } from '../context/SettingsContext';

const API_BASE = (process.env.REACT_APP_API_URL ?? '').replace(/\/$/, '');

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const FloatingChatbot: React.FC = () => {
  const { t } = useTranslation();
  const { currentLanguage, currentUnit } = useSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      const response = await fetch(`${API_BASE}/api/chat`, {
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
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
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
                  {msg.content}
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

      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className={cn(
          'flex items-center justify-center w-14 h-14 rounded-full',
          'bg-cyan-500/90 hover:bg-cyan-400 text-white shadow-lg',
          'hover:scale-105 hover:shadow-xl active:scale-100',
          'transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-transparent'
        )}
        aria-label={String(isOpen ? t('chat.close') : t('chat.open'))}
      >
        <Bot className="w-7 h-7" strokeWidth={1.5} />
      </button>
    </div>
  );
};
