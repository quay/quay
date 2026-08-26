import {
  Card,
  CardBody,
  CardFooter,
  Icon,
  Content,
} from '@patternfly/react-core';
import React from 'react';
import ArrowRightIcon from '@patternfly/react-icons/dist/js/icons/arrow-right-icon';
import ExternalLinkAltIcon from '@patternfly/react-icons/dist/js/icons/external-link-alt-icon';
import {Link} from 'react-router-dom';
import './simple-service-widget.scss';

interface SimpleServiceWidgetProps {
  id: number;
  body: string;
  linkTitle: string;
  url: string;
  isExternal?: boolean;
}

export const SimpleServiceWidget: React.FunctionComponent<
  SimpleServiceWidgetProps
> = (props) => {
  return (
    <Card isPlain>
      <>
        <CardBody className="pf-v6-u-p-md pf-v6-u-pb-0">
          <Content
            key={props.id}
            className="pf-v6-u-display-flex pf-v6-u-flex-direction-column"
          >
            <Content component="p" className="pf-v6-u-flex-grow-1">
              {props.body}{' '}
            </Content>
          </Content>
        </CardBody>
        <CardFooter className="pf-v6-u-p-md">
          {props.isExternal ? (
            <a href={props.url}>
              {props.linkTitle}
              <Icon className="pf-v6-u-ml-sm" isInline>
                <ExternalLinkAltIcon />
              </Icon>
            </a>
          ) : (
            <Link to={props.url}>
              {props.linkTitle}
              <Icon className="pf-v6-u-ml-sm" isInline>
                <ArrowRightIcon />
              </Icon>
            </Link>
          )}
        </CardFooter>
      </>
    </Card>
  );
};
