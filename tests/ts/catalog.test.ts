import { appCountLabel } from '@/lib/catalog';

describe('appCountLabel', () => {
  it('rounds down to the hundred, so the claim stays true', () => {
    expect(appCountLabel(1609)).toBe('1,600+');
    expect(appCountLabel(832)).toBe('800+');
    expect(appCountLabel(100)).toBe('100+');
  });

  it('gives a small count as it is', () => {
    expect(appCountLabel(42)).toBe('42');
    expect(appCountLabel(0)).toBe('0');
  });
});
