import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useTheme} from 'src/contexts/ThemeContext';

export function useLogo(): string {
  const branding = useQuayConfig()?.config?.BRANDING;
  const {isDarkTheme} = useTheme();

  if (isDarkTheme && branding?.logo_dark) {
    return branding.logo_dark;
  }

  return branding?.logo || '';
}
