import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {OrgMirroringFormData} from 'src/routes/OrganizationsList/Organization/Tabs/OrgMirroring/types';
import {Entity, EntityKind} from 'src/resources/UserResource';

// Default form values
export const defaultFormValues: OrgMirroringFormData = {
  isEnabled: true,
  externalRegistryType: '',
  externalRegistryUrl: '',
  externalNamespace: '',
  robotUsername: '',
  visibility: 'private',
  repositoryFilters: '',
  syncStartDate: '',
  syncValue: '24',
  syncUnit: 'hours',
  username: '',
  password: '',
  verifyTls: true,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  skopeoTimeout: 300,
};

export const useOrgMirroringForm = () => {
  // Initialize react-hook-form
  const form = useForm<OrgMirroringFormData>({
    defaultValues: defaultFormValues,
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

  // Only watch the single field that other components need reactively
  const isEnabled = watch('isEnabled');

  // Non-form UI state
  const [selectedRobot, setSelectedRobot] = useState<Entity | null>(null);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);

  const handleRobotSelect = (name: string) => {
    const robotEntity: Entity = {
      name,
      is_robot: true,
      kind: EntityKind.user,
      is_org_member: true,
    };
    setSelectedRobot(robotEntity);
    setValue('robotUsername', name, {shouldDirty: true, shouldValidate: true});
  };

  return {
    // Form methods
    control,
    handleSubmit,
    errors,
    isValid,
    isDirty,
    setValue,
    watch,
    reset,
    getValues,
    trigger,
    isEnabled,

    // UI state
    selectedRobot,
    setSelectedRobot,
    isCreateRobotModalOpen,
    setIsCreateRobotModalOpen,

    // Helper methods
    handleRobotSelect,
  };
};
