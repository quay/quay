import {useEffect, useState} from 'react';
import {useQuayConfig} from './UseQuayConfig';

const TRUSTARC_STAGE_URL =
  'https://static.redhat.com/libs/redhat/marketing/latest/trustarc/trustarc.stage.js';
const TRUSTARC_PROD_URL =
  'https://static.redhat.com/libs/redhat/marketing/latest/trustarc/trustarc.js';

const DPAL_STAGE_URL = 'https://www.redhat.com/ma/dpal-staging.js';
const DPAL_PROD_URL = 'https://www.redhat.com/ma/dpal.js';

export function useAnalytics() {
  const quayConfig = useQuayConfig();
  const [analyticsAdded, setAnalyticsAdded] = useState<boolean>(false);

  useEffect(() => {
    const host = quayConfig?.config?.SERVER_HOSTNAME;

    // analytics only for quay.io
    if (!host || (host != 'quay.io' && host != 'stage.quay.io')) {
      return;
    }

    // analytics already added
    if (analyticsAdded) {
      return;
    }

    const trustarcScript = document.createElement('script');
    const dpalScript = document.createElement('script');

    trustarcScript.type = 'text/javascript';
    dpalScript.type = 'text/javascript';

    if (host == 'stage.quay.io') {
      dpalScript.src = DPAL_STAGE_URL;
      trustarcScript.src = TRUSTARC_STAGE_URL;
    } else if (host == 'quay.io') {
      dpalScript.src = DPAL_PROD_URL;
      trustarcScript.src = TRUSTARC_PROD_URL;
    }

    document.head.insertBefore(dpalScript, document.head.firstChild);
    document.head.insertBefore(trustarcScript, document.head.firstChild);

    const footerScript = document.createElement('script');
    footerScript.type = 'text/javascript';
    footerScript.textContent = `if (("undefined" !== typeof _satellite) && ("function" === typeof _satellite.pageBottom)) {
                _satellite.pageBottom();
        }`;
    document.body.appendChild(footerScript);
    setAnalyticsAdded(true);
  }, [quayConfig]);
}
