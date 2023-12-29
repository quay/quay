import React, {createContext, useContext, useEffect, useState} from 'react';

type ThemePreference = string;
export const ThemePreference = {
  LIGHT: 'LIGHT',
  DARK: 'DARK',
  AUTO: 'AUTO',
};

const ThemeContext = createContext({
  themePreference: ThemePreference.AUTO,
  isDarkTheme: false,
  // eslint-disable-next-line @typescript-eslint/no-empty-function, @typescript-eslint/no-unused-vars
  setThemePreference: (value: ThemePreference) => {},
});

export const ThemeProvider: React.FC = ({children}) => {
  const storageKey = 'theme-preference';
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [themePreference, setThemePreference] = useState<ThemePreference>(
    ThemePreference[localStorage.getItem(storageKey)] !== undefined
      ? localStorage.getItem(storageKey)
      : ThemePreference.AUTO,
  );
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const mediaQueryListener = (e: MediaQueryListEvent) => {
    if (themePreference === ThemePreference.AUTO) {
      setIsDarkTheme(e.matches);
    }
  };

  useEffect(() => {
    const browserPreference = mediaQuery.matches
      ? ThemePreference.DARK
      : ThemePreference.LIGHT;

    switch (themePreference) {
      case ThemePreference.LIGHT:
        localStorage.setItem(storageKey, ThemePreference.LIGHT);
        setIsDarkTheme(false);
        break;
      case ThemePreference.DARK:
        localStorage.setItem(storageKey, ThemePreference.DARK);
        setIsDarkTheme(true);
        break;
      case ThemePreference.AUTO:
        mediaQuery.addEventListener('change', mediaQueryListener);
        switch (browserPreference) {
          case ThemePreference.LIGHT:
            setIsDarkTheme(false);
            break;
          case ThemePreference.DARK:
            setIsDarkTheme(true);
            break;
        }
        localStorage.setItem(storageKey, ThemePreference.AUTO);

        return () => {
          mediaQuery.removeEventListener('change', mediaQueryListener);
        };
    }
  }, [themePreference]);

  useEffect(() => {
    document.documentElement.classList.toggle('pf-v5-theme-dark', isDarkTheme);
  }, [isDarkTheme]);

  return (
    <ThemeContext.Provider
      value={{themePreference, isDarkTheme, setThemePreference}}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
