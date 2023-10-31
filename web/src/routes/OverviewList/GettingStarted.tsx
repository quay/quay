import {
  Button,
  Card,
  CardTitle,
  CardBody,
  CardFooter,
  Text,
  TextContent,
  Split,
  SplitItem,
} from '@patternfly/react-core';

import './css/GettingStarted.scss';

export default function GettingStarted() {
  return (
    <Card isFlat style={{margin: '24px'}}>
      <Split>
        <SplitItem>
          <CardTitle>
            <Text component="h1">Get started with Quay.io</Text>
          </CardTitle>
          <CardBody>
            <TextContent>
              <Text component="p">
                Welcome to Quay.io, the perfect platform for managing your
                container images, where you can securely store, distribute, and
                deploy them with confidence and ease - sign up now to get
                started!
              </Text>
            </TextContent>
          </CardBody>
          <CardFooter>
            <Button
              className="button-primary"
              component="a"
              href="https://quay.io"
              size="lg"
              id="try-quayio-button"
            >
              Try Quay.io free
            </Button>
            <Button
              variant="secondary"
              component="a"
              href="https://quay.io/plans/"
              size="lg"
              id="purchase-quayio-button"
            >
              Purchase private repository
            </Button>
          </CardFooter>
        </SplitItem>
        <SplitItem isFilled />
        <SplitItem className="quay-screenshot" />
      </Split>
    </Card>
  );
}
