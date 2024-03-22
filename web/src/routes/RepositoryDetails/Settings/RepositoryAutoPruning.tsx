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
  DataList,
  DataListItem,
  DataListItemRow,
  DataListItemCells,
  DataListCell,
  Gallery,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import Conditional from 'src/components/empty/Conditional';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useNamespaceAutoPrunePolicies} from 'src/hooks/UseNamespaceAutoPrunePolicies';
import {useOrganization} from 'src/hooks/UseOrganization';
import {
  useCreateRepositoryAutoPrunePolicy,
  useDeleteRepositoryAutoPrunePolicy,
  useFetchRepositoryAutoPrunePolicies,
  useUpdateRepositoryAutoPrunePolicy,
} from 'src/hooks/UseRepositoryAutoPrunePolicies';
import {isNullOrUndefined} from 'src/libs/utils';
import {AutoPruneMethod} from 'src/resources/NamespaceAutoPruneResource';
import {RepositoryAutoPrunePolicy} from 'src/resources/RepositoryAutoPruneResource';
import {shorthandTimeUnits} from 'src/routes/OrganizationsList/Organization/Tabs/Settings/AutoPruning';

enum AutoPrunePolicyType {
  NONE = 'None',
  TAG_NUMBER = 'Number of Tags',
  TAG_CREATION_DATE = 'Age of Tags',
}

// mapping between AutoPruneMethod and AutoPrunePolicyType values
const methodToPolicyType: Record<AutoPruneMethod, AutoPrunePolicyType> = {
  [AutoPruneMethod.NONE]: AutoPrunePolicyType.NONE,
  [AutoPruneMethod.TAG_NUMBER]: AutoPrunePolicyType.TAG_NUMBER,
  [AutoPruneMethod.TAG_CREATION_DATE]: AutoPrunePolicyType.TAG_CREATION_DATE,
};

// function to get the corresponding display string based on AutoPruneMethod
function getAutoPrunePolicyType(method: AutoPruneMethod): AutoPrunePolicyType {
  return methodToPolicyType[method];
}

