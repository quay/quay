import {useForm} from 'react-hook-form';
import {AlertVariant} from 'src/contexts/UIContext';
import {
  OAuthApplicationFormData,
  defaultOAuthFormValues,
} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/types';
import {useCreateOAuthApplication} from './UseOAuthApplications';

export const useOAuthApplicationForm = (
  orgName: string,
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void,
  onSuccess: () => void,
) => {
  // Initialize react-hook-form
  const form = useForm<OAuthApplicationFormData>({
    defaultValues: defaultOAuthFormValues,
    mode: 'onChange',
  });

  const {
    control,
    handleSubmit,
    formState: {errors, isValid, isDirty},
    setValue,
    watch,
    reset,
    getValues,
    trigger,
  } = form;

  // Watch all form values
  const formValues = watch();

  // Create OAuth application mutation
  const {createOAuthApplication} = useCreateOAuthApplication(orgName, {
    onError: (error) => {
      const errorMessage =
        error?.error?.message || error?.message || String(error);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error creating application',
        message: errorMessage,
      });
    },
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully created application: ${formValues.name}`,
      });
      reset(); // Clear form
      onSuccess(); // Close modal
    },
  });

  // Form submission
  const onSubmit = async (data: OAuthApplicationFormData) => {
    await createOAuthApplication(data);
  };

  return {
    // Form controls
    control,
    errors,
    formValues,
    handleSubmit: handleSubmit(onSubmit),
    isValid,
    isDirty,
    setValue,
    reset,
    getValues,
    trigger,

    // Form actions
    onSubmit,
  };
};
