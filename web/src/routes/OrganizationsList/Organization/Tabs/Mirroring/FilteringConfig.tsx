import {
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  HelperText,
  HelperTextItem,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import {useState, useEffect} from 'react';

export type FilteringType = 'NONE' | 'INCLUDE_LIST' | 'EXCLUDE_LIST' | 'REGEX';

interface FilteringConfigProps {
  filteringType: FilteringType;
  repoList: string;
  repoRegex: string;
  onChange: (type: FilteringType, list: string, regex: string) => void;
  errors?: Record<string, string>;
}

export default function FilteringConfig({
  filteringType,
  repoList,
  repoRegex,
  onChange,
  errors = {},
}: FilteringConfigProps) {
  const handleTypeChange = (value: string) => {
    onChange(value as FilteringType, repoList, repoRegex);
  };

  const handleListChange = (value: string) => {
    onChange(filteringType, value, repoRegex);
  };

  const handleRegexChange = (value: string) => {
    onChange(filteringType, repoList, value);
  };

  return (
    <>
      <FormGroup label="Repository Filtering" fieldId="filtering-type">
        <FormSelect
          id="filtering-type"
          data-testid="filtering-type-select"
          value={filteringType}
          onChange={(_event, value) => handleTypeChange(value)}
          aria-label="Repository filtering type"
        >
          <FormSelectOption
            value="NONE"
            label="No filtering (mirror all repositories)"
          />
          <FormSelectOption
            value="INCLUDE_LIST"
            label="Include list (only mirror specified repositories)"
          />
          <FormSelectOption
            value="EXCLUDE_LIST"
            label="Exclude list (mirror all except specified)"
          />
          <FormSelectOption
            value="REGEX"
            label="Regex pattern (mirror matching repositories)"
          />
        </FormSelect>
        <FormHelperText>
          <HelperText>
            <HelperTextItem>
              Choose how to filter which repositories are mirrored from the
              source
            </HelperTextItem>
          </HelperText>
        </FormHelperText>
      </FormGroup>

      {(filteringType === 'INCLUDE_LIST' ||
        filteringType === 'EXCLUDE_LIST') && (
        <FormGroup
          label={
            filteringType === 'INCLUDE_LIST'
              ? 'Repositories to Include'
              : 'Repositories to Exclude'
          }
          fieldId="repo-list"
        >
          <TextArea
            id="repo-list"
            data-testid="repo-list-input"
            value={repoList}
            onChange={(_event, value) => handleListChange(value)}
            placeholder="repo1&#10;repo2&#10;repo3"
            aria-label="Repository list"
            rows={5}
            validated={errors.repo_list ? 'error' : 'default'}
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                Enter one repository name per line
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
          {errors.repo_list && (
            <HelperText>
              <HelperTextItem variant="error">
                {errors.repo_list}
              </HelperTextItem>
            </HelperText>
          )}
        </FormGroup>
      )}

      {filteringType === 'REGEX' && (
        <FormGroup label="Regex Pattern" fieldId="repo-regex">
          <TextInput
            id="repo-regex"
            data-testid="repo-regex-input"
            type="text"
            value={repoRegex}
            onChange={(_event, value) => handleRegexChange(value)}
            placeholder="^prod-.*"
            aria-label="Regex pattern"
            validated={errors.repo_regex ? 'error' : 'default'}
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem>
                Enter a regular expression to match repository names
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
          {errors.repo_regex && (
            <HelperText>
              <HelperTextItem variant="error">
                {errors.repo_regex}
              </HelperTextItem>
            </HelperText>
          )}
        </FormGroup>
      )}
    </>
  );
}
