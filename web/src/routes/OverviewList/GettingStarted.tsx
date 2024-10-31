import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  Split,
  SplitItem,
  Text,
  TextContent,
} from '@patternfly/react-core';

import {useTheme} from 'src/contexts/ThemeContext';
import './css/GettingStarted.scss';

export default function GettingStarted(props: GettingStartedProps) {
  const theme = useTheme();

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
                Welcome to Quay.io, the container registry platform for managing
                your cloud native artifacts, where you can securely store,
                distribute, and deploy them with confidence and ease - sign up
                now to get started!
              </Text>
            </TextContent>
          </CardBody>
          <CardFooter>
            <Button
              className="button-primary"
              component="a"
              href="/organization"
              size="lg"
              id="try-quayio-button"
            >
              Try free
            </Button>
            <Button
              variant="secondary"
              component="a"
              size="lg"
              id="purchase-quayio-button"
              onClick={props.onPaidPlansClick}
            >
              Sign up for paid plans
            </Button>
          </CardFooter>
        </SplitItem>
        <SplitItem isFilled />
        <SplitItem
          className={
            theme.isDarkTheme ? 'quay-screenshot-dark' : 'quay-screenshot'
          }
        />
      </Split>
    </Card>
  );
}

interface GettingStartedProps {
  onPaidPlansClick: () => void;
}
