import {useState} from 'react';
import {Link, useNavigate, useSearchParams} from 'react-router-dom';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  Alert,
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
} from '@patternfly/react-core';
import {
  ArrowLeftIcon,
  CreditCardIcon,
  ChevronDownIcon,
  LockIcon,
} from '@patternfly/react-icons';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {getPlanInformationPath, summarizeSampleCard} from 'src/libs/billing';
import type {SampleCardDetails} from 'src/libs/billing';
import {
  addPrototypePaymentMethod,
  fetchPrototypePaymentMethods,
  selectPrototypePaymentMethod,
} from 'src/resources/PrototypeBillingResource';
import type {BillingCard} from 'src/resources/BillingResource';
import {setSubscription} from 'src/resources/BillingResource';
import merchantLogo from 'src/assets/stripe-checkout/redhat-merchant.png';
import applePayLogo from 'src/assets/stripe-checkout/apple-pay.png';
import linkLogo from 'src/assets/stripe-checkout/link.png';
import cardBrands from 'src/assets/stripe-checkout/card-brands.png';
import googlePayLogo from 'src/assets/stripe-checkout/google-pay.png';
import securityCodeImage from 'src/assets/stripe-checkout/security-code.png';
import flagImage from 'src/assets/stripe-checkout/us-flag.png';
import './StripeCheckoutPreview.css';

type Props = {organizationName: string};
type PaymentChange = {card: BillingCard} | {id: string};

