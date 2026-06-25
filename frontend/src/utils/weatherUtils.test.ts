import { resolveWmoBackgroundTheme } from '../utils/weatherUtils';

describe('resolveWmoBackgroundTheme', () => {
  it('maps clear codes', () => {
    expect(resolveWmoBackgroundTheme(0)).toBe('clear');
    expect(resolveWmoBackgroundTheme(1)).toBe('clear');
  });

  it('maps cloudy and fog codes', () => {
    expect(resolveWmoBackgroundTheme(2)).toBe('cloudy');
    expect(resolveWmoBackgroundTheme(45)).toBe('cloudy');
  });

  it('maps rain and drizzle codes', () => {
    expect(resolveWmoBackgroundTheme(55)).toBe('rainy');
    expect(resolveWmoBackgroundTheme(81)).toBe('rainy');
  });

  it('maps snow codes', () => {
    expect(resolveWmoBackgroundTheme(73)).toBe('snowy');
    expect(resolveWmoBackgroundTheme(86)).toBe('snowy');
  });

  it('maps thunderstorm codes', () => {
    expect(resolveWmoBackgroundTheme(95)).toBe('stormy');
    expect(resolveWmoBackgroundTheme(99)).toBe('stormy');
  });
});
