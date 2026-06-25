import {
  getCookie,
  setCookie,
  setPermanentCookie,
  deleteCookie,
} from './cookieUtils';

beforeEach(() => {
  document.cookie.split(';').forEach((c) => {
    const name = c.trim().split('=')[0];
    if (name) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/`;
    }
  });
});

describe('getCookie', () => {
  it('returns value of existing cookie', () => {
    document.cookie = 'session=abc123';
    expect(getCookie('session')).toBe('abc123');
  });

  it('returns null when cookie not found', () => {
    expect(getCookie('nonexistent')).toBeNull();
  });

  it('handles multiple cookies and does not match name prefixes', () => {
    document.cookie = 'token=xyz';
    document.cookie = 'tokenExtra=should-not-match';
    document.cookie = 'other=val';
    expect(getCookie('token')).toBe('xyz');
    expect(getCookie('other')).toBe('val');
    expect(getCookie('tok')).toBeNull();
  });
});

describe('setCookie', () => {
  it('sets a cookie retrievable via getCookie', () => {
    setCookie('myCookie', 'myValue');
    expect(getCookie('myCookie')).toBe('myValue');
  });
});

describe('setPermanentCookie', () => {
  it('sets a cookie retrievable via getCookie', () => {
    setPermanentCookie('perm', 'yes');
    expect(getCookie('perm')).toBe('yes');
  });
});

describe('deleteCookie', () => {
  it('removes a previously set cookie', () => {
    setCookie('temp', 'value');
    expect(getCookie('temp')).toBe('value');
    deleteCookie('temp');
    expect(getCookie('temp')).toBeNull();
  });
});
