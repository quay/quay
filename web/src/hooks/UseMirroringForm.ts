import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {MirroringFormData} from 'src/routes/RepositoryDetails/Mirroring/types';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {AlertVariant} from 'src/atoms/AlertState';

// Default form values
const defaultFormValues: MirroringFormData = {
  isEnabled: true,
  externalReference: '',
  tags: '',
  syncStartDate: '',
  syncValue: '24',
  syncUnit: 'hours',
  robotUsername: '',
  username: '',
  password: '',
  verifyTls: false,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  unsignedImages: false,
  skopeoTimeoutInterval: 300,
};

export const useMirroringForm = (
  submitConfig: (data: MirroringFormData) => Promise<void>,
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void,
  setError: (error: string | null) => void,
) => {
  // Initialize react-hook-form
  const form = useForm<MirroringFormData>({
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

  // Watch all form values to maintain existing functionality
  const formValues = watch();

  // Non-form UI state
  const [selectedRobot, setSelectedRobot] = useState<Entity | null>(null);
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const [isCreateTeamModalOpen, setIsCreateTeamModalOpen] = useState(false);
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');

  // Form submission
  const onSubmit = async (data: MirroringFormData) => {
    try {
      await submitConfig(data);

      // Reset form with current values to mark it as clean
      reset(data);

      addAlert({
        variant: AlertVariant.Success,
        title: 'Mirror configuration saved successfully',
      });
    } catch (err) {
      setError(err.message);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error saving mirror configuration',
        message: err.message,
      });
    }
  };

  const handleRobotSelect = (name: string) => {
    const robotEntity: Entity = {
      name,
      is_robot: true,
      kind: EntityKind.user,
      is_org_member: true,
    };
    setSelectedRobot(robotEntity);
    setValue('robotUsername', name);
  };

  const handleTeamSelect = (name: string) => {
    const teamEntity: Entity = {
      name,
      is_robot: false,
      kind: EntityKind.team,
      is_org_member: true,
    };
    setSelectedRobot(teamEntity);
    setValue('robotUsername', name);
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
    formValues,
    onSubmit,

    // UI state
    selectedRobot,
    setSelectedRobot,
    isSelectOpen,
    setIsSelectOpen,
    isHovered,
    setIsHovered,
    isCreateRobotModalOpen,
    setIsCreateRobotModalOpen,
    isCreateTeamModalOpen,
    setIsCreateTeamModalOpen,
    teamName,
    setTeamName,
    teamDescription,
    setTeamDescription,

    // Helper methods
    handleRobotSelect,
    handleTeamSelect,
  };
};
