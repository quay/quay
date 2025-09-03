import {
  ActionGroup,
  Button,
  Flex,
  Form,
  FormGroup,
  Select,
  SelectOption,
  MenuToggle,
  Spinner,
  TextInput,
  Alert,
  Grid,
  GridItem,
  Card,
  CardBody,
  Text,
  FlexItem,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import {PlusIcon} from '@patternfly/react-icons';
import {useEffect, useState} from 'react';
import {useForm, Controller} from 'react-hook-form';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {AlertVariant as AlertVariantState} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  useFetchOrganizationQuota,
  useCreateOrganizationQuota,
  useUpdateOrganizationQuota,
  useDeleteOrganizationQuota,
  useCreateQuotaLimit,
  useUpdateQuotaLimit,
  useDeleteQuotaLimit,
} from 'src/hooks/UseQuotaManagement';
import {
  IQuotaLimit,
  bytesToHumanReadable,
  humanReadableToBytes,
} from 'src/resources/QuotaResource';
import Alerts from 'src/routes/Alerts';

type QuotaManagementProps = {
  organizationName: string;
  isUser: boolean;
};

const QUOTA_UNITS = ['KiB', 'MiB', 'GiB', 'TiB'];
const QUOTA_LIMIT_TYPES = ['Warning', 'Reject'];

interface QuotaFormData {
  quotaValue: string;
  quotaUnit: string;
}

const defaultFormValues: QuotaFormData = {
  quotaValue: '0',
  quotaUnit: 'GiB',
};

