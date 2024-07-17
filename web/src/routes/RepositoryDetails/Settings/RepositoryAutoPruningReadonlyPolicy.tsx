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
            <DataListItemRow>
              <DataListItemCells
                dataListCells={
                  props.policies
                    ? [
                        <DataListCell
                          key="policy-method"
                          data-testid={`${props.testId}-method`}
                        >
                          <span id="simple-item1">
                            <b>
                              {getAutoPrunePolicyType(
                                props.policies[0]?.method,
                              )}
                              :
                            </b>
                          </span>
                        </DataListCell>,
                        <DataListCell
                          key="policy-value"
                          data-testid={`${props.testId}-value`}
                        >
                          <span id="simple-item1">
                            <b>{props.policies[0]?.value}</b>
                          </span>
                        </DataListCell>,
                      ]
                    : []
                }
              />
            </DataListItemRow>
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
