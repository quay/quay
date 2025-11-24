import {useEffect, useState} from 'react';
import {useQuayConfig} from './UseQuayConfig';

// Module-level shared state to prevent duplicate script loading across multiple hook instances
const loadedScripts = new Set<string>();
const loadingPromises = new Map<string, Promise<void>>();

/**
 * Dynamically loads external scripts (Stripe, StatusPage) only when BILLING feature is enabled.
 * This prevents blocking page load in air-gapped/restricted environments where these external
 * resources are unreachable.
 *
 * Uses module-level shared state to ensure scripts are loaded only once, even when multiple
 * components use this hook simultaneously.
 */
export function useExternalScripts() {
  const config = useQuayConfig();
  const [statusPageLoaded, setStatusPageLoaded] = useState(false);

  useEffect(() => {
    // Only load external scripts when BILLING feature is enabled (quay.io deployments)
    if (!config?.features?.BILLING) {
      return;
    }

    /**
     * Dynamically inject a script tag into the document head
     * @param src - Script source URL
     * @param id - Unique identifier for the script element
     * @param onload - Optional callback when script loads successfully
     */
    const loadScript = async (
      src: string,
      id: string,
      onload?: () => void,
    ): Promise<void> => {
      // If already fully loaded, call callback immediately
      if (loadedScripts.has(id)) {
        if (onload) onload();
        return;
      }

      // If script element exists in DOM (loaded by another instance), wait for it
      const existingScript = document.getElementById(id);
      if (existingScript) {
        loadedScripts.add(id);
        if (onload) onload();
        return;
      }

      // If another instance is currently loading this script, wait for that promise
      if (loadingPromises.has(id)) {
        await loadingPromises.get(id);
        if (onload) onload();
        return;
      }

      // Create new loading promise
      const loadPromise = new Promise<void>((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.id = id;
        script.async = true; // Non-blocking load
        script.onload = () => {
          loadedScripts.add(id);
          loadingPromises.delete(id);
          resolve();
        };
        script.onerror = () => {
          console.warn(`Failed to load external script: ${src}`);
          loadingPromises.delete(id);
          reject(new Error(`Failed to load script: ${src}`));
        };

        document.head.appendChild(script);
      });

      loadingPromises.set(id, loadPromise);

      try {
        await loadPromise;
        if (onload) onload();
      } catch (error) {
        // Script loading failed, but don't throw - just log
        console.error(error);
      }
    };

    // Load scripts (non-blocking, parallel)
    loadScript('https://checkout.stripe.com/checkout.js', 'stripe-checkout');
    loadScript(
      'https://cdn.statuspage.io/se-v2.js',
      'statuspage-widget',
      () => {
        setStatusPageLoaded(true);
      },
    );

    // Cleanup: reset local state when component unmounts
    return () => {
      setStatusPageLoaded(false);
    };
  }, [config?.features?.BILLING]);

  return {statusPageLoaded};
}
