import {
  ActionGroup,
  Button,
  Card,
  CardBody,
  DataList,
  DataListAction,
  DataListCell,
  DataListItem,
  DataListItemCells,
  DataListItemRow,
  Form,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  HelperText,
  HelperTextItem,
  TextInput,
  ValidatedOptions,
} from '@patternfly/react-core';
import {PencilAltIcon, TrashIcon} from '@patternfly/react-icons';
import {ImmutabilityPolicy} from '../resources/ImmutabilityPolicyResource';
import {useEffect, useState} from 'react';

export default function ImmutabilityPolicyForm(
  props: ImmutabilityPolicyFormProps,
) {
  const [uuid, setUuid] = useState<string | null>(null);
  const [tagPattern, setTagPattern] = useState<string>('');
  const [tagPatternMatches, setTagPatternMatches] = useState<boolean>(true);
  const [patternError, setPatternError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);

  useEffect(() => {
    if (props.successFetchingPolicies) {
      if (props.policy) {
        setUuid(props.policy.uuid ?? null);
        setTagPattern(props.policy.tagPattern ?? '');
        setTagPatternMatches(props.policy.tagPatternMatches ?? true);
        setPatternError(null);
        // New policies (no uuid) start in edit mode, or if isInline is set
        setIsEditing(!props.policy.uuid || props.isInline);
      } else {
        // Reset state when policy is cleared
        setUuid(null);
        setTagPattern('');
        setTagPatternMatches(true);
        setPatternError(null);
        setIsEditing(true);
      }
    }
  }, [props.policy, props.successFetchingPolicies, props.isInline]);

  const validatePattern = (pattern: string): boolean => {
    if (!pattern.trim()) {
      setPatternError('Tag pattern is required');
      return false;
    }
    if (pattern.length > 256) {
      setPatternError('Tag pattern must be 256 characters or less');
      return false;
    }
    try {
      new RegExp(pattern);
      setPatternError(null);
      return true;
    } catch (e) {
      setPatternError('Invalid regular expression pattern');
      return false;
    }
  };

  const handlePatternChange = (value: string) => {
    setTagPattern(value);
    if (value.trim()) {
      validatePattern(value);
    } else {
      setPatternError(null);
    }
  };

  const saveForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validatePattern(tagPattern)) {
      return;
    }
    props.onSave(uuid, tagPattern.trim(), tagPatternMatches);
    if (!props.isInline) {
      setIsEditing(false);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    if (uuid && props.onDelete) {
      props.onDelete(uuid);
    }
  };

  const handleCancel = () => {
    // Reset to original values from props
    if (props.policy) {
      setTagPattern(props.policy.tagPattern ?? '');
      setTagPatternMatches(props.policy.tagPatternMatches ?? true);
      setPatternError(null);
    }
    setIsEditing(false);
    // Call external onCancel if provided
    if (props.onCancel) {
      props.onCancel();
    }
  };

  // Compact view for existing saved policies (only when not inline mode)
  if (!isEditing && uuid && !props.isInline) {
    return (
      <DataList
        aria-label={`Immutability policy ${props.index}`}
        isCompact
        className="pf-v5-u-mb-sm"
      >
        <DataListItem aria-labelledby={`policy-${props.index}`}>
          <DataListItemRow>
            <DataListItemCells
              dataListCells={[
                <DataListCell key="pattern" width={2}>
                  <code data-testid="immutability-tag-pattern-display">
                    {tagPattern}
                  </code>
                </DataListCell>,
                <DataListCell key="behavior" width={3}>
                  <span data-testid="immutability-behavior-display">
                    {tagPatternMatches
                      ? 'Tags matching pattern are immutable'
                      : 'Tags NOT matching pattern are immutable'}
                  </span>
                </DataListCell>,
              ]}
            />
            <DataListAction
              aria-labelledby={`policy-${props.index}`}
              id={`policy-actions-${props.index}`}
              aria-label="Actions"
            >
              <Button
                variant="plain"
                onClick={() => setIsEditing(true)}
                aria-label="Edit policy"
                data-testid="edit-immutability-policy-btn"
              >
                <PencilAltIcon />
              </Button>
              {props.onDelete && (
                <Button
                  variant="plain"
                  onClick={handleDelete}
                  aria-label="Delete policy"
                  data-testid="delete-immutability-policy-btn"
                >
                  <TrashIcon />
                </Button>
              )}
            </DataListAction>
          </DataListItemRow>
        </DataListItem>
      </DataList>
    );
  }

  // Form content (shared between inline and card modes)
  const formContent = (
    <Form id={`immutability-policy-form-${props.index}`}>
      <FormGroup
        label="Tag Pattern"
        fieldId={`tag-pattern-${props.index}`}
        isRequired
      >
        <TextInput
          id={`tag-pattern-${props.index}`}
          value={tagPattern}
          onChange={(_, val) => handlePatternChange(val)}
          aria-label="Tag pattern"
          data-testid="immutability-tag-pattern"
          placeholder="e.g., v[0-9]+\\..*"
          validated={
            patternError ? ValidatedOptions.error : ValidatedOptions.default
          }
        />
        <FormHelperText>
          <HelperText>
            <HelperTextItem variant={patternError ? 'error' : 'default'}>
              {patternError ?? 'Regular expression pattern to match tag names'}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>
      <FormGroup
        label="Pattern Behavior"
        fieldId={`pattern-behavior-${props.index}`}
        isRequired
      >
        <FormSelect
          id={`pattern-behavior-${props.index}`}
          value={tagPatternMatches ? 'matches' : 'doesnotmatch'}
          onChange={(_, val) => setTagPatternMatches(val === 'matches')}
          aria-label="Pattern behavior"
          data-testid="immutability-pattern-behavior"
        >
          <FormSelectOption
            key="matches"
            value="matches"
            label="Tags matching pattern are immutable"
          />
          <FormSelectOption
            key="doesnotmatch"
            value="doesnotmatch"
            label="Tags NOT matching pattern are immutable"
          />
        </FormSelect>
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              {tagPatternMatches
                ? 'Tags that match the pattern will be immutable and cannot be modified or deleted'
                : 'Tags that do NOT match the pattern will be immutable and cannot be modified or deleted'}
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>
      <ActionGroup className="pf-v5-u-m-0">
        <Button
          variant="primary"
          type="submit"
          onClick={saveForm}
          data-testid="save-immutability-policy-btn"
        >
          Save
        </Button>
        {(uuid || props.onCancel) && (
          <Button
            variant="link"
            onClick={handleCancel}
            data-testid="cancel-immutability-policy-btn"
          >
            Cancel
          </Button>
        )}
      </ActionGroup>
    </Form>
  );

  // Inline mode: render form without card wrapper
  if (props.isInline) {
    return <div className="pf-v5-u-p-md">{formContent}</div>;
  }

  // Default: render form in card
  return (
    <Card isFlat className="pf-v5-u-mb-md">
      <CardBody>{formContent}</CardBody>
    </Card>
  );
}

interface ImmutabilityPolicyFormProps {
  onSave: (
    uuid: string | null,
    tagPattern: string,
    tagPatternMatches: boolean,
  ) => void;
  onDelete?: (uuid: string) => void;
  onCancel?: () => void;
  policy: ImmutabilityPolicy | null;
  index: number;
  successFetchingPolicies: boolean;
  isInline?: boolean;
}
