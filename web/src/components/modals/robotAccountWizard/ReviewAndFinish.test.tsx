import {render, screen, userEvent} from 'src/test-utils';
import ReviewAndFinish from './ReviewAndFinish';

function makeProps(overrides = {}) {
  return {
    robotName: 'myrobot',
    robotDescription: 'A test robot',
    selectedTeams: [
      {
        name: 'team1',
        role: 'admin',
        member_count: 3,
        last_updated: '2025-01-01',
      },
    ],
    selectedRepos: [
      {
        name: 'repo1',
        permission: 'Read',
        last_modified: '2025-01-01',
      },
    ],
    robotdefaultPerm: 'None',
    userNamespace: false,
    ...overrides,
  };
}

describe('ReviewAndFinish', () => {
  it('renders heading and robot name/description', () => {
    render(<ReviewAndFinish {...makeProps()} />);
    expect(screen.getByText('Review and finish')).toBeInTheDocument();
    expect(screen.getByDisplayValue('myrobot')).toBeInTheDocument();
    expect(screen.getByDisplayValue('A test robot')).toBeInTheDocument();
  });

  it('shows Teams toggle for org namespace', () => {
    render(<ReviewAndFinish {...makeProps()} />);
    expect(screen.getByText('Teams')).toBeInTheDocument();
    expect(screen.getByText('Repositories')).toBeInTheDocument();
    expect(screen.getByText('Default permissions')).toBeInTheDocument();
  });

  it('shows only Repositories toggle for user namespace', () => {
    render(<ReviewAndFinish {...makeProps({userNamespace: true})} />);
    expect(screen.getByText('Repositories')).toBeInTheDocument();
    expect(screen.queryByText('Teams')).not.toBeInTheDocument();
    expect(screen.queryByText('Default permissions')).not.toBeInTheDocument();
  });

  it('displays team data in Teams view', () => {
    render(<ReviewAndFinish {...makeProps()} />);
    expect(screen.getByText('team1')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('3 Members')).toBeInTheDocument();
  });

  it('switches to Repositories view', async () => {
    render(<ReviewAndFinish {...makeProps()} />);
    await userEvent.click(screen.getByText('Repositories'));
    expect(screen.getByText('repo1')).toBeInTheDocument();
    expect(screen.getByText('Read')).toBeInTheDocument();
  });

  it('displays singular Member for count of 1', () => {
    render(
      <ReviewAndFinish
        {...makeProps({
          selectedTeams: [
            {name: 'solo', role: 'member', member_count: 1, last_updated: null},
          ],
        })}
      />,
    );
    expect(screen.getByText('1 Member')).toBeInTheDocument();
    expect(screen.getByText('Never')).toBeInTheDocument();
  });
});
