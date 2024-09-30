import {
  DataList,
  DataListCell,
  DataListItem,
  DataListItemCells,
  DataListItemRow,
  Gallery,
  Title,
} from '@patternfly/react-core';
import {
  AutoPruneMethod,
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
      <Gallery>
        <DataList
          className="pf-v5-u-mb-lg"
          aria-label={`Auto prune policy for ${props.title}`}
          isCompact
        >
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
                        <b>{getAutoPrunePolicyType(policy.method)}:</b>
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
                      style={
                        policy?.tagPattern != null
                          ? {display: 'block'}
                          : {display: 'none'}
                      }
                    >
                      <span id="simple-item1">
                        <b>
                          {policy?.tagPatternMatches
                            ? `matches`
                            : `does not match`}
                        </b>
                      </span>
                    </DataListCell>,
                    <DataListCell
                      key={`policy-tag-pattern-${index}`}
                      data-testid={`${props.testId}-tag-pattern`}
                      style={
                        policy?.tagPattern != null
                          ? {display: 'block'}
                          : {display: 'none'}
                      }
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
      </Gallery>
    </>
  );
}

enum AutoPrunePolicyType {
  NONE = 'None',
  TAG_NUMBER = 'Number of Tags',
  TAG_CREATION_DATE = 'Age of Tags',
}

// mapping between AutoPruneMethod and AutoPrunePolicyType values
const methodToPolicyType: Record<AutoPruneMethod, AutoPrunePolicyType> = {
  [AutoPruneMethod.NONE]: AutoPrunePolicyType.NONE,
  [AutoPruneMethod.TAG_NUMBER]: AutoPrunePolicyType.TAG_NUMBER,
  [AutoPruneMethod.TAG_CREATION_DATE]: AutoPrunePolicyType.TAG_CREATION_DATE,
};

// function to get the corresponding display string based on AutoPruneMethod
function getAutoPrunePolicyType(method: AutoPruneMethod): AutoPrunePolicyType {
  return methodToPolicyType[method];
}

interface ReadonlyAutoprunePolicyProps {
  title: string;
  policies: NamespaceAutoPrunePolicy[];
  testId?: string;
}
