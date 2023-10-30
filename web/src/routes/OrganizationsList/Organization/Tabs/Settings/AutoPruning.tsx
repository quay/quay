import {
  ActionGroup,
  Button,
  Flex,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  NumberInput,
  Spinner,
  Title,
  FormHelperText,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import Conditional from 'src/components/empty/Conditional';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  useCreateNamespaceAutoPrunePolicy,
  useDeleteNamespaceAutoPrunePolicy,
  useNamespaceAutoPrunePolicies,
  useUpdateNamespaceAutoPrunePolicy,
} from 'src/hooks/UseNamespaceAutoPrunePolicies';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  AutoPruneMethod,
  NamespaceAutoPrunePolicy,
} from 'src/resources/NamespaceAutoPruneResource';

// Must match convert_to_timedelta from backend
export const shorthandTimeUnits = {
  s: 'seconds',
  m: 'minutes',
  h: 'hours',
  d: 'days',
  w: 'weeks',
};

export default function AutoPruning(props: AutoPruning) {
  const [uuid, setUuid] = useState<string>(null);
  const [method, setMethod] = useState<AutoPruneMethod>(AutoPruneMethod.NONE);
  const [tagCount, setTagCount] = useState<number>(20);
  const [tagCreationDateUnit, setTagCreationDateUnit] = useState<string>('d');
  const [tagCreationDateValue, setTagCreationDateValue] = useState<number>(7);
  const {addAlert} = useAlerts();
  const {
    error,
    isSuccess: successFetchingPolicies,
    isLoading,
    policies,
    dataUpdatedAt,
  } = useNamespaceAutoPrunePolicies(props.org, props.isUser);
  const {
    createPolicy,
    successCreatePolicy,
    errorCreatePolicy,
    errorCreatePolicyDetails,
  } = useCreateNamespaceAutoPrunePolicy(props.org, props.isUser);
  const {
    updatePolicy,
    successUpdatePolicy,
    errorUpdatePolicy,
    errorUpdatePolicyDetails,
  } = useUpdateNamespaceAutoPrunePolicy(props.org, props.isUser);
  const {
    deletePolicy,
    successDeletePolicy,
    errorDeletePolicy,
    errorDeletePolicyDetails,
  } = useDeleteNamespaceAutoPrunePolicy(props.org, props.isUser);

  useEffect(() => {
    if (successFetchingPolicies) {
      // Currently we only support one policy per namespace but
      // this will change in the future.
      if (policies.length > 0) {
        const policy: NamespaceAutoPrunePolicy = policies[0];
        setMethod(policy.method);
        setUuid(policy.uuid);
        switch (policy.method) {
          case AutoPruneMethod.TAG_NUMBER: {
            setTagCount(policy.value as number);
            break;
          }
          case AutoPruneMethod.TAG_CREATION_DATE: {
            const tagAgeValue = (policy.value as string).match(/\d+/g);
            const tagAgeUnit = (policy.value as string).match(/[a-zA-Z]+/g);
            if (tagAgeValue.length > 0 && tagAgeUnit.length > 0) {
              setTagCreationDateValue(Number(tagAgeValue[0]));
              setTagCreationDateUnit(tagAgeUnit[0]);
            } else {
              // Shouldn't ever happen but leave it here just in case
              console.error('Invalid tag age value');
            }
            break;
          }
        }
      } else {
        // If no policy was returned it's possible this was
        // after the deletion of the policy, in which all the state
        // has to be reset
        setUuid(null);
        setMethod(AutoPruneMethod.NONE);
        setTagCount(20);
        setTagCreationDateUnit('d');
        setTagCreationDateValue(7);
      }
    }
  }, [successFetchingPolicies, dataUpdatedAt]);

  useEffect(() => {
    if (successCreatePolicy) {
      addAlert({
        title: 'Successfully created auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successCreatePolicy]);

  useEffect(() => {
    if (successUpdatePolicy) {
      addAlert({
        title: 'Successfully updated auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successUpdatePolicy]);

  useEffect(() => {
    if (successDeletePolicy) {
      addAlert({
        title: 'Successfully deleted auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successDeletePolicy]);

  useEffect(() => {
    if (errorCreatePolicy) {
      addAlert({
        title: 'Could not create auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorCreatePolicyDetails.toString(),
      });
    }
  }, [errorCreatePolicy]);

  useEffect(() => {
    if (errorUpdatePolicy) {
      addAlert({
        title: 'Could not update auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorUpdatePolicyDetails.toString(),
      });
    }
  }, [errorUpdatePolicy]);

  useEffect(() => {
    if (errorDeletePolicy) {
      addAlert({
        title: 'Could not delete auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDeletePolicyDetails.toString(),
      });
    }
  }, [errorDeletePolicy]);

  const onSave = (e) => {
    e.preventDefault();
    let value = null;
    switch (method) {
      case AutoPruneMethod.TAG_NUMBER:
        value = tagCount;
        break;
      case AutoPruneMethod.TAG_CREATION_DATE:
        value = `${String(tagCreationDateValue)}${tagCreationDateUnit}`;
        break;
      case AutoPruneMethod.NONE:
        // Delete the policy is done by setting the method to none
        if (!isNullOrUndefined(uuid)) {
          deletePolicy(uuid);
        }
        return;
      default:
        // Reaching here indicates programming error, component should always be aware of valid methods
        return;
    }
    if (isNullOrUndefined(uuid)) {
      createPolicy({method: method, value: value});
    } else {
      updatePolicy({uuid: uuid, method: method, value: value});
    }
  };

  if (isLoading) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(error)) {
    return <RequestError message={error.toString()} />;
  }

  return (
    <>
      <Title headingLevel="h2" style={{paddingBottom: '.5em'}}>
        Auto Pruning Policies
      </Title>
      <p style={{paddingBottom: '1em'}}>
        Auto-pruning policies automatically delete tags across all repositories
        within this organization by a given method.
      </p>
      <Form id="autpruning-form" maxWidth="70%">
        <FormGroup
          isInline
          label="Prune Policy - select a method to prune tags"
          fieldId="method"
          isRequired
        >
          <FormSelect
            placeholder=""
            aria-label="namespace-auto-prune-method"
            data-testid="namespace-auto-prune-method"
            value={method}
            onChange={(_, val) => setMethod(val as AutoPruneMethod)}
          >
            <FormSelectOption
              key={1}
              value={AutoPruneMethod.NONE}
              label="None"
            />
            <FormSelectOption
              key={2}
              value={AutoPruneMethod.TAG_NUMBER}
              label="By number of tags"
            />
            <FormSelectOption
              key={3}
              value={AutoPruneMethod.TAG_CREATION_DATE}
              label="By age of tags"
            />
          </FormSelect>
          <FormHelperText>
            <HelperText>
              <HelperTextItem>The method used to prune tags.</HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <Conditional if={method === AutoPruneMethod.TAG_NUMBER}>
          <FormGroup label="The number of tags to keep." fieldId="" isRequired>
            <NumberInput
              value={tagCount}
              onMinus={() => {
                tagCount > 1 ? setTagCount(tagCount - 1) : setTagCount(1);
              }}
              onChange={(e) => {
                const input = (e.target as HTMLInputElement).value;
                const value = Number(input);
                if (value > 0 && /^\d+$/.test(input)) {
                  setTagCount(value);
                }
              }}
              onPlus={() => {
                setTagCount(tagCount + 1);
              }}
              inputAriaLabel="number of tags"
              minusBtnAriaLabel="minus"
              plusBtnAriaLabel="plus"
              data-testid="namespace-auto-prune-tag-count"
            />
            <FormHelperText>
              <HelperText>
                <HelperTextItem>
                  All tags sorted by earliest creation date will be deleted
                  until the repository total falls below the threshold
                </HelperTextItem>
              </HelperText>
            </FormHelperText>
          </FormGroup>
        </Conditional>
        <Conditional if={method === AutoPruneMethod.TAG_CREATION_DATE}>
          <FormGroup
            label="Delete tags older than given timespan."
            fieldId=""
            isRequired
            isInline
          >
            <div style={{display: 'flex'}}>
              <NumberInput
                value={tagCreationDateValue}
                onMinus={() => {
                  tagCreationDateValue > 1
                    ? setTagCreationDateValue(tagCreationDateValue - 1)
                    : setTagCreationDateValue(1);
                }}
                onChange={(e) => {
                  const input = (e.target as HTMLInputElement).value;
                  const value = Number(input);
                  if (value > 0 && /^\d+$/.test(input)) {
                    setTagCreationDateValue(value);
                  }
                }}
                onPlus={() => {
                  setTagCreationDateValue(tagCreationDateValue + 1);
                }}
                inputAriaLabel="tag creation date value"
                minusBtnAriaLabel="minus"
                plusBtnAriaLabel="plus"
                data-testid="namespace-auto-prune-tag-creation-date-value"
                style={{paddingRight: '1em'}}
              />
              <FormSelect
                placeholder=""
                aria-label="tag creation date unit"
                data-testid="tag-auto-prune-creation-date-timeunit"
                value={tagCreationDateUnit}
                onChange={(_, val) => setTagCreationDateUnit(val)}
                style={{width: '10em'}}
              >
                {Object.keys(shorthandTimeUnits).map((key) => (
                  <FormSelectOption
                    key={key}
                    value={key}
                    label={shorthandTimeUnits[key]}
                  />
                ))}
              </FormSelect>
            </div>
            <FormHelperText>
              <HelperText>
                <HelperTextItem>
                  All tags with a creation date earlier than the selected time
                  period will be deleted
                </HelperTextItem>
              </HelperText>
            </FormHelperText>
          </FormGroup>
        </Conditional>

        <ActionGroup>
          <Flex
            justifyContent={{default: 'justifyContentFlexEnd'}}
            width="100%"
          >
            <Button variant="primary" type="submit" onClick={onSave}>
              Save
            </Button>
          </Flex>
        </ActionGroup>
      </Form>
    </>
  );
}

interface AutoPruning {
  org: string;
  isUser: boolean;
}