export function StripeCheckoutPreview({organizationName}: Props) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const checkoutPlan = searchParams.get('checkoutPlan');
  const queryClient = useQueryClient();
  const {user} = useCurrentUser();
  const {isUserOrganization} = useOrganization(organizationName);
  const org = isUserOrganization ? null : organizationName;
  const {currentPlan, plans} = useUpgradePlan(
    organizationName,
    !isUserOrganization,
  );
  const currentDetail = plans.find(
    (plan) => plan.stripeId === (checkoutPlan ?? currentPlan?.plan),
  );
  const {data: saved} = useQuery(
    ['prototype-payment-methods', organizationName],
    () => fetchPrototypePaymentMethods(org),
    {enabled: process.env.MOCK_API === 'true', retry: false},
  );
  const savedCard =
    saved?.methods.find((method) => method.id === saved.defaultId) ??
    saved?.methods[0];
  const [details, setDetails] = useState<SampleCardDetails>({
    owner: '',
    number: '',
    expiry: '',
    securityCode: '',
  });
  const [country, setCountry] = useState('US');
  const [postalCode, setPostalCode] = useState('');
  const [phone, setPhone] = useState('');
  const [saveWithLink, setSaveWithLink] = useState(true);
  const [paymentType, setPaymentType] = useState<'card' | 'google'>('card');
  const [wallet, setWallet] = useState<'Apple Pay' | 'Link' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const backPath = getPlanInformationPath(organizationName);
  const update = useMutation({
    mutationFn: async (value: PaymentChange) => {
      if (checkoutPlan && !currentDetail)
        throw new Error('The selected plan is unavailable.');
      if ('card' in value) await addPrototypePaymentMethod(value.card, org);
      else await selectPrototypePaymentMethod(value.id, org);
      if (checkoutPlan) await setSubscription(checkoutPlan, org);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries(['card', organizationName]),
        queryClient.invalidateQueries([
          'prototype-payment-methods',
          organizationName,
        ]),
        queryClient.invalidateQueries(['organization', org, 'plan']),
        queryClient.invalidateQueries(['privateallowed', organizationName]),
      ]);
      navigate(backPath);
    },
  });
  const setField = (field: keyof SampleCardDetails, value: string) => {
    setError(null);
    setDetails((previous) => ({...previous, [field]: value}));
  };
  const save = (event: React.FormEvent) => {
    event.preventDefault();
    if (paymentType === 'google') {
      if (savedCard) update.mutate({id: savedCard.id});
      else setError('Add a sample card before using a wallet.');
      return;
    }
    const summary = summarizeSampleCard(details);
    if (summary.error) {
      setError(summary.error);
      return;
    }
    if (
      !postalCode.trim() ||
      (country === 'US' && !/^\d{5}(-\d{4})?$/.test(postalCode))
    ) {
      setError(
        country === 'US'
          ? 'Enter a valid ZIP code.'
          : 'Enter your postal code.',
      );
      return;
    }
    update.mutate({card: summary.card});
  };

  return (
    <main className="stripe-checkout" data-testid="stripe-checkout-page">
      <section
        className="stripe-checkout-summary"
        aria-label="Current subscription"
      >
        <div className="stripe-checkout-summary-inner">
          <Link
            className="stripe-checkout-merchant"
            to={backPath}
            aria-label="Back to Plan information"
          >
            <ArrowLeftIcon className="stripe-checkout-back" />
            <img src={merchantLogo} alt="Red Hat" />
            <span>Red Hat, Inc</span>
          </Link>
          <div className="stripe-checkout-plan-summary">
            <h1>
              {checkoutPlan
                ? `Subscribe to ${currentDetail?.title ?? 'selected plan'}`
                : 'Update payment method'}
            </h1>
            <div className="stripe-checkout-price">
              <span>
                {currentDetail
                  ? `$${(currentDetail.price / 100).toFixed(2)}`
                  : '—'}
              </span>
              <span className="stripe-checkout-price-period">
                per
                <br />
                month
              </span>
            </div>
            {!checkoutPlan && (
              <p className="stripe-checkout-plan-name">
                {currentDetail?.title ?? 'Current'} plan
              </p>
            )}
          </div>
        </div>
      </section>
      <section className="stripe-checkout-payment" aria-label="Checkout">
        <div className="stripe-checkout-form-container">
          <div className="stripe-checkout-wallets">
            <button
              type="button"
              className="stripe-checkout-wallet stripe-checkout-apple"
              aria-label="Apple Pay"
              onClick={() => setWallet('Apple Pay')}
            >
              <img src={applePayLogo} alt="Apple Pay" />
            </button>
            <button
              type="button"
              className="stripe-checkout-wallet stripe-checkout-link"
              aria-label="Pay with Link"
              onClick={() => setWallet('Link')}
            >
              <img src={linkLogo} alt="Link" />
            </button>
          </div>
          <div className="stripe-checkout-divider">
            <span>OR</span>
          </div>
          <form className="stripe-checkout-form" noValidate onSubmit={save}>
            <section className="stripe-checkout-contact">
              <h2>Contact information</h2>
              <div className="stripe-checkout-email-row">
                <label htmlFor="stripe-contact-email">Email</label>
                <input
                  id="stripe-contact-email"
                  type="email"
                  readOnly
                  value={user?.email ?? ''}
                />
              </div>
            </section>
            <section className="stripe-checkout-method-section">
              <h2>Payment method</h2>
              <fieldset className="stripe-checkout-methods">
                <legend className="stripe-checkout-sr-only">
                  Payment method
                </legend>
                <div className="stripe-checkout-card-option">
                  <label className="stripe-checkout-method-label">
                    <input
                      type="radio"
                      name="checkout-payment-method"
                      checked={paymentType === 'card'}
                      onChange={() => {
                        setPaymentType('card');
                        setError(null);
                      }}
                    />
                    <CreditCardIcon />
                    <span>Card</span>
                  </label>
                  {paymentType === 'card' && (
                    <div className="stripe-checkout-card-fields">
                      <label htmlFor="stripe-card-number">
                        Card information
                      </label>
                      <div className="stripe-checkout-input-group stripe-checkout-card-group">
                        <div className="stripe-checkout-number-field">
                          <input
                            id="stripe-card-number"
                            aria-label="Card number"
                            placeholder="1234 1234 1234 1234"
                            inputMode="numeric"
                            autoComplete="off"
                            value={details.number}
                            onChange={(event) =>
                              setField('number', event.target.value)
                            }
                            maxLength={23}
                            disabled={update.isLoading}
                          />
                          <img
                            className="stripe-checkout-card-brands"
                            src={cardBrands}
                            alt="Visa, Mastercard, American Express and JCB"
                          />
                        </div>
                        <div className="stripe-checkout-card-bottom">
                          <input
                            aria-label="Expiration date"
                            placeholder="MM / YY"
                            autoComplete="off"
                            value={details.expiry}
                            onChange={(event) =>
                              setField('expiry', event.target.value)
                            }
                            maxLength={7}
                            disabled={update.isLoading}
                          />
                          <div className="stripe-checkout-cvc-field">
                            <input
                              aria-label="Security code"
                              placeholder="CVC"
                              type="password"
                              inputMode="numeric"
                              autoComplete="off"
                              value={details.securityCode}
                              onChange={(event) =>
                                setField('securityCode', event.target.value)
                              }
                              maxLength={4}
                              disabled={update.isLoading}
                            />
                            <img
                              src={securityCodeImage}
                              alt="Security code on the back of your card"
                            />
                          </div>
                        </div>
                      </div>
                      <label htmlFor="stripe-card-owner">Cardholder name</label>
                      <input
                        id="stripe-card-owner"
                        className="stripe-checkout-single-input"
                        placeholder="Full name on card"
                        autoComplete="off"
                        value={details.owner}
                        onChange={(event) =>
                          setField('owner', event.target.value)
                        }
                        disabled={update.isLoading}
                      />
                      <label htmlFor="stripe-country">Country or region</label>
                      <div className="stripe-checkout-input-group stripe-checkout-address-group">
                        <div className="stripe-checkout-country-field">
                          <select
                            id="stripe-country"
                            value={country}
                            onChange={(event) => {
                              setCountry(event.target.value);
                              setPostalCode('');
                              setError(null);
                            }}
                            disabled={update.isLoading}
                          >
                            <option value="US">United States</option>
                            <option value="CA">Canada</option>
                            <option value="GB">United Kingdom</option>
                            <option value="DE">Germany</option>
                            <option value="FR">France</option>
                            <option value="IN">India</option>
                          </select>
                          <ChevronDownIcon />
                        </div>
                        <input
                          aria-label={country === 'US' ? 'ZIP' : 'Postal code'}
                          placeholder={country === 'US' ? 'ZIP' : 'Postal code'}
                          value={postalCode}
                          onChange={(event) => {
                            setPostalCode(event.target.value);
                            setError(null);
                          }}
                          autoComplete="off"
                          disabled={update.isLoading}
                        />
                      </div>
                      <label className="stripe-checkout-link-opt-in">
                        <input
                          type="checkbox"
                          checked={saveWithLink}
                          onChange={(event) =>
                            setSaveWithLink(event.target.checked)
                          }
                          disabled={update.isLoading}
                        />
                        <span>
                          Save my information with{' '}
                          <button
                            type="button"
                            onClick={() => setWallet('Link')}
                          >
                            Link
                          </button>{' '}
                          for faster checkout
                        </span>
                      </label>
                      {saveWithLink && (
                        <>
                          <label htmlFor="stripe-phone">Phone number</label>
                          <div className="stripe-checkout-phone-field">
                            <img src={flagImage} alt="United States" />
                            <input
                              id="stripe-phone"
                              type="tel"
                              placeholder="(201) 555-0123"
                              value={phone}
                              onChange={(event) => setPhone(event.target.value)}
                              autoComplete="off"
                              disabled={update.isLoading}
                            />
                          </div>
                          <p className="stripe-checkout-link-terms">
                            By saving, you agree to Link’s{' '}
                            <button
                              type="button"
                              onClick={() => setWallet('Link')}
                            >
                              Terms
                            </button>{' '}
                            and{' '}
                            <button
                              type="button"
                              onClick={() => setWallet('Link')}
                            >
                              Privacy
                            </button>
                            .
                          </p>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="stripe-checkout-google-option">
                  <label className="stripe-checkout-method-label">
                    <input
                      type="radio"
                      name="checkout-payment-method"
                      checked={paymentType === 'google'}
                      onChange={() => {
                        setPaymentType('google');
                        setError(null);
                      }}
                    />
                    <img src={googlePayLogo} alt="" />
                    <span>Google Pay</span>
                  </label>
                  {paymentType === 'google' && (
                    <div className="stripe-checkout-wallet-card">
                      {savedCard
                        ? `${savedCard.type} ending in ${savedCard.last4}`
                        : 'No saved card available.'}
                    </div>
                  )}
                </div>
              </fieldset>
            </section>
            {(error || update.isError) && (
              <Alert
                isInline
                variant="danger"
                title={
                  error ??
                  'Unable to update your payment method. Please try again.'
                }
                className="stripe-checkout-error"
              />
            )}
            <button
              className="stripe-checkout-submit"
              type="submit"
              disabled={update.isLoading}
            >
              {update.isLoading
                ? 'Saving…'
                : checkoutPlan
                ? 'Subscribe'
                : 'Save payment method'}
            </button>
            <Link className="stripe-checkout-cancel" to={backPath}>
              Cancel
            </Link>
            <p className="stripe-checkout-footer">
              <LockIcon /> Secure checkout <span>Sample payment flow</span>
            </p>
          </form>
        </div>
      </section>
      <Modal
        variant={ModalVariant.small}
        isOpen={!!wallet}
        onClose={() => {
          if (!update.isLoading) setWallet(null);
        }}
        aria-labelledby="checkout-wallet-title"
      >
        <ModalHeader title={wallet ?? ''} labelId="checkout-wallet-title" />
        <ModalBody>
          <p>
            {savedCard
              ? `Use your sample ${savedCard.type} ending in ${savedCard.last4}.`
              : 'Add a sample card to try this wallet.'}
          </p>
          {update.isError && (
            <Alert
              isInline
              variant="danger"
              title="Unable to save your payment method."
            />
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="primary"
            isDisabled={!savedCard || update.isLoading}
            isLoading={update.isLoading}
            onClick={() => {
              if (savedCard) update.mutate({id: savedCard.id});
            }}
          >
            Use sample card
          </Button>
          <Button
            variant="link"
            isDisabled={update.isLoading}
            onClick={() => setWallet(null)}
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </main>
  );
}
