import logo_dark from 'src/assets/quay.svg';
import logo_light from 'src/assets/logo.svg';
import rh_logo_dark from 'src/assets/RH_QuayIO2.svg';
import rh_logo_light from 'src/assets/RH_QuayIO.svg';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useTheme} from 'src/contexts/ThemeContext';

/**
 * Hook to determine the appropriate logo URL based on theme and configuration.
 *
 * Logo selection priority:
 * 1. If hostname is quay.io or stage.quay.io → theme-aware Red Hat branding
 * 2. Else if BRANDING.logo_dark is configured AND dark theme is active → use logo_dark
 * 3. Else if BRANDING.logo is configured → use logo
 * 4. Else (downstream default) → theme-aware default logo
 *
 * Note: Customers can configure BRANDING.logo_dark for theme-aware custom branding.
 *
 * @returns {string} The logo URL to display
 */
export function useLogo(): string {
  const quayConfig = useQuayConfig();
  const {isDarkTheme} = useTheme();

  // Priority 1: Special case for quay.io and stage.quay.io (Red Hat branding)
  if (
    window?.location?.hostname === 'stage.quay.io' ||
    window?.location?.hostname === 'quay.io'
  ) {
    return isDarkTheme ? rh_logo_dark : rh_logo_light;
  }

  // Priority 2 & 3: Check for custom branding configuration
  if (quayConfig?.config?.BRANDING) {
    // Use dark logo variant when theme is dark and logo_dark is configured
    if (isDarkTheme && quayConfig.config.BRANDING.logo_dark) {
      return quayConfig.config.BRANDING.logo_dark;
    }
    // Otherwise use the regular logo if configured
    if (quayConfig.config.BRANDING.logo) {
      return quayConfig.config.BRANDING.logo;
    }
  }

  // Priority 4: Default for downstream (self-hosted Quay)
  return isDarkTheme ? logo_dark : logo_light;
}
