import {useForm} from 'react-hook-form';
import {AlertVariant} from 'src/atoms/AlertState';
import {
  createServiceKey,
  CreateServiceKeyRequest,
} from 'src/resources/ServiceKeysResource';

export interface CreateServiceKeyFormData {
  name: string;
  service: string;
  expiration: string; // Date string in YYYY-MM-DDTHH:MM format
  notes: string;
}

const defaultFormValues: CreateServiceKeyFormData = {
  name: '',
  service: '',
  expiration: '', // No default expiration - user must specify if wanted
  notes: '',
};

export const useCreateServiceKey = (
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void,
  setError: (error: string | null) => void,
  onSuccess: () => void,
) => {
  // Initialize react-hook-form
  const form = useForm<CreateServiceKeyFormData>({
    defaultValues: defaultFormValues,
    mode: 'onChange',
  });

  const {
    control,
    handleSubmit,
    formState: {errors, isValid, isDirty, isSubmitting},
    setValue,
    watch,
    reset,
    getValues,
    trigger,
  } = form;

  // Watch all form values
  const formValues = watch();

  // Form submission
  const onSubmit = async (data: CreateServiceKeyFormData) => {
    try {
      // Convert form data to API format
      const apiData: CreateServiceKeyRequest = {
        service: data.service,
        name: data.name || undefined, // Convert empty string to undefined
        expiration: data.expiration
          ? Math.floor(new Date(data.expiration).getTime() / 1000)
          : null, // Should not be null since field is required, but keeping for safety
        notes: data.notes || undefined, // Convert empty string to undefined
      };

      await createServiceKey(apiData);

      // Reset form to default values
      reset(defaultFormValues);

      addAlert({
        variant: AlertVariant.Success,
        title: 'Service key created successfully',
      });

      onSuccess();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error creating service key',
        message: errorMessage,
      });
    }
  };

  // Form validation rules
  const validationRules = {
    name: {
      required: 'Key name is required',
      pattern: {
        value: /^[\s a-zA-Z0-9\-_:/]*$/,
        message: 'Key name must match ^[\\s a-zA-Z0-9\\-_:/*$',
      },
    },
    service: {
      required: 'Service name is required',
      pattern: {
        value: /^[a-z0-9_]+$/,
        message: 'Service name must match [a-z0-9_]+',
      },
    },
    expiration: {
      required: 'Expiration date is required',
      validate: (value: string) => {
        if (!value) return 'Expiration date is required';
        const date = new Date(value);
        if (isNaN(date.getTime())) return 'Please enter a valid date and time';
        if (date <= new Date()) return 'Expiration date must be in the future';
        return true;
      },
    },
  };

  return {
    // Form methods
    control,
    handleSubmit,
    errors,
    isValid,
    isDirty,
    isSubmitting,
    setValue,
    watch,
    reset,
    getValues,
    trigger,
    formValues,
    onSubmit,
    validationRules,
  };
};
