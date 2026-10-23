export type ReceiptSettings = {
  invoice_email: boolean;
  invoice_email_address: string;
};

export function loadReceiptSettings(
  namespace: string,
  defaultEmail: string,
): ReceiptSettings {
  try {
    const saved = localStorage.getItem(
      `quay-receipt-settings-prototype-v1:${namespace}`,
    );
    if (saved) {
      const settings = JSON.parse(saved) as ReceiptSettings;
      if (
        typeof settings.invoice_email === 'boolean' &&
        typeof settings.invoice_email_address === 'string'
      )
        return settings;
    }
  } catch {
    // Start with the requested sample state when storage is unavailable.
  }
  return {invoice_email: true, invoice_email_address: defaultEmail};
}

export function saveReceiptSettings(
  namespace: string,
  settings: ReceiptSettings,
): void {
  localStorage.setItem(
    `quay-receipt-settings-prototype-v1:${namespace}`,
    JSON.stringify(settings),
  );
}
