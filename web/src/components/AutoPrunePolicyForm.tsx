import {
  ActionGroup,
  Button,
  Flex,
  Form,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  HelperText,
  HelperTextItem,
  NumberInput,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {
  AutoPruneMethod,
  NamespaceAutoPrunePolicy,
} from '../resources/NamespaceAutoPruneResource';
import Conditional from './empty/Conditional';
import {shorthandTimeUnits} from '../routes/OrganizationsList/Organization/Tabs/Settings/AutoPruning';

import {useEffect, useState} from 'react';

export default function AutoPrunePolicyForm(props: AutoPrunePolicyForm) {
  const [uuid, setUuid] = useState<string>(null);
  const [method, setMethod] = useState<AutoPruneMethod>(AutoPruneMethod.NONE);
  const [tagCount, setTagCount] = useState<number>(20);
  const [tagCreationDateValue, setTagCreationDateValue] = useState<number>(7);
  const [tagCreationDateUnit, setTagCreationDateUnit] = useState<string>('d');
  const [tagPatternMatches, setTagPatternMatches] = useState<boolean>(true);
  const [tagPattern, setTagPattern] = useState<string>('');

  useEffect(() => {
    if (props.successFetchingPolicies) {
      if (props.policy) {
        setMethod(props.policy.method);
        setUuid(props.policy.uuid);
        setTagPattern(
          props.policy.tagPattern == null ? '' : props.policy.tagPattern,
        );
        setTagPatternMatches(props.policy.tagPatternMatches);
        switch (props.policy.method) {
          case AutoPruneMethod.TAG_NUMBER: {
            setTagCount(props.policy.value as number);
            break;
          }
          case AutoPruneMethod.TAG_CREATION_DATE: {
            const tagAgeValue = (props.policy.value as string).match(/\d+/g);
            const tagAgeUnit = (props.policy.value as string).match(
              /[a-zA-Z]+/g,
            );
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
        setTagPattern('');
        setTagPatternMatches(true);
      }
    }
  }, [props.policy]);

  const saveForm = (e) => {
    e.preventDefault();
    let value = null;
    switch (method) {
      case AutoPruneMethod.TAG_NUMBER:
        value = tagCount;
        break;
      case AutoPruneMethod.TAG_CREATION_DATE:
        value = `${String(tagCreationDateValue)}${tagCreationDateUnit}`;
        break;
      default:
        break;
    }
    props.onSave(method, value, uuid, tagPattern, tagPatternMatches);
  };

  return (
    <Form id={`autoprune-policy-form-${props.index}`} maxWidth="70%">
      <Title headingLevel="h3" style={{paddingTop: '1em'}}>
        Policy {props.index + 1}
      </Title>
      <FormGroup
        isInline
        label="Prune Policy - select a method to prune tags"
        fieldId="method"
        isRequired
      >
        <FormSelect
          placeholder=""
          aria-label="auto-prune-method"
          data-testid="auto-prune-method"
          value={method}
          onChange={(_, val) => setMethod(val as AutoPruneMethod)}
        >
          <FormSelectOption key={1} value={AutoPruneMethod.NONE} label="None" />
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
            data-testid="auto-prune-tag-count"
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                All tags sorted by earliest creation date will be deleted until
                the repository total falls below the threshold
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
              data-testid="auto-prune-tag-creation-date-value"
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
      <Conditional if={method !== AutoPruneMethod.NONE}>
        <FormGroup label="Tag pattern" isInline>
          <div style={{display: 'flex'}}>
            <FormSelect
              style={{width: '10em'}}
              id="selection"
              value={tagPatternMatches ? 'matches' : 'doesnotmatch'}
              onChange={(e, val) => {
                setTagPatternMatches(val === 'matches');
              }}
              aria-label="tag pattern matches"
            >
              <FormSelectOption key={0} value="matches" label="match" />
              <FormSelectOption
                key={1}
                value="doesnotmatch"
                label="does not match"
              />
            </FormSelect>
          </div>
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                {tagPatternMatches
                  ? 'Only tags matching the given regex pattern will be pruned'
                  : 'Only tags not matching the given regex pattern will be pruned'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
        <FormGroup isInline>
          <div style={{display: 'flex'}}>
            <TextInput
              style={{width: '25em'}}
              value={tagPattern}
              onChange={(e, val) =>
                val !== '' ? setTagPattern(val) : setTagPattern('')
              }
              aria-label="tag pattern"
              data-testid="tag-pattern"
            />
          </div>
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                The regex pattern to match tags against. Defaults to all tags if
                left empty.
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
      </Conditional>
      <ActionGroup style={{margin: '0'}}>
        <Flex justifyContent={{default: 'justifyContentFlexEnd'}} width="100%">
          <Button variant="primary" type="submit" onClick={saveForm}>
            Save
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
}

interface AutoPrunePolicyForm {
  onSave: (method, value, uuid, tagPattern, tagPatternMatches) => void;
  policy: NamespaceAutoPrunePolicy;
  index: number;
  successFetchingPolicies: boolean;
}
