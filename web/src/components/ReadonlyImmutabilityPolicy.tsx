import {
  DataList,
  DataListCell,
  DataListItem,
  DataListItemCells,
  DataListItemRow,
  Title,
} from '@patternfly/react-core';
import {ImmutabilityPolicy} from 'src/resources/ImmutabilityPolicyResource';

export default function ReadonlyImmutabilityPolicy(
  props: ReadonlyImmutabilityPolicyProps,
) {
  return (
    <>
      <Title
        headingLevel="h2"
        style={{paddingBottom: '.5em'}}
        data-testid={`${props.testId}-heading`}
      >
        {props.title}
      </Title>
      <DataList
        className="pf-v5-u-mb-lg"
        aria-label={`Immutability policy for ${props.title}`}
        isCompact
      >
        <DataListItem aria-labelledby="immutability-policies-header">
          <DataListItemRow>
            <DataListItemCells
              dataListCells={[
                <DataListCell key="policy-pattern-header">
                  <span>
                    <b>Tag Pattern</b>
                  </span>
                </DataListCell>,
                <DataListCell key="policy-behavior-header">
                  <span>
                    <b>Behavior</b>
                  </span>
                </DataListCell>,
              ]}
            />
          </DataListItemRow>
        </DataListItem>
        <DataListItem aria-labelledby="immutability-policy-list">
          {props.policies.map((policy, index) => (
            <DataListItemRow key={`policy-list-${index}`}>
              <DataListItemCells
                dataListCells={[
                  <DataListCell
                    key={`policy-pattern-${index}`}
                    data-testid={`${props.testId}-pattern-${index}`}
                  >
                    <span>
                      <code>{policy.tagPattern}</code>
                    </span>
                  </DataListCell>,
                  <DataListCell
                    key={`policy-behavior-${index}`}
                    data-testid={`${props.testId}-behavior-${index}`}
                  >
                    <span>
                      {policy.tagPatternMatches
                        ? 'Tags matching pattern are immutable'
                        : 'Tags NOT matching pattern are immutable'}
                    </span>
                  </DataListCell>,
                ]}
              />
            </DataListItemRow>
          ))}
        </DataListItem>
      </DataList>
    </>
  );
}

interface ReadonlyImmutabilityPolicyProps {
  title: string;
  policies: ImmutabilityPolicy[];
  testId?: string;
}
