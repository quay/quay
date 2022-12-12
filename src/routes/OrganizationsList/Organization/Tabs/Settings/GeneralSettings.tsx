import {useEffect, useState} from 'react';
import {
  Flex,
  FormGroup,
  Form,
  TextInput,
  FormSelect,
  FormSelectOption,
  ActionGroup,
  Button,
  FormAlert,
  Alert,
  Grid,
  GridItem,
} from '@patternfly/react-core';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useUpdateOrganization} from 'src/hooks/UseUpdateOrganization';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import moment from 'moment';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {AxiosError} from 'axios';
import {useUpdateUser} from 'src/hooks/UseUpdateUser';

export const GeneralSettings = () => {
  const location = useLocation();
  const organizationName = location.pathname.split('/')[2];

  const {user} = useCurrentUser();
  const {config} = useQuayConfig();

  const tagExpirationOptions = config.TAG_EXPIRATION_OPTIONS.map((option) => {
    const number = option.substring(0, option.length - 1);
    const suffix = option.substring(option.length - 1);
    return moment.duration(number, suffix).asSeconds();
  });

  type validate = 'success' | 'warning' | 'error' | 'default';
  const [validated, setValidated] = useState<validate>('success');

  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);

  const {
    updateOrganization,
    loading: organizationUpdateLoading,
    error: organizationUpdateError,
  } = useUpdateOrganization({
    onSuccess: () => {
      setTouched(false);
    },
    onError: (err) => {
      console.log(err);
    },
  });

  const {
    updateUser,
    loading: userUpdateLoading,
    error: userUpdateError,
  } = useUpdateUser({
    onSuccess: () => {
      setTouched(false);
    },
    onError: (err) => {
      console.log(err);
    },
  });

  const error = userUpdateError || organizationUpdateError;

  const updateLoading = userUpdateLoading || organizationUpdateLoading;

  // Time Machine
  const timeMachineOptions = tagExpirationOptions;
  const [timeMachineFormValue, setTimeMachineFormValue] = useState(
    timeMachineOptions[0],
  );

  const [touched, setTouched] = useState(false);

  // Email
  const [emailFormValue, setEmailFormValue] = useState('');
  const [fullName, setFullName] = useState('');
  const [userLocation, setUserLocation] = useState('');
  const [company, setCompany] = useState('');

  useEffect(() => {
    resetFields();
  }, [loading, isUserOrganization]);

  const resetFields = () => {
    if (!loading && organization) {
      setEmailFormValue(organization.email || '');
      setTimeMachineFormValue(organization.tag_expiration_s || 0);
    } else if (isUserOrganization) {
      setEmailFormValue(user.email || '');
      setTimeMachineFormValue(user.tag_expiration_s || 0);
      setFullName(user.family_name || '');
      setCompany(user.company || '');
      setUserLocation(user.location || '');
    }
    setTouched(false);
  };

  return (
    <Form id="form-form" maxWidth="90%">
      {error && touched && (
        <FormAlert>
          <Alert
            variant="danger"
            title={((error as AxiosError).response.data as any).error_message}
            // title="Error"
            aria-live="polite"
            isInline
          />
        </FormAlert>
      )}

      <Grid hasGutter>
        {!isUserOrganization && (
          <GridItem span={12}>
            <FormGroup
              isInline
              label="Organization"
              fieldId="form-organization"
              helperText={'Orgnization names cannot be changed once set.'}
            >
              <TextInput
                isDisabled
                type="text"
                id="form-name"
                value={organizationName}
              />
            </FormGroup>
          </GridItem>
        )}

        <GridItem span={isUserOrganization ? 6 : 12}>
          <FormGroup
            isInline
            label="Email"
            fieldId="form-email"
            validated={validated}
            helperTextInvalid="Must be an email"
            helperTextInvalidIcon={<ExclamationCircleIcon />}
          >
            <TextInput
              type="email"
              id="modal-with-form-form-name"
              isDisabled={!isUserOrganization && loading}
              value={emailFormValue}
              validated={validated}
              onChange={(val) => {
                setTouched(true);
                setEmailFormValue(val);
                if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(val)) {
                  setValidated('success');
                } else {
                  setValidated('error');
                }
              }}
            />
          </FormGroup>
        </GridItem>

        {isUserOrganization && (
          <>
            <GridItem span={6}>
              <FormGroup isInline label="Full Name" fieldId="full name">
                <TextInput
                  type="text"
                  id="fullName"
                  value={fullName}
                  onChange={(val) => {
                    setTouched(true);
                    setFullName(val);
                  }}
                />
              </FormGroup>
            </GridItem>
            <GridItem span={6}>
              <FormGroup isInline label="Location" fieldId="location">
                <TextInput
                  type="text"
                  id="location"
                  value={userLocation}
                  onChange={(val) => {
                    setTouched(true);
                    setUserLocation(val);
                  }}
                />
              </FormGroup>
            </GridItem>
            <GridItem span={6}>
              <FormGroup isInline label="Company" fieldId="company">
                <TextInput
                  type="text"
                  id="company"
                  value={company}
                  onChange={(val) => {
                    setTouched(true);
                    setCompany(val);
                  }}
                />
              </FormGroup>
            </GridItem>
          </>
        )}

        <GridItem span={12}>
          <FormGroup
            isInline
            label="Time Machine"
            fieldId="form-time-machine"
            helperText="The amount of time, after a tag is deleted, that the tag is accessible in time machine before being garbage collected."
          >
            <FormSelect
              placeholder="Time Machine"
              aria-label="Time Machine select"
              data-testid="arch-select"
              value={timeMachineFormValue}
              onChange={(val) => {
                setTouched(true);
                setTimeMachineFormValue(parseInt(val));
              }}
            >
              {timeMachineOptions.map((option, index) => (
                <FormSelectOption
                  key={index}
                  value={option}
                  label={moment.duration(option || 0, 's').humanize()}
                />
              ))}
            </FormSelect>
          </FormGroup>
        </GridItem>
      </Grid>

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
        >
          <Button
            variant="primary"
            isLoading={updateLoading}
            isDisabled={!touched || validated == 'error'}
            onClick={() => {
              if (isUserOrganization) {
                updateUser(organizationName, {
                  company,
                  location: userLocation,
                  family_name: fullName,
                  email: emailFormValue,
                  tag_expiration_s: timeMachineFormValue,
                });
              } else {
                updateOrganization(organizationName, {
                  email: emailFormValue,
                  tag_expiration_s: timeMachineFormValue,
                });
              }
            }}
          >
            Save
          </Button>
          <Button
            variant="link"
            onClick={() => resetFields()}
            isDisabled={!touched}
          >
            Cancel
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
};
