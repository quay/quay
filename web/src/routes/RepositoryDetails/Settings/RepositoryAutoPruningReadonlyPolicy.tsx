import {
  DataList,
  DataListCell,
  DataListItem,
  DataListItemCells,
  DataListItemRow,
  Title,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  getAutoPruneMethodLabel,
  NamespaceAutoPrunePolicy,
} from 'src/resources/NamespaceAutoPruneResource';

export default function ReadonlyAutoprunePolicy(
  props: ReadonlyAutoprunePolicyProps,
) {
  return (
    <>
      <Title
        headingLevel="h2"
        style={{paddingBottom: '.5em'}}
        data-testid="namespace-auto-prune-policy-heading"
      >
        {props.title}
      </Title>
      <DataList
        className="pf-v6-u-mb-lg"
        aria-label={`Auto prune policy for ${props.title}`}
        isCompact
      >
        <DataListItem aria-labelledby="autoprune-policies-header">
          <DataListItemRow>
            <DataListItemCells
              dataListCells={[
                <DataListCell key="policy-method-header">
                  <span>
                    <b>Method</b>
                  </span>
                </DataListCell>,
                <DataListCell key="policy-value-header">
                  <span>
                    <b>Value</b>
                  </span>
                </DataListCell>,
                <DataListCell key="policy-tag-pattern-matches">
                  <span>
                    <b>Tag Pattern Matches</b>
                  </span>
                </DataListCell>,
                <DataListCell key="policy-tag-pattern">
                  <span>
                    <b>Tag Pattern</b>
                  </span>
                </DataListCell>,
              ]}
            />
          </DataListItemRow>
        </DataListItem>
        <DataListItem aria-labelledby="simple-item1">
          {props.policies.map((policy, index) => (
            <DataListItemRow key={`policy-list-${index}`}>
              <DataListItemCells
                dataListCells={[
                  <DataListCell
                    key={`policy-method-${index}`}
                    data-testid={`${props.testId}-method`}
                  >
                    <span id="simple-item1">
                      <b>{getAutoPruneMethodLabel(policy.method)}</b>
                    </span>
                  </DataListCell>,
                  <DataListCell
                    key={`policy-value-${index}`}
                    data-testid={`${props.testId}-value`}
                  >
                    <span id="simple-item1">
                      <b>{policy?.value}</b>
                    </span>
                  </DataListCell>,
                  <DataListCell
                    key={`policy-matches-${index}`}
                    data-testid={`${props.testId}-tag-pattern-matches`}
                  >
                    <Conditional if={!isNullOrUndefined(policy.tagPattern)}>
                      <span id="simple-item1">
                        <b>
                          {isNullOrUndefined(policy?.tagPatternMatches) ||
                          policy.tagPatternMatches
                            ? `matches`
                            : `does not match`}
                        </b>
                      </span>
                    </Conditional>
                  </DataListCell>,
                  <DataListCell
                    key={`policy-tag-pattern-${index}`}
                    data-testid={`${props.testId}-tag-pattern`}
                  >
                    <span id="simple-item1">
                      <b>{policy?.tagPattern}</b>
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

interface ReadonlyAutoprunePolicyProps {
  title: string;
  policies: NamespaceAutoPrunePolicy[];
  testId?: string;
}
