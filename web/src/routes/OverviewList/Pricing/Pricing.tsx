import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardTitle,
  DataList,
  DataListItem,
  Dropdown,
  DropdownItem,
  ExpandableSection,
  Level,
  LevelItem,
  Title,
  Text,
  MenuToggle,
  MenuToggleElement,
  DropdownGroup,
  DropdownList,
} from '@patternfly/react-core';
import {ExternalLinkAltIcon} from '@patternfly/react-icons';
import React from 'react';
import '../css/Pricing.scss';

const pricings = {
  medium: '$125/month',
  large: '$250/month',
  XL: '$450/month',
  XXL: '$850/month',
  XXXL: '$1600/month',
  XXXXL: '$3100/month',
  XXXXXL: '$21700/month',
};

const pricingText = {
  medium: '50 private repos - $125/mo',
  large: '125 private repos - $250/mo',
  XL: '250 private repos - $450/mo',
  XXL: '500 private repos - $850/mo',
  XXXL: '1000 private repos - $1600/mo',
  XXXXL: '2000 private repos - $3100/mo',
  XXXXXL: '15000 private repos - $21700/mo',
};

const pricingLinks = {
  developer: 'https://quay.io/plans/?tab=enterprise',
  micro:
    'https://quay.io/organizations/new/?tab=enterprise&plan=bus-micro-2018',
  small:
    'https://quay.io/organizations/new/?tab=enterprise&plan=bus-small-2018',
  medium:
    'https://quay.io/organizations/new/?tab=enterprise&plan=bus-medium-2018',
  large:
    'https://quay.io/organizations/new/?tab=enterprise&plan=bus-large-2018',
  XL: 'https://quay.io/organizations/new/?tab=enterprise&plan=bus-xlarge-2018',
  XXL: 'https://quay.io/organizations/new/?tab=enterprise&plan=bus-500-2018',
  XXXL: 'https://quay.io/organizations/new/?tab=enterprise&plan=bus-1000-2018',
  XXXXL: 'https://quay.io/organizations/new/?tab=enterprise&plan=bus-2000-2018',
  XXXXXL:
    'https://quay.io/organizations/new/?tab=enterprise&plan=price_1LRztA2OoNF1TIf0SvSrz106',
};

const MorePlansCard: React.FunctionComponent = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [currentPricing, setPricing] = React.useState('medium');

  const onToggleClick = () => {
    setIsOpen(!isOpen);
  };

  const onSelect = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined,
  ) => {
    setIsOpen(false);
  };

  const dropdownItems = [
    <DropdownItem
      id="medium"
      key="medium"
      component="button"
      onClick={() => setPricing('medium')}
    >
      {pricingText['medium']}
    </DropdownItem>,
    <DropdownItem
      id="large"
      key="large"
      component="button"
      onClick={() => setPricing('large')}
    >
      {pricingText['large']}
    </DropdownItem>,
    <DropdownItem
      id="XL"
      key="XL"
      component="button"
      onClick={() => setPricing('XL')}
    >
      {pricingText['XL']}
    </DropdownItem>,
    <DropdownItem
      id="XXL"
      key="XXL"
      component="button"
      onClick={() => setPricing('XXL')}
    >
      {pricingText['XXL']}
    </DropdownItem>,
    <DropdownItem
      id="XXXL"
      key="XXXL"
      component="button"
      onClick={() => setPricing('XXXL')}
    >
      {pricingText['XXXL']}
    </DropdownItem>,
    <DropdownItem
      id="XXXXL"
      key="XXXXL"
      component="button"
      onClick={() => setPricing('XXXXL')}
    >
      {pricingText['XXXXL']}
    </DropdownItem>,
    <DropdownItem
      id="XXXXXL"
      key="XXXXXL"
      component="button"
      onClick={() => setPricing('XXXXXL')}
    >
      {pricingText['XXXXXL']}
    </DropdownItem>,
  ];

  const plansDropdown = (
    <Dropdown
      onSelect={onSelect}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id="plans-dropdown"
          onClick={onToggleClick}
          isExpanded={isOpen}
          style={{margin: '10px'}}
        >
          <Text id="selected-pricing">{pricingText[currentPricing]}</Text>
        </MenuToggle>
      )}
      isOpen={isOpen}
      style={{alignSelf: 'center', minWidth: '241px', maxWidth: '241px'}}
    >
      <DropdownGroup>
        <DropdownList id="plans-dropdown-options">{dropdownItems}</DropdownList>
      </DropdownGroup>
    </Dropdown>
  );

  return (
    <Card className="pricing-card">
      <CardTitle>
        <Title headingLevel="h3">Need larger plans?</Title>
      </CardTitle>
      {plansDropdown}
      <CardBody>
        -Unlimited public repositories <br />
        -Team-based permissions <br />
      </CardBody>
      <CardFooter style={{textAlign: 'center'}}>
        <Title id="pricing-value" headingLevel="h1">
          {pricings[currentPricing]}
        </Title>
        <Button
          variant="danger"
          style={{marginTop: '10px'}}
          component="a"
          href={pricingLinks[currentPricing]}
        >
          Start free trial <ExternalLinkAltIcon />
        </Button>
      </CardFooter>
    </Card>
  );
};

