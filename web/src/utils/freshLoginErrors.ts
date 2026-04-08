/**
 * Checks if error message is from fresh login verification.
 * Used to prevent duplicate error alerts in modals.
 */
export function isFreshLoginError(errorMessage: string): boolean {
  return (
    errorMessage === 'Fresh login verification cancelled' ||
    errorMessage === 'Verification canceled' ||
    errorMessage === 'Invalid verification credentials' ||
    errorMessage === 'Invalid Username or Password'
  );
}
