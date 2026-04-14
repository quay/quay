import React from 'react';
import {render, screen} from '@testing-library/react';
import {useForm} from 'react-hook-form';
import {OrgMirroringRobotUser} from '../OrgMirroringRobotUser';
import {OrgMirroringFormData} from '../types';

jest.mock('src/components/EntitySearch', () => ({
  __esModule: true,
  default: (props: any) => <div data-testid="entity-search" />,
}));

jest.mock('src/contexts/UIContext', () => ({
  AlertVariant: {Failure: 'danger'},
}));

function TestWrapper() {
  const {control, formState} = useForm<OrgMirroringFormData>({
    defaultValues: {
      isEnabled: false,
      externalRegistryType: '',
      externalRegistryUrl: '',
      externalNamespace: '',
      robotUsername: '',
      visibility: 'public',
      repositoryFilters: '',
      syncStartDate: '',
      syncValue: '',
      syncUnit: 'minutes',
      username: '',
      password: '',
      verifyTls: true,
      httpProxy: '',
      httpsProxy: '',
      noProxy: '',
      skopeoTimeout: null,
    },
  });

  return (
    <OrgMirroringRobotUser
      control={control}
      errors={formState.errors}
      orgName="testorg"
      selectedRobot={null}
      setSelectedRobot={jest.fn()}
      robotOptions={[]}
      addAlert={jest.fn()}
    />
  );
}

describe('OrgMirroringRobotUser', () => {
  it('renders the Robot User label', () => {
    render(<TestWrapper />);
    expect(screen.getByText('Robot User')).toBeInTheDocument();
  });

  it('renders the required asterisk indicator on the Robot User field', () => {
    const {container} = render(<TestWrapper />);
    const requiredIndicator = container.querySelector(
      '.pf-v6-c-form__label-required',
    );
    expect(requiredIndicator).toBeInTheDocument();
    expect(requiredIndicator).toHaveTextContent('*');
  });

  it('renders the entity search input', () => {
    render(<TestWrapper />);
    expect(screen.getByTestId('entity-search')).toBeInTheDocument();
  });
});
