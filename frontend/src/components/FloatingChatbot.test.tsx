import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import en from '../../public/locales/en/translation.json';
import { FloatingChatbot } from './FloatingChatbot';
import { streamChatReply } from '../utils/chatStream';

jest.mock('react-i18next', () => {
  const mockEn = require('../../public/locales/en/translation.json');
  return {
    useTranslation: () => ({
      t: (key: string, options?: { defaultValue?: string }) => {
        const parts = key.split('.');
        let value: unknown = mockEn;
        for (const part of parts) {
          if (value && typeof value === 'object' && part in (value as object)) {
            value = (value as Record<string, unknown>)[part];
          } else {
            return options?.defaultValue ?? key;
          }
        }
        return typeof value === 'string' ? value : options?.defaultValue ?? key;
      },
      i18n: { language: 'en', changeLanguage: jest.fn() },
    }),
  };
});

jest.mock('../utils/chatStream', () => ({
  streamChatReply: jest.fn(),
}));

jest.mock('../context/SettingsContext', () => ({
  useSettings: () => ({
    currentLanguage: 'en',
    currentUnit: 'metric',
    setLanguage: jest.fn(),
    setUnit: jest.fn(),
  }),
}));

jest.mock('framer-motion', () => {
  const React = require('react');
  const stripMotionProps = (props: Record<string, unknown>) => {
    const {
      initial,
      animate,
      exit,
      transition,
      variants,
      whileHover,
      whileTap,
      style,
      ...rest
    } = props;
    return rest;
  };

  return {
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
        <div {...stripMotionProps(props)}>{children}</div>
      ),
      button: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
        <button type="button" {...stripMotionProps(props)}>
          {children}
        </button>
      ),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useAnimation: () => ({
      start: jest.fn().mockResolvedValue(undefined),
    }),
    useReducedMotion: () => true,
  };
});

jest.mock('./MarkdownMessage', () => ({
  MarkdownMessage: ({ content }: { content: string }) => <div data-testid="markdown-message">{content}</div>,
}));

const mockStreamChatReply = streamChatReply as jest.MockedFunction<typeof streamChatReply>;

beforeEach(() => {
  mockStreamChatReply.mockReset();
  mockStreamChatReply.mockImplementation(async (_messages, _context, callbacks) => {
    callbacks.onToken('**Current Conditions**\n\nMild and sunny in Paris today.');
  });
  Element.prototype.scrollIntoView = jest.fn();
});

describe('FloatingChatbot', () => {
  it('opens and closes the chat panel when the launcher is toggled', async () => {
    render(<FloatingChatbot />);

    expect(screen.queryByText(en.chat.welcome)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: en.chat.open }));
    expect(await screen.findByText(en.chat.welcome)).toBeInTheDocument();
    expect(screen.getByText(en.chat.title)).toBeInTheDocument();

    const launcherClose = screen.getAllByRole('button', { name: en.chat.close }).pop()!;
    fireEvent.click(launcherClose);
    await waitFor(() => {
      expect(screen.queryByText(en.chat.welcome)).not.toBeInTheDocument();
    });
  });

  it('submits a weather question and renders the streamed AI response', async () => {
    render(<FloatingChatbot cityName="Paris" latitude={48.8566} longitude={2.3522} />);

    fireEvent.click(screen.getByRole('button', { name: en.chat.open }));

    const input = await screen.findByPlaceholderText(en.chat.placeholder);
    fireEvent.change(input, { target: { value: 'What is the weather in Paris?' } });
    fireEvent.click(screen.getByRole('button', { name: en.chat.send }));

    await waitFor(() => {
      expect(mockStreamChatReply).toHaveBeenCalledWith(
        expect.any(Array),
        expect.objectContaining({
          language: 'en',
          unit: 'metric',
          cityName: 'Paris',
          latitude: 48.8566,
          longitude: 2.3522,
        }),
        expect.any(Object),
        expect.any(AbortSignal)
      );
    });

    expect(await screen.findByTestId('markdown-message')).toHaveTextContent('Mild and sunny in Paris');
    expect(screen.getByText('What is the weather in Paris?')).toBeInTheDocument();
  });

  it('handles a plain JSON reply payload from the backend', async () => {
    mockStreamChatReply.mockImplementation(async (_messages, _context, callbacks) => {
      callbacks.onToken('JSON fallback reply from backend.');
    });

    render(<FloatingChatbot />);
    fireEvent.click(screen.getByRole('button', { name: en.chat.open }));

    const input = await screen.findByPlaceholderText(en.chat.placeholder);
    fireEvent.change(input, { target: { value: 'Paris weather?' } });
    fireEvent.click(screen.getByRole('button', { name: en.chat.send }));

    expect(await screen.findByText('JSON fallback reply from backend.')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(en.chat.placeholder)).not.toBeDisabled();
  });

  it('shows an assistant error bubble when the SSE stream reports an error', async () => {
    mockStreamChatReply.mockImplementation(async (_messages, _context, callbacks) => {
      callbacks.onError?.('Bir bağlantı sorunu oluştu, lütfen tekrar deneyin.');
    });

    render(<FloatingChatbot />);
    fireEvent.click(screen.getByRole('button', { name: en.chat.open }));

    const input = await screen.findByPlaceholderText(en.chat.placeholder);
    fireEvent.change(input, { target: { value: 'Paris weather?' } });
    fireEvent.click(screen.getByRole('button', { name: en.chat.send }));

    expect(
      await screen.findByText('Bir bağlantı sorunu oluştu, lütfen tekrar deneyin.')
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(en.chat.placeholder)).not.toBeDisabled();
  });
});
