import {render, screen} from 'src/test-utils';
import Review from './ReviewTeam';

const requiredIndicatorSelector = '.pf-v6-c-form__label-required';

function getRequiredIndicator(testId: string): Element | null | undefined {
  return screen
    .getByTestId(testId)
    .closest('.pf-v6-c-form__group')
    ?.querySelector(requiredIndicatorSelector);
}

describe('ReviewTeam', () => {
  it('leaves empty repository and member selections optional', () => {
    const {container} = render(
      <Review
        teamName="empty-team"
        description=""
        selectedRepos={[]}
        addedTeamMembers={[]}
      />,
    );

    expect(screen.getByTestId('empty-team-team-name-review')).toHaveValue(
      'empty-team',
    );
    expect(screen.getByTestId('-team-descr-review')).toHaveValue('');
    expect(screen.getByTestId('selected-repos-review')).toHaveValue('');
    expect(screen.getByTestId('selected-team-members-review')).toHaveValue('');
    expect(container.querySelectorAll(requiredIndicatorSelector)).toHaveLength(
      1,
    );
    expect(
      getRequiredIndicator('empty-team-team-name-review'),
    ).toBeInTheDocument();
    expect(
      getRequiredIndicator('selected-repos-review'),
    ).not.toBeInTheDocument();
    expect(
      getRequiredIndicator('selected-team-members-review'),
    ).not.toBeInTheDocument();
  });

  it('displays populated repository and member selections without requiring them', () => {
    const {container} = render(
      <Review
        teamName="populated-team"
        description="A populated review"
        selectedRepos={[{name: 'repository-one'}, {name: 'repository-two'}]}
        addedTeamMembers={[
          {name: 'user-one', kind: 'user', is_robot: false},
          {name: 'user-two', kind: 'user', is_robot: false},
        ]}
      />,
    );

    expect(screen.getByTestId('selected-repos-review')).toHaveValue(
      'repository-one, repository-two',
    );
    expect(screen.getByTestId('selected-team-members-review')).toHaveValue(
      'user-one, user-two',
    );
    expect(container.querySelectorAll(requiredIndicatorSelector)).toHaveLength(
      1,
    );
    expect(
      getRequiredIndicator('selected-repos-review'),
    ).not.toBeInTheDocument();
    expect(
      getRequiredIndicator('selected-team-members-review'),
    ).not.toBeInTheDocument();
  });
});
