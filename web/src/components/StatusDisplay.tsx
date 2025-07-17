import React from 'react';
import {
  Card,
  CardBody,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Flex,
  FlexItem,
  Title,
} from '@patternfly/react-core';

interface StatusItem {
  label: string;
  value: string | React.ReactNode;
  action?: React.ReactNode;
}

interface StatusDisplayProps {
  title?: string;
  items: StatusItem[];
  'data-testid'?: string;
}

export function StatusDisplay({
  title,
  items,
  'data-testid': dataTestId,
}: StatusDisplayProps) {
  return (
    <>
      {title && <Title headingLevel="h3">{title}</Title>}
      <Card isFlat data-testid={dataTestId}>
        <CardBody>
          <DescriptionList isHorizontal>
            {items.map((item, index) => (
              <DescriptionListGroup key={index}>
                <DescriptionListTerm>{item.label}</DescriptionListTerm>
                <DescriptionListDescription>
                  {item.action ? (
                    <Flex>
                      <FlexItem flex={{default: 'flex_1'}}>
                        {item.value}
                      </FlexItem>
                      <FlexItem>{item.action}</FlexItem>
                    </Flex>
                  ) : (
                    item.value
                  )}
                </DescriptionListDescription>
              </DescriptionListGroup>
            ))}
          </DescriptionList>
        </CardBody>
      </Card>
    </>
  );
}
