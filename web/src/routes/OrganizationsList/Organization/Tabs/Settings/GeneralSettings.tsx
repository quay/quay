import {
  ActionGroup,
  Alert,
  Button,
  Flex,
  Form,
  FormAlert,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  Grid,
  GridItem,
  HelperText,
  HelperTextItem,
  TextInput,
} from '@patternfly/react-core';
import moment from 'moment';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {
  humanizeTimeForExpiry,
  isValidEmail,
  parseTimeDuration,
} from 'src/libs/utils';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {IOrganization} from 'src/resources/OrganizationResource';
import {UpdateUserRequest} from 'src/resources/UserResource';
import Alerts from 'src/routes/Alerts';

type validate = 'success' | 'warning' | 'error' | 'default';
const normalize = (value) => (value === null ? '' : value);

type GeneralSettingsProps = {
  organizationName: string;
};

export const GeneralSettings = (props: GeneralSettingsProps) => {
  const quayConfig = useQuayConfig();
  const [timeMachineOptions, setTimeMachineOptions] = useState<{
    [key: string]: string;
  }>({});
  const organizationName = props.organizationName;
  const {user, loading: isUserLoading} = useCurrentUser();
  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);
  const [error, setError] = useState<string>('');
  const {addAlert} = useAlerts();

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: () => {
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
    onSuccess: () => {
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

  useEffect(() => {
    if (quayConfig?.config?.TAG_EXPIRATION_OPTIONS) {
      const options = quayConfig.config.TAG_EXPIRATION_OPTIONS.reduce(
        (acc: {[key: string]: string}, option: string) => {
          const duration = parseTimeDuration(option);
          if (duration.isValid()) {
            acc[option] = humanizeTimeForExpiry(duration);
          }

          return acc;
        },
        {},
      );
      setTimeMachineOptions(options);
    }
  }, [quayConfig]);

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
    for (const key of Object.keys(timeMachineOptions)) {
      const optionSeconds = parseTimeDuration(key).asSeconds();

      if (optionSeconds === namespaceTimeMachineExpiry) {
        setTimeMachineFormValue(optionSeconds.toString());
        break;
      }
    }
  }, [loading, isUserLoading, isUserOrganization, timeMachineOptions]);

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
    if (
      !isUserOrganization &&
      normalize(namespaceEmail) != normalize(emailFormValue)
    ) {
      return validated == 'success';
    }

    return (
      (moment.duration(timeMachineFormValue, 'seconds').asSeconds() !=
        namespaceTimeMachineExpiry ||
        normalize(namespaceEmail) != normalize(emailFormValue) ||
        normalize(user?.family_name) != normalize(fullNameValue) ||
        normalize(user?.company) != normalize(companyValue) ||
        normalize(user?.location) != normalize(locationValue)) &&
      validated != 'error'
    );
  };

  const updateSettings = async () => {
    try {
      if (!isUserOrganization) {
        const response = await updateOrgSettings({
          tag_expiration_s:
            moment.duration(timeMachineFormValue, 'seconds') !=
            moment.duration(namespaceTimeMachineExpiry, 'seconds')
              ? moment.duration(timeMachineFormValue, 'seconds').asSeconds()
              : null,
          email: namespaceEmail != emailFormValue ? emailFormValue : null,
          isUser: isUserOrganization,
        });
        return response;
      } else {
        let updateRequest: UpdateUserRequest = {
          email: normalize(emailFormValue).trim(),
          company: normalize(companyValue).trim(),
          location: normalize(locationValue).trim(),
          family_name: normalize(fullNameValue).trim(),
        };

        if (quayConfig?.features?.CHANGE_TAG_EXPIRATION) {
          updateRequest = {
            ...updateRequest,
            tag_expiration_s:
              moment.duration(timeMachineFormValue, 'seconds') !=
              moment.duration(namespaceTimeMachineExpiry, 'seconds')
                ? moment.duration(timeMachineFormValue, 'seconds').asSeconds()
                : null,
          };
        }
        const response = await updateUser(updateRequest);
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
              label="Full name"
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

      {quayConfig?.features?.CHANGE_TAG_EXPIRATION && (
        <FormGroup isInline label="Time machine" fieldId="form-time-machine">
          <FormSelect
            placeholder="Time Machine"
            aria-label="Time Machine select"
            data-testid="tag-expiration-picker"
            value={timeMachineFormValue}
            onChange={(_, val) => setTimeMachineFormValue(val)}
          >
            {Object.entries(timeMachineOptions).map(([key, value], index) => (
              <FormSelectOption
                key={index}
                value={moment.duration(parseTimeDuration(key)).asSeconds()}
                label={value}
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
      )}

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
