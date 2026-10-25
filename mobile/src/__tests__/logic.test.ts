/// <reference types="jest" />
import { targetSize } from '../features/detection/normaliseImage';
import { codeKey } from '../features/weather/weather';
import en from '../i18n/locales/en.json';
import hi from '../i18n/locales/hi.json';

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    k.startsWith('_') ? [] : typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`]);
}

describe('normaliseImage.targetSize', () => {
  it('never upscales', () => expect(targetSize(1200, 900)).toBeNull());
  it('caps the long edge at 1600 and keeps the aspect ratio', () => {
    expect(targetSize(4000, 3000)).toEqual({ width: 1600, height: 1200 });
    expect(targetSize(3000, 4000)).toEqual({ width: 1200, height: 1600 });
  });
});

describe('weather codes', () => {
  it('maps WMO codes', () => {
    expect(codeKey(0)).toBe('clear');
    expect(codeKey(63)).toBe('rain');
    expect(codeKey(95)).toBe('storm');
    expect(codeKey(null)).toBe('unknown');
  });
});

describe('i18n', () => {
  it('Hindi has every English key [A4]', () => {
    const hiKeys = new Set(keys(hi));
    expect(keys(en).filter((k) => !hiKeys.has(k))).toEqual([]);
  });
});
