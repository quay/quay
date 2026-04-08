import React from 'react';
import {Control, FieldErrors} from 'react-hook-form';
import {Divider, Title} from '@patternfly/react-core';
import {FormTextInput} from 'src/components/forms/FormTextInput';
import {OrgMirroringFormData} from './types';

interface OrgMirroringFiltersProps {
  control: Control<OrgMirroringFormData>;
  errors: FieldErrors<OrgMirroringFormData>;
}

export const OrgMirroringFilters: React.FC<OrgMirroringFiltersProps> = ({
  control,
  errors,
}) => {
  return (
    <>
      <Divider />
      <Title headingLevel="h3">Repository Filters</Title>

      <FormTextInput
        name="repositoryFilters"
        control={control}
        errors={errors}
        label="Filter Patterns"
        fieldId="repository_filters"
        placeholder="nginx, redis*, app-*"
        helperText="Comma-separated list of glob patterns to filter which repositories are mirrored. Leave empty to mirror all repositories."
        data-testid="repository-filters-input"
      />
    </>
  );
};
