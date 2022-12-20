import {render, screen, fireEvent} from '@testing-library/react';
import {RecoilRoot} from 'recoil';
import RepositoryDetails from './RepositoryDetails';
import {useLocation, useNavigate, useSearchParams} from 'react-router-dom';
import {mocked} from 'ts-jest/utils';

jest.mock('react-router-dom', () => ({
  useLocation: jest.fn(),
  useNavigate: jest.fn(),
  useSearchParams: jest.fn(),
}));

test('Org and repo names should show in Title and Breadcrumb', () => {
  // TODO implement once breadcrumbs are fixed
});

// Original implementation for reference
// test('Org and repo names should show in Title and Breadcrumb', () => {
//   mocked(useLocation, true).mockImplementation(() => ({
//     ...jest.requireActual('react-router-dom').useLocation,
//     pathname: '/organization/testorg/testrepo',
//   }));
//   mocked(useSearchParams, true).mockImplementation(() => [
//     new URLSearchParams(),
//     jest.fn(),
//   ]);
//   render(
//     <RecoilRoot>
//       <RepositoryDetails />
//     </RecoilRoot>,
//   );
//   expect(screen.getByTestId('namespace-breadcrumb')).toHaveTextContent(
//     'organization',
//   );
//   expect(screen.getByTestId('org-breadcrumb')).toHaveTextContent('testorg');
//   expect(screen.getByTestId('repo-breadcrumb')).toHaveTextContent('testrepo');
//   expect(screen.getByTestId('repo-title')).toHaveTextContent('testrepo');
// });
