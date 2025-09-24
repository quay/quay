import {
  ActionGroup,
  Button,
  Flex,
  FlexItem,
  Form,
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
import {useForm, Controller} from 'react-hook-form';
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
import Avatar from 'src/components/Avatar';
import ChangePasswordModal from 'src/components/modals/ChangePasswordModal';
import ChangeAccountTypeModal from 'src/components/modals/ChangeAccountTypeModal';
import DesktopNotificationsModal from 'src/components/modals/DesktopNotificationsModal';
import DeleteAccountModal from 'src/components/modals/DeleteAccountModal';
import {getCookie, setPermanentCookie} from 'src/libs/cookieUtils';
import {useDeleteAccount} from 'src/hooks/UseDeleteAccount';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';

// Form data interface for react-hook-form
interface GeneralSettingsFormData {
  email: string;
  fullName: string;
  company: string;
  location: string;
  tagExpirationS: string;
  desktopNotifications: boolean;
}

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

  // Initialize react-hook-form
  const {
    control,
    handleSubmit,
    formState: {errors, isDirty, isValid},
    reset,
    setValue,
  } = useForm<GeneralSettingsFormData>({
    mode: 'onChange',
    defaultValues: {
      email: '',
      fullName: '',
      company: '',
      location: '',
      tagExpirationS: '', // Will be set properly in useEffect when data loads
      desktopNotifications: false,
    },
  });

  // Time Machine
  const namespaceTimeMachineExpiry = isUserOrganization
    ? user?.tag_expiration_s
    : (organization as IOrganization)?.tag_expiration_s;

  // Email
  const namespaceEmail = isUserOrganization
    ? user?.email || ''
    : organization?.email || '';

  // Password modal state
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  // Account type modal state
  const [isAccountTypeModalOpen, setIsAccountTypeModalOpen] = useState(false);

  // Desktop notifications state
  const [notificationsModalOpen, setNotificationsModalOpen] = useState(false);
  const [pendingNotificationChange, setPendingNotificationChange] = useState<
    boolean | null
  >(null);
  const [browserPermissionDenied, setBrowserPermissionDenied] = useState(false);
  // Delete account state
  const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState(false);

  useEffect(() => {
    // Don't initialize until timeMachineOptions is loaded
    if (Object.keys(timeMachineOptions).length === 0) {
      return;
    }

    // Find the correct time machine option
    let tagExpirationValue =
      quayConfig?.config?.TAG_EXPIRATION_OPTIONS?.[0] || '';

    for (const key of Object.keys(timeMachineOptions)) {
      const optionSeconds = parseTimeDuration(key).asSeconds();
      if (optionSeconds === namespaceTimeMachineExpiry) {
        tagExpirationValue = optionSeconds.toString(); // Convert to string to match FormSelectOption values
        break;
      }
    }

    // Reset form with actual data
    reset({
      email: namespaceEmail,
      fullName: user?.family_name || '',
      company: user?.company || '',
      location: user?.location || '',
      tagExpirationS: tagExpirationValue,
      desktopNotifications: false, // Will be set by initializeNotificationsState
    });

    // Initialize desktop notifications state
    initializeNotificationsState();
  }, [
    loading,
    isUserLoading,
    isUserOrganization,
    timeMachineOptions,
    reset,
    namespaceEmail,
    user,
    namespaceTimeMachineExpiry,
    quayConfig,
  ]);

  const initializeNotificationsState = () => {
    // Check if browser notifications are supported and not denied
    if (typeof window !== 'undefined' && window.Notification) {
      const browserPermissionDenied =
        window.Notification.permission === 'denied';
      setBrowserPermissionDenied(browserPermissionDenied);

      // Check cookie state and browser permission
      const cookieEnabled =
        getCookie('quay.enabledDesktopNotifications') === 'on';
      const browserGranted = window.Notification.permission === 'granted';

      setValue('desktopNotifications', cookieEnabled && browserGranted);
    } else {
      setBrowserPermissionDenied(true);
      setValue('desktopNotifications', false);
    }
  };

  const handleNotificationToggle = (checked: boolean) => {
    if (browserPermissionDenied) {
      return; // Cannot toggle if browser permission is denied
    }

    setPendingNotificationChange(checked);
    setNotificationsModalOpen(true);
  };

  const handleNotificationConfirm = async () => {
    if (pendingNotificationChange === null) return;

    const enabling = pendingNotificationChange;

    if (enabling) {
      // Turning ON notifications
      if (window.Notification && window.Notification.permission === 'default') {
        // Request permission first
        try {
          const permission = await window.Notification.requestPermission();
          if (permission === 'granted') {
            setPermanentCookie('quay.enabledDesktopNotifications', 'on');
            setValue('desktopNotifications', true);
          } else {
            setBrowserPermissionDenied(permission === 'denied');
            setValue('desktopNotifications', false);
          }
        } catch (error) {
          console.error('Error requesting notification permission:', error);
          setValue('desktopNotifications', false);
        }
      } else if (
        window.Notification &&
        window.Notification.permission === 'granted'
      ) {
        // Permission already granted, just enable
        setPermanentCookie('quay.enabledDesktopNotifications', 'on');
        setValue('desktopNotifications', true);
      }
    } else {
      // Turning OFF notifications
      setPermanentCookie('quay.enabledDesktopNotifications', 'off');
      setValue('desktopNotifications', false);
    }

    setPendingNotificationChange(null);
  };

  const handleNotificationModalClose = () => {
    setNotificationsModalOpen(false);
    setPendingNotificationChange(null);
  };

  const deleteAccountMutator = useDeleteAccount({
    onSuccess: () => {
      // Account deleted successfully - redirect to signin
      window.location.href = '/signin';
    },
    onError: (err) => {
      addAlert({
        title: err.message || 'Failed to delete account',
        variant: AlertVariant.Failure,
        key: 'delete-account-error',
      });
    },
  });

  const handleDeleteAccount = () => {
    setDeleteAccountModalOpen(true);
  };

  const handleDeleteAccountConfirm = async () => {
    setDeleteAccountModalOpen(false);

    try {
      if (isUserOrganization) {
        await deleteAccountMutator.deleteUser();
      } else {
        await deleteAccountMutator.deleteOrg(organizationName);
      }
    } catch (error) {
      // Error handling is done in the onError callback
    }
  };

  const handleDeleteAccountModalClose = () => {
    setDeleteAccountModalOpen(false);
  };

  // Determine namespace info for delete modal
  const namespaceName = isUserOrganization
    ? user?.username
    : organization?.name;
  const namespaceTitle = isUserOrganization ? 'account' : 'organization';

  // Check if deletion should be blocked (Database auth only, like Angular)
  const canShowDelete = quayConfig?.config?.AUTHENTICATION_TYPE === 'Database';

  // TODO: Add billing subscription check here if needed
  // const hasActiveBilling = subscriptionStatus === 'valid';
  const hasActiveBilling = false; // Placeholder for now

  const onSubmit = async (data: GeneralSettingsFormData) => {
    try {
      if (!isUserOrganization) {
        // Update organization settings
        let tagExpirationSeconds = null;
        if (data.tagExpirationS !== undefined && data.tagExpirationS !== '') {
          const seconds = parseInt(data.tagExpirationS, 10);
          if (!isNaN(seconds) && seconds >= 0) {
            tagExpirationSeconds = seconds;
          }
        }

        const orgUpdateData = {
          tag_expiration_s: tagExpirationSeconds,
          email: data.email !== namespaceEmail ? data.email : null,
          isUser: isUserOrganization,
        };

        await updateOrgSettings(orgUpdateData);
      } else {
        // Update user settings
        const userUpdateRequest: UpdateUserRequest = {
          email: data.email.trim(),
          company: data.company.trim(),
          location: data.location.trim(),
          family_name: data.fullName.trim(),
        };

        if (
          quayConfig?.features?.CHANGE_TAG_EXPIRATION &&
          data.tagExpirationS !== undefined &&
          data.tagExpirationS !== ''
        ) {
          const seconds = parseInt(data.tagExpirationS, 10);
          if (!isNaN(seconds) && seconds >= 0) {
            userUpdateRequest.tag_expiration_s = seconds;
          }
        }

        await updateUser(userUpdateRequest);
      }

      // Reset form to mark as clean
      reset(data);
    } catch (error) {
      addDisplayError('Unable to update namespace settings', error);
    }
  };

  return (
    <Form id="form-form" maxWidth="70%" onSubmit={handleSubmit(onSubmit)}>
      <FormGroup isInline label="Organization" fieldId="form-organization">
        <TextInput
          isDisabled
          type="text"
          id="form-name"
          value={organizationName}
        />

        <FormHelperText>
          <HelperText>
            <HelperTextItem variant="indeterminate">
              Namespace names cannot be changed once set.
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      {(isUserOrganization ? user?.avatar : organization?.avatar) && (
        <FormGroup
          isInline
          label="Avatar"
          fieldId="form-avatar"
          data-testid="form-avatar"
        >
          <Flex
            direction={{default: 'column'}}
            alignItems={{default: 'alignItemsFlexStart'}}
          >
            <FlexItem spacer={{default: 'spacerSm'}}>
              <Avatar
                avatar={
                  isUserOrganization ? user?.avatar : organization?.avatar
                }
                size="md"
                data-testid="avatar"
              />
            </FlexItem>
            <FlexItem>
              <HelperText>
                <HelperTextItem variant="indeterminate">
                  Avatar is generated based off of{' '}
                  {isUserOrganization
                    ? 'your username'
                    : 'the organization name'}
                  .
                </HelperTextItem>
              </HelperText>
            </FlexItem>
          </Flex>
        </FormGroup>
      )}

      <FormTextInput<GeneralSettingsFormData>
        name="email"
        control={control}
        errors={errors}
        label="Email"
        fieldId="org-settings-email"
        type="email"
        helperText="The e-mail address associated with the organization."
        customValidation={(value: string) =>
          isValidEmail(value) || 'Please enter a valid email address'
        }
      />

      {isUserOrganization && quayConfig?.features.USER_METADATA === true && (
        <Grid hasGutter>
          <GridItem span={6}>
            <FormTextInput<GeneralSettingsFormData>
              name="fullName"
              control={control}
              errors={errors}
              label="Full name"
              fieldId="org-settings-fullname"
              isStack={false}
            />
          </GridItem>

          <GridItem span={6}>
            <FormTextInput<GeneralSettingsFormData>
              name="company"
              control={control}
              errors={errors}
              label="Company"
              fieldId="org-settings-company"
              isStack={false}
            />
          </GridItem>

          <GridItem span={6}>
            <FormTextInput<GeneralSettingsFormData>
              name="location"
              control={control}
              errors={errors}
              label="Location"
              fieldId="org-settings-location"
              isStack={false}
            />
          </GridItem>
        </Grid>
      )}

      {isUserOrganization &&
        quayConfig?.config?.AUTHENTICATION_TYPE === 'Database' && (
          <FormGroup isInline label="Password" fieldId="form-password">
            <Button
              variant="link"
              isInline
              onClick={() => setIsPasswordModalOpen(true)}
              style={{padding: 0}}
            >
              Change password
            </Button>
          </FormGroup>
        )}

      {isUserOrganization &&
        quayConfig?.config?.AUTHENTICATION_TYPE === 'Database' && (
          <FormGroup isInline label="Account Type" fieldId="form-account-type">
            <Button
              variant="link"
              isInline
              onClick={() => setIsAccountTypeModalOpen(true)}
              style={{padding: 0}}
            >
              Individual account
            </Button>
          </FormGroup>
        )}

      {isUserOrganization && (
        <FormCheckbox<GeneralSettingsFormData>
          name="desktopNotifications"
          control={control}
          label="Enable desktop notifications"
          fieldId="form-notifications"
          data-testid="form-notifications"
          description={
            browserPermissionDenied
              ? 'Desktop notifications have been disabled, or are unavailable, in your browser.'
              : undefined
          }
          isStack={false}
          customOnChange={async (checked) => {
            // Wait to change cb state until after user confirms in modal
            await handleNotificationToggle(checked);
          }}
        />
      )}

      {quayConfig?.features?.CHANGE_TAG_EXPIRATION && (
        <FormGroup isInline label="Time machine" fieldId="form-time-machine">
          <Controller
            name="tagExpirationS"
            control={control}
            render={({field: {value, onChange}}) => (
              <FormSelect
                placeholder="Time Machine"
                aria-label="Time Machine select"
                data-testid="tag-expiration-picker"
                value={value}
                onChange={(_, val) => onChange(val)}
              >
                {Object.entries(timeMachineOptions).map(
                  ([key, value], index) => (
                    <FormSelectOption
                      key={index}
                      value={moment
                        .duration(parseTimeDuration(key))
                        .asSeconds()
                        .toString()}
                      label={value}
                    />
                  ),
                )}
              </FormSelect>
            )}
          />

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
        <Button
          id="save-org-settings"
          variant="primary"
          type="submit"
          onClick={handleSubmit(onSubmit)}
          isDisabled={!isDirty || !isValid}
        >
          Save
        </Button>

        {canShowDelete && (
          <>
            {hasActiveBilling ? (
              <Flex alignItems={{default: 'alignItemsCenter'}}>
                <FlexItem spacer={{default: 'spacerSm'}}>
                  <i
                    className="fa fa-exclamation-triangle"
                    style={{color: '#f0ad4e'}}
                  />
                </FlexItem>
                <FlexItem>
                  You must cancel your billing subscription before this{' '}
                  {namespaceTitle} can be deleted.
                </FlexItem>
              </Flex>
            ) : (
              <Button variant="danger" onClick={handleDeleteAccount}>
                Delete {namespaceTitle}
              </Button>
            )}
          </>
        )}
      </ActionGroup>

      <Alerts />

      <ChangePasswordModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />

      <ChangeAccountTypeModal
        isOpen={isAccountTypeModalOpen}
        onClose={() => setIsAccountTypeModalOpen(false)}
      />

      <DesktopNotificationsModal
        isOpen={notificationsModalOpen}
        onClose={handleNotificationModalClose}
        onConfirm={handleNotificationConfirm}
        isEnabling={pendingNotificationChange === true}
      />

      <DeleteAccountModal
        isOpen={deleteAccountModalOpen}
        onClose={handleDeleteAccountModalClose}
        onConfirm={handleDeleteAccountConfirm}
        namespaceName={namespaceName || ''}
        namespaceTitle={namespaceTitle}
        isLoading={deleteAccountMutator.loading}
      />
    </Form>
  );
};