export default function Pricing() {
  const planCards = (
    <Level hasGutter style={{margin: '24px'}} id="purchase-plans">
      <LevelItem>
        <Card className="pricing-card">
          <CardTitle>
            <Title headingLevel="h3">Developer</Title>
          </CardTitle>
          <CardBody>
            -5 private repositories <br />
            -Unlimited public repositories <br />
          </CardBody>
          <CardFooter style={{textAlign: 'center'}}>
            <Title headingLevel="h1">$15/month</Title>
            <Button
              variant="danger"
              style={{marginTop: '10px'}}
              component="a"
              href={pricingLinks.developer}
            >
              Purchase plan <ExternalLinkAltIcon />
            </Button>
          </CardFooter>
        </Card>
      </LevelItem>

      <LevelItem>
        <Card className="pricing-card">
          <CardTitle>
            <Title headingLevel="h3">Micro</Title>
          </CardTitle>
          <CardBody>
            -10 private repositories <br />
            -Unlimited public repositories <br />
            -Team-based permissions <br />
          </CardBody>
          <CardFooter style={{textAlign: 'center'}}>
            <Title headingLevel="h1">$30/month</Title>
            <Button
              variant="danger"
              style={{marginTop: '10px'}}
              component="a"
              href={pricingLinks.micro}
            >
              Purchase plan <ExternalLinkAltIcon />
            </Button>
          </CardFooter>
        </Card>
      </LevelItem>

      <LevelItem>
        <Card className="pricing-card">
          <CardTitle>
            <Title headingLevel="h3">Small</Title>
          </CardTitle>
          <CardBody>
            -20 private repositories <br />
            -Unlimited public repositories <br />
            -Team-based permissions <br />
          </CardBody>
          <CardFooter style={{textAlign: 'center'}}>
            <Title headingLevel="h1">$60/month</Title>
            <Button
              variant="danger"
              style={{marginTop: '10px'}}
              component="a"
              href={pricingLinks.small}
            >
              Purchase plan <ExternalLinkAltIcon />
            </Button>
          </CardFooter>
        </Card>
      </LevelItem>

      <LevelItem>
        <MorePlansCard />
      </LevelItem>
    </Level>
  );

  return (
    <div>
      {planCards}

      <Card style={{margin: '24px'}} id="plans-info">
        <CardTitle>
          <Title headingLevel="h2">All plans include</Title>
        </CardTitle>
        <CardBody>
          <Text>
            Quay.io offers various benefits such as automated container building
            in response to git pushes, a 30-day free trial, public repositories
            with free public download pages, robot accounts for automatic
            software deployment, team management, SSL encryption, logging and
            auditing functionalities, and Invoice History for easy billing and
            purchasing management.
          </Text>
        </CardBody>
      </Card>

      <Card style={{margin: '24px'}}>
        <ExpandableSection
          isExpanded
          toggleContent={
            <Title
              headingLevel="h3"
              style={{color: 'var(--pf-v5-global--Color--100)'}}
            >
              How do I use Quay with my servers and code?
            </Title>
          }
          className="faq-section"
        >
          {`Using Quay with your infrastructure is separated into two main
            actions: building containers and distributing them to your servers.`}
          <br />
          <br />
          {`You can configure Quay to automatically build containers of your code
            on each commit. Integrations with GitHub, Bitbucket, GitLab and
            self-hosted Git repositories are supported. Each built container is
            stored on Quay and is available to be pulled down onto your servers.`}
          <br />
          <br />
          {`To distribute your private containers onto your servers, Docker or rkt
            must be configured with the correct credentials. Quay has
            sophisticated access controls — organizations, teams, robot accounts,
            and more — to give you full control over which servers can pull down
            your containers. An API can be used to automate the creation and
            management of these credentials.`}
        </ExpandableSection>
      </Card>
      <Card style={{margin: '24px'}}>
        <ExpandableSection
          isExpanded
          toggleContent={
            <Title
              headingLevel="h3"
              style={{color: 'var(--pf-v5-global--Color--100)'}}
            >
              How is Quay optimized for a team environment?
            </Title>
          }
          className="faq-section"
        >
          {`Quay's permission model is designed for teams. Each new user can be
          assigned to one or more teams, with specific permissions. Robot
          accounts, used for automated deployments, can be managed per team as
          well. This system allows for each development team to manage their own
          credentials.`}
          <br />
          <br />
          {`Full logging and auditing is integrated into every part of the
            application and API. Quay helps you dig into every action for more
            details.`}
        </ExpandableSection>
      </Card>

      <Card className="pricing-faqs-card">
        <CardTitle>Additional FAQs</CardTitle>
        <DataList aria-label="additional-faqs" isCompact>
          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Text className="faq-expand">Can I change my plan?</Text>
              }
            >
              <Text className="faq-field">
                Yes, you can change your plan at any time and your account will
                be pro-rated for the difference. For large organizations, Red
                Hat Quay offers unlimited users and repos.
              </Text>
            </ExpandableSection>
          </DataListItem>
          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Text className="faq-expand">
                  Do you offer special plans for business or academic
                  instututions?
                </Text>
              }
            >
              <Text className="faq-field">
                Please contact us at our support email address to discuss the
                details of your organization and intended usage.
              </Text>
            </ExpandableSection>
          </DataListItem>
          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Text className="faq-expand">Can I use Quay for free?</Text>
              }
            >
              <Text className="faq-field">
                Yes! We offer unlimited storage and serving of public
                repositories. We strongly believe in the open source community
                and will do what we can to help!
              </Text>
            </ExpandableSection>
          </DataListItem>
          <DataListItem>
            <ExpandableSection
              toggleContent={
                <Text className="faq-expand">
                  What types of payment do you accept?
                </Text>
              }
            >
              <Text className="faq-field">
                Quay uses Stripe as our payment processor, so we can accept any
                of the payment options they offer, which are currently: Visa,
                MasterCard, American Express, JCB, Discover and Diners Club.
              </Text>
            </ExpandableSection>
          </DataListItem>
        </DataList>
      </Card>
    </div>
  );
}
