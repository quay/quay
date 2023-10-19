import {useEffect, useState} from 'react';
import {
  Flex,
  FormGroup,
  Form,
  FormAlert,
  TextInput,
  FormSelect,
  FormSelectOption,
  ActionGroup,
  Button,
  Alert,
  Grid,
  GridItem,
  FormHelperText,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {IOrganization} from 'src/resources/OrganizationResource';
import {humanizeTimeForExpiry, getSeconds, isValidEmail} from 'src/libs/utils';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import Alerts from 'src/routes/Alerts';

type validate = 'success' | 'warning' | 'error' | 'default';
const timeMachineOptions = {
  '0s': 'a few seconds',
  '1d': 'a day',
  '1w': '7 days',
  '2w': '14 days',
  '4w': 'a month',
};

type GeneralSettingsProps = {
  organizationName: string;
};

export const GeneralSettings = (props: GeneralSettingsProps) => {
  const quayConfig = useQuayConfig();
  const organizationName = props.organizationName;
  const {user, loading: isUserLoading} = useCurrentUser();
  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);
  const [error, setError] = useState<string>('');
  const {addAlert} = useAlerts();

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: (result) => {
      addAlert({
        title: 'Successfully updated settings',
        variant: AlertVariant.Success,
        key: 'alert',
      });
    },
    onError: (err) => {
      addAlert({
        title: err.response.data.error_message,
        variant: AlertVariant.Failure,
        key: 'alert',
      });
    },
  });

  const {updateUser} = useUpdateUser({
    onSuccess: (result) => {
      addAlert({
        title: 'Successfully updated settings',
        variant: AlertVariant.Success,
        key: 'alert',
      });
    },
    onError: (err) => {
      addAlert({
        title: err.response.data.error_message,
        variant: AlertVariant.Failure,
        key: 'alert',
      });
    },
  });

  // Time Machine
  const [timeMachineFormValue, setTimeMachineFormValue] = useState(
    timeMachineOptions[quayConfig?.config?.TAG_EXPIRATION_OPTIONS[0]],
  );
  const namespaceTimeMachineExpiry = isUserOrganization
    ? user?.tag_expiration_s
    : (organization as IOrganization)?.tag_expiration_s;

  // Email
  const namespaceEmail = isUserOrganization
    ? user?.email || ''
    : organization?.email || '';
  const [emailFormValue, setEmailFormValue] = useState<string>('');
  const [fullNameValue, setFullNameValue] = useState<string>(null);
  const [companyValue, setCompanyValue] = useState<string>(null);
  const [locationValue, setLocationValue] = useState<string>(null);
  const [validated, setValidated] = useState<validate>('default');

  useEffect(() => {
    setEmailFormValue(namespaceEmail);
    setFullNameValue(user?.family_name || null);
    setCompanyValue(user?.company || null);
    setLocationValue(user?.location || null);
    const humanized_expiry = humanizeTimeForExpiry(namespaceTimeMachineExpiry);
    for (const key of Object.keys(timeMachineOptions)) {
      if (humanized_expiry == timeMachineOptions[key]) {
        setTimeMachineFormValue(key);
        break;
      }
    }
  }, [loading, isUserLoading, isUserOrganization]);

  const handleEmailChange = (emailFormValue: string) => {
    setEmailFormValue(emailFormValue);
    if (namespaceEmail == emailFormValue) {
      setValidated('default');
      setError('');
      return;
    }

    if (!emailFormValue) {
      setValidated('error');
      setError('Please enter email associate with namespace');
      return;
    }

    if (namespaceEmail != emailFormValue) {
      if (isValidEmail(emailFormValue)) {
        setValidated('success');
        setError('');
      } else {
        setValidated('error');
        setError('Please enter a valid email address');
      }
    }
  };

  const checkForChanges = () => {
    if (!isUserOrganization && namespaceEmail != emailFormValue) {
      return validated == 'success';
    }

    return (
      (getSeconds(timeMachineFormValue) != namespaceTimeMachineExpiry ||
        namespaceEmail != emailFormValue ||
        user?.family_name != fullNameValue ||
        user?.company != companyValue ||
        user?.location != locationValue) &&
      validated != 'error'
    );
  };

  const updateSettings = async () => {
    try {
      if (!isUserOrganization) {
        const response = await updateOrgSettings({
          tag_expiration_s:
            getSeconds(timeMachineFormValue) != namespaceTimeMachineExpiry
              ? getSeconds(timeMachineFormValue)
              : null,
          email: namespaceEmail != emailFormValue ? emailFormValue : null,
          isUser: isUserOrganization,
        });
        return response;
      } else {
        const response = await updateUser({
          email: emailFormValue.trim(),
          company: companyValue.trim(),
          location: locationValue.trim(),
          family_name: fullNameValue.trim(),
        });
        return response;
      }
    } catch (error) {
      addDisplayError('Unable to update namespace settings', error);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    updateSettings();
  };

  return (
    <Form id="form-form" maxWidth="70%">
      {validated === 'error' && (
        <FormAlert>
          <Alert variant="danger" title={error} aria-live="polite" isInline />
        </FormAlert>
      )}
      <FormGroup isInline label="Organization" fieldId="form-organization">
        <TextInput
          isDisabled
          type="text"
          id="form-name"
          value={organizationName}
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Namespace names cannot be changed once set.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <FormGroup isInline label="Email" fieldId="form-email">
        <TextInput
          type="email"
          id="org-settings-email"
          value={emailFormValue}
          onChange={(_event, emailFormValue) =>
            handleEmailChange(emailFormValue)
          }
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              The e-mail address associated with the organization.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      {isUserOrganization && quayConfig?.features.USER_METADATA === true && (
        <Grid hasGutter>
          <GridItem span={6}>
            <FormGroup
              isInline
              label="Full Name"
              fieldId="org-settings-fullname"
            >
              <TextInput
                type="text"
                id="org-settings-fullname"
                value={fullNameValue}
                onChange={(_, value) => {
                  setFullNameValue(value);
                }}
              />
            </FormGroup>
          </GridItem>

          <GridItem span={6}>
            <FormGroup isInline label="Company" fieldId="company">
              <TextInput
                type="text"
                id="org-settings-company"
                value={companyValue}
                onChange={(_, value) => {
                  setCompanyValue(value);
                }}
              />
            </FormGroup>
          </GridItem>

          <GridItem span={6}>
            <FormGroup isInline label="Location" fieldId="location">
              <TextInput
                type="text"
                id="org-settings-location"
                value={locationValue}
                onChange={(_, value) => {
                  setLocationValue(value);
                }}
              />
            </FormGroup>
          </GridItem>
        </Grid>
      )}

      <FormGroup isInline label="Time Machine" fieldId="form-time-machine">
        <FormSelect
          placeholder="Time Machine"
          aria-label="Time Machine select"
          data-testid="arch-select"
          value={timeMachineFormValue}
          onChange={(_, val) => setTimeMachineFormValue(val)}
        >
          {quayConfig?.config?.TAG_EXPIRATION_OPTIONS.map((option, index) => (
            <FormSelectOption
              key={index}
              value={option}
              label={timeMachineOptions[option]}
            />
          ))}
        </FormSelect>

        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              The amount of time, after a tag is deleted, that the tag is
              accessible in time machine before being garbage collected.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
        >
          <Button
            id="save-org-settings"
            variant="primary"
            type="submit"
            onClick={(event) => onSubmit(event)}
            isDisabled={!checkForChanges()}
          >
            Save
          </Button>
        </Flex>
      </ActionGroup>
      <Alerts />
    </Form>
  );
};