export default function RepositoryAutoPruning(props: RepositoryAutoPruning) {
  const [uuid, setUuid] = useState<string>(null);
  const [method, setMethod] = useState<AutoPruneMethod>(AutoPruneMethod.NONE);
  const [tagCount, setTagCount] = useState<number>(20);
  const [tagCreationDateUnit, setTagCreationDateUnit] = useState<string>('d');
  const [tagCreationDateValue, setTagCreationDateValue] = useState<number>(7);
  const {addAlert} = useAlerts();
  const {organization} = useOrganization(props.organizationName);

  const {
    error,
    isSuccess: successFetchingPolicies,
    isLoading,
    nsPolicies,
    dataUpdatedAt,
  } = useNamespaceAutoPrunePolicies(
    props.organizationName,
    props.isUser,
    organization?.is_admin || false,
  );

  const {
    errorFetchingRepoPolicies,
    successFetchingRepoPolicies,
    isLoadingRepoPolicies,
    repoPolicies,
    repoPoliciesDataUpdatedAt,
  } = useFetchRepositoryAutoPrunePolicies(
    props.organizationName,
    props.repoName,
  );

  const {
    createRepoPolicy,
    successRepoPolicyCreation,
    errorRepoPolicyCreation,
    errorDetailsRepoPolicyCreation,
  } = useCreateRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  const {
    updateRepoPolicy,
    successRepoPolicyUpdation,
    errorRepoPolicyUpdation,
    errorDetailsRepoPolicyUpdation,
  } = useUpdateRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  const {
    deleteRepoPolicy,
    successRepoPolicyDeletion,
    errorRepoPolicyDeletion,
    errorDetailsRepoPolicyDeletion,
  } = useDeleteRepositoryAutoPrunePolicy(
    props.organizationName,
    props.repoName,
  );

  useEffect(() => {
    if (successFetchingRepoPolicies) {
      // Currently we only support one policy per repository but
      // this will change in the future.
      if (repoPolicies.length > 0) {
        const policy: RepositoryAutoPrunePolicy = repoPolicies[0];
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
  }, [
    successFetchingRepoPolicies,
    successFetchingPolicies,
    repoPoliciesDataUpdatedAt,
  ]);

  useEffect(() => {
    if (successRepoPolicyCreation) {
      addAlert({
        title: 'Successfully created repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyCreation]);

  useEffect(() => {
    if (successRepoPolicyUpdation) {
      addAlert({
        title: 'Successfully updated repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyUpdation]);

  useEffect(() => {
    if (successRepoPolicyDeletion) {
      addAlert({
        title: 'Successfully deleted repository auto-prune policy',
        variant: AlertVariant.Success,
      });
    }
  }, [successRepoPolicyDeletion]);

  useEffect(() => {
    if (errorRepoPolicyCreation) {
      addAlert({
        title: 'Could not create repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyCreation.toString(),
      });
    }
  }, [errorRepoPolicyCreation]);

  useEffect(() => {
    if (errorRepoPolicyUpdation) {
      addAlert({
        title: 'Could not update repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyUpdation.toString(),
      });
    }
  }, [errorRepoPolicyUpdation]);

  useEffect(() => {
    if (errorRepoPolicyDeletion) {
      addAlert({
        title: 'Could not delete repository auto-prune policy',
        variant: AlertVariant.Failure,
        message: errorDetailsRepoPolicyDeletion.toString(),
      });
    }
  }, [errorRepoPolicyDeletion]);

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
          deleteRepoPolicy(uuid);
        }
        return;
      default:
        // Reaching here indicates programming error, component should always be aware of valid methods
        return;
    }
    if (isNullOrUndefined(uuid)) {
      createRepoPolicy({method: method, value: value});
    } else {
      updateRepoPolicy({uuid: uuid, method: method, value: value});
    }
  };

  if (isLoadingRepoPolicies) {
    return <Spinner />;
  }

  if (!isNullOrUndefined(errorFetchingRepoPolicies)) {
    return <RequestError message={errorFetchingRepoPolicies.toString()} />;
  }

  return (
    <>
      <Conditional if={nsPolicies?.length > 0 && organization?.is_admin}>
        <Title
          headingLevel="h2"
          style={{paddingBottom: '.5em'}}
          data-testid="namespace-auto-prune-policy-heading"
        >
          Namespace Auto-Pruning Policies
        </Title>
        <Gallery>
          <DataList
            className="pf-v5-u-mb-lg"
            aria-label="Simple data list example"
            isCompact
          >
            <DataListItem aria-labelledby="simple-item1">
              <DataListItemRow>
                <DataListItemCells
                  dataListCells={
                    nsPolicies
                      ? [
                          <DataListCell
                            key="policy-method"
                            data-testid={'namespace-autoprune-policy-method'}
                          >
                            <span id="simple-item1">
                              <b>
                                {getAutoPrunePolicyType(nsPolicies[0]?.method)}:
                              </b>
                            </span>
                          </DataListCell>,
                          <DataListCell
                            key="policy-value"
                            data-testid={'namespace-autoprune-policy-value'}
                          >
                            <span id="simple-item1">
                              <b>{nsPolicies[0]?.value}</b>
                            </span>
                          </DataListCell>,
                        ]
                      : []
                  }
                />
              </DataListItemRow>
            </DataListItem>
          </DataList>
        </Gallery>
      </Conditional>
      <Title headingLevel="h2" style={{paddingBottom: '.5em'}}>
        Repository Auto-Pruning Policies
      </Title>
      <p style={{paddingBottom: '1em'}}>
        Auto-pruning policies automatically delete tags under this repository by
        a given method.
      </p>
      <Form id="autopruning-form" maxWidth="40%">
        <FormGroup
          isInline
          label="Prune Policy - select a method to prune tags"
          fieldId="method"
          isRequired
        >
          <FormSelect
            placeholder=""
            aria-label="repository-auto-prune-method"
            data-testid="repository-auto-prune-method"
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
              data-testid="repository-auto-prune-tag-count"
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
                data-testid="repository-auto-prune-tag-creation-date-value"
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

interface RepositoryAutoPruning {
  organizationName: string;
  repoName: string;
  isUser: boolean;
}