export const QuotaManagement = (props: QuotaManagementProps) => {
  const {organizationQuota, isLoadingQuotas} = useFetchOrganizationQuota(
    props.organizationName,
  );

  // Initialize react-hook-form
  const form = useForm<QuotaFormData>({
    defaultValues: defaultFormValues,
    mode: 'onChange',
  });

  const {
    control,
    handleSubmit,
    formState: {errors, isValid},
    setValue,
    watch,
    reset,
  } = form;

  // Watch form values
  const formValues = watch();

  const [isUnitSelectOpen, setIsUnitSelectOpen] = useState(false);
  const [limits, setLimits] = useState<IQuotaLimit[]>([]);
  const [newLimit, setNewLimit] = useState<{
    type: 'Warning' | 'Reject' | '';
    limit_percent: number | '';
  }>({
    type: '',
    limit_percent: '',
  });
  const [isNewLimitTypeSelectOpen, setIsNewLimitTypeSelectOpen] =
    useState(false);
  const [editingLimits, setEditingLimits] = useState<{[key: string]: boolean}>(
    {},
  );
  const [originalLimits, setOriginalLimits] = useState<{
    [key: string]: IQuotaLimit;
  }>({});
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const {addAlert, clearAllAlerts} = useAlerts();

  // Initialize form with existing quota data
  useEffect(() => {
    if (organizationQuota) {
      const humanReadable = bytesToHumanReadable(organizationQuota.limit_bytes);
      setValue('quotaValue', humanReadable.value.toString());
      setValue('quotaUnit', humanReadable.unit);
      setLimits(organizationQuota.limits || []);

      // Store original values for change detection
      const originalLimitsMap: {[key: string]: IQuotaLimit} = {};
      (organizationQuota.limits || []).forEach((limit) => {
        originalLimitsMap[limit.id] = {...limit};
      });
      setOriginalLimits(originalLimitsMap);
    } else {
      reset(defaultFormValues);
      setLimits([]);
      setOriginalLimits({});
    }
  }, [organizationQuota, setValue, reset]);

  // Clear alerts when component unmounts or tab changes
  useEffect(() => {
    return () => {
      clearAllAlerts();
    };
  }, []);

  // Mutation hooks
  const {createQuotaMutation} = useCreateOrganizationQuota(
    props.organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariantState.Success,
          title: 'Successfully created quota',
        });
      },
      onError: (err) => {
        addAlert({
          variant: AlertVariantState.Failure,
          title: err,
        });
      },
    },
  );

  const {updateQuotaMutation} = useUpdateOrganizationQuota(
    props.organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariantState.Success,
          title: 'Successfully updated quota',
        });
      },
      onError: (err) => {
        addAlert({
          variant: AlertVariantState.Failure,
          title: err,
        });
      },
    },
  );

  const {deleteQuotaMutation} = useDeleteOrganizationQuota(
    props.organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariantState.Success,
          title: 'Successfully deleted quota',
        });
        // Reset form
        reset(defaultFormValues);
        setLimits([]);
      },
      onError: (err) => {
        addAlert({
          variant: AlertVariantState.Failure,
          title: err,
        });
      },
    },
  );

  const {createLimitMutation} = useCreateQuotaLimit(props.organizationName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariantState.Success,
        title: 'Successfully added quota limit',
      });
      // Reset new limit form to blank values
      setNewLimit({type: '', limit_percent: ''});
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariantState.Failure,
        title: err,
      });
    },
  });

  const {updateLimitMutation} = useUpdateQuotaLimit(props.organizationName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariantState.Success,
        title: 'Successfully updated quota limit',
      });
      setEditingLimits({});
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariantState.Failure,
        title: err,
      });
    },
  });

  const {deleteLimitMutation} = useDeleteQuotaLimit(props.organizationName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariantState.Success,
        title: 'Successfully deleted quota limit',
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariantState.Failure,
        title: err,
      });
    },
  });

  // Validation functions
  const validateQuota = (value: string): string | boolean => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue <= 0) {
      return 'A quota greater than 0 must be defined.';
    }
    return true;
  };

  const validateLimit = (limit_percent: number): string | null => {
    if (limit_percent < 1 || limit_percent > 100) {
      return 'A quota limit greater than 0 and less than or equal to 100 must be defined.';
    }
    return null;
  };

  const validateLimitsUnique = (): string | null => {
    const rejectLimits = limits.filter((limit) => limit.type === 'Reject');
    if (rejectLimits.length > 1) {
      return 'Error: A quota policy should only have a single reject threshold.';
    }

    // Check for duplicate thresholds
    const thresholds = limits.map(
      (limit) => `${limit.type}-${limit.limit_percent}`,
    );
    if (new Set(thresholds).size !== thresholds.length) {
      return 'Error: The quota policy contains two identical thresholds.';
    }

    return null;
  };

  // Form submission
  const onSubmit = async (data: QuotaFormData) => {
    const limitError = validateLimitsUnique();
    if (limitError) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: limitError,
      });
      return;
    }

    const limit_bytes = humanReadableToBytes(
      Number(data.quotaValue),
      data.quotaUnit,
    );

    if (organizationQuota) {
      updateQuotaMutation({
        quotaId: organizationQuota.id,
        params: {limit_bytes},
      });
    } else {
      createQuotaMutation({limit_bytes});
    }
  };

  const handleDeleteQuota = () => {
    setIsDeleteModalOpen(true);
  };

  const confirmDeleteQuota = () => {
    if (organizationQuota) {
      deleteQuotaMutation(organizationQuota.id);
      setIsDeleteModalOpen(false);
    }
  };

  const handleAddLimit = () => {
    if (!organizationQuota) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: 'Please set quota before adding a quota limit.',
      });
      return;
    }

    // Validate required fields
    if (!newLimit.type) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: 'Please select an action type (Warning or Reject).',
      });
      return;
    }

    if (newLimit.limit_percent === '' || newLimit.limit_percent === 0) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: 'Please enter a quota threshold percentage.',
      });
      return;
    }

    const limitError = validateLimit(Number(newLimit.limit_percent));
    if (limitError) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: limitError,
      });
      return;
    }

    // Check for duplicate reject limits
    if (
      newLimit.type === 'Reject' &&
      limits.some((limit) => limit.type === 'Reject')
    ) {
      addAlert({
        variant: AlertVariantState.Failure,
        title:
          'Error: A quota policy should only have a single reject threshold.',
      });
      return;
    }

    createLimitMutation({
      quotaId: organizationQuota.id,
      params: {
        type: newLimit.type as 'Warning' | 'Reject',
        threshold_percent: Number(newLimit.limit_percent),
      },
    });
  };

  const handleUpdateLimit = (limitId: string, updatedLimit: IQuotaLimit) => {
    if (!organizationQuota) return;

    const limitError = validateLimit(updatedLimit.limit_percent);
    if (limitError) {
      addAlert({
        variant: AlertVariantState.Failure,
        title: limitError,
      });
      return;
    }

    updateLimitMutation({
      quotaId: organizationQuota.id,
      limitId: limitId,
      params: {
        type: updatedLimit.type,
        threshold_percent: updatedLimit.limit_percent,
      },
    });
  };

  const handleDeleteLimit = (limitId: string) => {
    if (!organizationQuota) return;

    deleteLimitMutation({
      quotaId: organizationQuota.id,
      limitId: limitId,
    });
  };

  const handleLimitChange = (
    limitId: string,
    field: keyof IQuotaLimit,
    value: string | number,
  ) => {
    setLimits((prevLimits) =>
      prevLimits.map((limit) =>
        limit.id === limitId ? {...limit, [field]: value} : limit,
      ),
    );
  };

  // Check if a limit has changed from its original value
  const hasLimitChanged = (limitId: string): boolean => {
    const currentLimit = limits.find((l) => l.id === limitId);
    const originalLimit = originalLimits[limitId];

    if (!currentLimit || !originalLimit) return false;

    return (
      currentLimit.type !== originalLimit.type ||
      currentLimit.limit_percent !== originalLimit.limit_percent
    );
  };

  if (isLoadingQuotas) {
    return <Spinner size="md" />;
  }

  const hasQuota = organizationQuota !== null;

  return (
    <Form id="quota-management-form" onSubmit={handleSubmit(onSubmit)}>
      {!hasQuota && (
        <Alert
          variant="info"
          title="No Quota Configured"
          style={{marginBottom: '1em'}}
        />
      )}

      {/* Storage Quota Section */}
      <FormGroup label="Storage quota" fieldId="quota-input">
        <Card isCompact isPlain style={{maxWidth: '600px'}}>
          <CardBody>
            <Grid hasGutter>
              <GridItem span={3}>
                <FormTextInput
                  name="quotaValue"
                  control={control}
                  errors={errors}
                  label=""
                  type="text"
                  inputMode="numeric"
                  required={true}
                  customValidation={validateQuota}
                  data-testid="quota-value-input"
                  isStack={false}
                />
              </GridItem>
              <GridItem span={2}>
                <Controller
                  name="quotaUnit"
                  control={control}
                  render={({field: {value, onChange}}) => (
                    <Select
                      id="quota-unit-select"
                      isOpen={isUnitSelectOpen}
                      selected={value}
                      onSelect={(_event, selection) => {
                        onChange(selection as string);
                        setIsUnitSelectOpen(false);
                      }}
                      onOpenChange={(isOpen) => setIsUnitSelectOpen(isOpen)}
                      toggle={(toggleRef) => (
                        <MenuToggle
                          ref={toggleRef}
                          onClick={() => setIsUnitSelectOpen(!isUnitSelectOpen)}
                          isDisabled={hasQuota && props.isUser}
                          style={{minWidth: '90px'}}
                        >
                          {value}
                        </MenuToggle>
                      )}
                    >
                      {QUOTA_UNITS.map((unit) => (
                        <SelectOption key={unit} value={unit}>
                          {unit}
                        </SelectOption>
                      ))}
                    </Select>
                  )}
                />
              </GridItem>
            </Grid>
          </CardBody>
        </Card>
      </FormGroup>

      {/* Quota Policy Section */}
      {hasQuota && (
        <FormGroup label="Quota Policy" fieldId="quota-limits">
          <Flex
            direction={{default: 'column'}}
            spaceItems={{default: 'spaceItemsXs'}}
          >
            {/* Column headers */}
            <Flex
              justifyContent={{default: 'justifyContentFlexStart'}}
              spaceItems={{default: 'spaceItemsLg'}}
              style={{
                maxWidth: '600px',
                paddingLeft: '16px',
                paddingTop: '16px',
                paddingBottom: '4px',
              }}
            >
              <FlexItem>
                <Flex
                  alignItems={{default: 'alignItemsCenter'}}
                  spaceItems={{default: 'spaceItemsSm'}}
                >
                  <FlexItem style={{minWidth: '140px'}}>
                    <Text component="h6">Action</Text>
                  </FlexItem>
                  <FlexItem style={{minWidth: '140px'}}>
                    <Text component="h6">Quota Threshold</Text>
                  </FlexItem>
                </Flex>
              </FlexItem>
            </Flex>
            {limits.map((limit) => (
              <Card
                key={limit.id}
                isCompact
                isPlain
                style={{maxWidth: '600px'}}
              >
                <CardBody>
                  <Flex
                    justifyContent={{default: 'justifyContentFlexStart'}}
                    alignItems={{default: 'alignItemsCenter'}}
                    spaceItems={{default: 'spaceItemsLg'}}
                  >
                    <FlexItem>
                      <Flex
                        alignItems={{default: 'alignItemsCenter'}}
                        spaceItems={{default: 'spaceItemsSm'}}
                      >
                        <FlexItem style={{minWidth: '140px'}}>
                          <Select
                            id={`limit-type-select-${limit.id}`}
                            isOpen={editingLimits[limit.id] || false}
                            selected={limit.type}
                            onSelect={(_event, selection) => {
                              handleLimitChange(
                                limit.id,
                                'type',
                                selection as 'Warning' | 'Reject',
                              );
                              setEditingLimits({
                                ...editingLimits,
                                [limit.id]: false,
                              });
                            }}
                            onOpenChange={(isOpen) =>
                              setEditingLimits({
                                ...editingLimits,
                                [limit.id]: isOpen,
                              })
                            }
                            toggle={(toggleRef) => (
                              <MenuToggle
                                ref={toggleRef}
                                onClick={() =>
                                  setEditingLimits({
                                    ...editingLimits,
                                    [limit.id]: !editingLimits[limit.id],
                                  })
                                }
                                isDisabled={false}
                                style={{width: '120px'}}
                              >
                                {limit.type}
                              </MenuToggle>
                            )}
                          >
                            {QUOTA_LIMIT_TYPES.map((type) => (
                              <SelectOption key={type} value={type}>
                                {type}
                              </SelectOption>
                            ))}
                          </Select>
                        </FlexItem>
                        <FlexItem style={{minWidth: '140px'}}>
                          <Flex
                            alignItems={{default: 'alignItemsCenter'}}
                            spaceItems={{default: 'spaceItemsXs'}}
                          >
                            <FlexItem>
                              <TextInput
                                type="number"
                                value={limit.limit_percent}
                                min={1}
                                max={100}
                                onChange={(_event, value) => {
                                  const numValue = parseInt(value, 10);
                                  if (
                                    !isNaN(numValue) &&
                                    numValue >= 1 &&
                                    numValue <= 100
                                  ) {
                                    handleLimitChange(
                                      limit.id,
                                      'limit_percent',
                                      numValue,
                                    );
                                  } else if (value === '') {
                                    handleLimitChange(
                                      limit.id,
                                      'limit_percent',
                                      '',
                                    );
                                  }
                                }}
                                style={{width: '120px'}}
                                isDisabled={false}
                              />
                            </FlexItem>
                            <FlexItem>
                              <Text component="small">%</Text>
                            </FlexItem>
                          </Flex>
                        </FlexItem>
                      </Flex>
                    </FlexItem>
                    <FlexItem>
                      <Flex spaceItems={{default: 'spaceItemsSm'}}>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleUpdateLimit(limit.id, limit)}
                          isDisabled={!hasLimitChanged(limit.id)}
                        >
                          Update
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDeleteLimit(limit.id)}
                        >
                          Remove
                        </Button>
                      </Flex>
                    </FlexItem>
                  </Flex>
                </CardBody>
              </Card>
            ))}

            {/* Add new limit card */}
            {
              <Card isCompact isPlain style={{maxWidth: '600px'}}>
                <CardBody>
                  <Flex
                    justifyContent={{default: 'justifyContentFlexStart'}}
                    alignItems={{default: 'alignItemsCenter'}}
                    spaceItems={{default: 'spaceItemsLg'}}
                  >
                    <FlexItem>
                      <Flex
                        alignItems={{default: 'alignItemsCenter'}}
                        spaceItems={{default: 'spaceItemsSm'}}
                      >
                        <FlexItem style={{minWidth: '140px'}}>
                          <Select
                            id="new-limit-type-select"
                            isOpen={isNewLimitTypeSelectOpen}
                            selected={newLimit.type}
                            onSelect={(_event, selection) => {
                              setNewLimit({
                                ...newLimit,
                                type: selection as 'Warning' | 'Reject',
                              });
                              setIsNewLimitTypeSelectOpen(false);
                            }}
                            onOpenChange={(isOpen) =>
                              setIsNewLimitTypeSelectOpen(isOpen)
                            }
                            toggle={(toggleRef) => (
                              <MenuToggle
                                ref={toggleRef}
                                onClick={() =>
                                  setIsNewLimitTypeSelectOpen(
                                    !isNewLimitTypeSelectOpen,
                                  )
                                }
                                style={{width: '120px'}}
                              >
                                {newLimit.type || ''}
                              </MenuToggle>
                            )}
                          >
                            {QUOTA_LIMIT_TYPES.map((type) => (
                              <SelectOption key={type} value={type}>
                                {type}
                              </SelectOption>
                            ))}
                          </Select>
                        </FlexItem>
                        <FlexItem style={{minWidth: '140px'}}>
                          <Flex
                            alignItems={{default: 'alignItemsCenter'}}
                            spaceItems={{default: 'spaceItemsXs'}}
                          >
                            <FlexItem>
                              <TextInput
                                type="number"
                                value={newLimit.limit_percent}
                                min={1}
                                max={100}
                                onChange={(_event, value) => {
                                  const numValue = parseInt(value, 10);
                                  if (
                                    !isNaN(numValue) &&
                                    numValue >= 1 &&
                                    numValue <= 100
                                  ) {
                                    setNewLimit({
                                      ...newLimit,
                                      limit_percent: numValue,
                                    });
                                  } else if (value === '') {
                                    setNewLimit({
                                      ...newLimit,
                                      limit_percent: '',
                                    });
                                  }
                                }}
                                style={{width: '120px'}}
                              />
                            </FlexItem>
                            <FlexItem>
                              <Text component="small">%</Text>
                            </FlexItem>
                          </Flex>
                        </FlexItem>
                      </Flex>
                    </FlexItem>
                    <FlexItem>
                      <Button
                        variant="primary"
                        size="sm"
                        icon={<PlusIcon />}
                        onClick={handleAddLimit}
                      >
                        Add Limit
                      </Button>
                    </FlexItem>
                  </Flex>
                </CardBody>
              </Card>
            }

            {/* Note message when no limits exist - placed after Add Limit form */}
            {limits.length === 0 && (
              <Alert
                variant="info"
                title="Note: No quota policy defined. Users will be able to exceed the storage quota set above."
                isInline
              />
            )}
          </Flex>
        </FormGroup>
      )}

      {/* Action Buttons */}
      <ActionGroup>
        <Button
          id="save-quota"
          variant="primary"
          type="submit"
          isDisabled={!isValid || parseFloat(formValues.quotaValue || '0') <= 0}
        >
          Apply
        </Button>

        {hasQuota && (
          <Button
            id="delete-quota"
            variant="danger"
            onClick={handleDeleteQuota}
          >
            Remove
          </Button>
        )}
      </ActionGroup>

      <Alerts />

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Quota"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button key="confirm" variant="danger" onClick={confirmDeleteQuota}>
            OK
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        Are you sure you want to delete quota for this organization? When you
        remove the quota storage, users can consume arbitrary amount of storage
        resources.
      </Modal>
    </Form>
  );
};
