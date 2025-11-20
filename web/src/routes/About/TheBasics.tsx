import React from 'react';
import {
  Card,
  CardBody,
  Flex,
  FlexItem,
  Grid,
  GridItem,
  Text,
  TextContent,
  TextVariants,
} from '@patternfly/react-core';
import {CalendarAltIcon, GlobeIcon} from '@patternfly/react-icons';
import CoreOSLogo from 'src/assets/coreos-globe-color-lg.png';
import RedHatLogo from 'src/assets/RedHat.svg';

interface InfoCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const InfoCard: React.FC<InfoCardProps> = ({icon, label, value}) => {
  return (
    <Card isCompact style={{height: '100%'}}>
      <CardBody
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          minHeight: '150px',
        }}
      >
        <Flex
          direction={{default: 'column'}}
          alignItems={{default: 'alignItemsCenter'}}
        >
          <FlexItem style={{fontSize: '2.5rem', marginBottom: '0.5rem'}}>
            {icon}
          </FlexItem>
          <FlexItem>
            <TextContent style={{textAlign: 'center'}}>
              <Text component={TextVariants.h4}>{label}</Text>
              <Text component={TextVariants.p}>{value}</Text>
            </TextContent>
          </FlexItem>
        </Flex>
      </CardBody>
    </Card>
  );
};

interface RedHatCardProps {
  logo: string;
  value: string;
}

const RedHatCard: React.FC<RedHatCardProps> = ({logo, value}) => {
  return (
    <Card isCompact style={{height: '100%'}}>
      <CardBody
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          minHeight: '150px',
        }}
      >
        <Flex
          direction={{default: 'column'}}
          alignItems={{default: 'alignItemsCenter'}}
        >
          <FlexItem style={{marginBottom: '0.5rem'}}>
            <img src={logo} alt="Red Hat" style={{height: '42px'}} />
          </FlexItem>
          <FlexItem>
            <TextContent style={{textAlign: 'center'}}>
              <Text component={TextVariants.p}>{value}</Text>
            </TextContent>
          </FlexItem>
        </Flex>
      </CardBody>
    </Card>
  );
};

export const TheBasics: React.FC = () => {
  return (
    <>
      <Grid hasGutter>
        <GridItem sm={12} md={6} lg={3}>
          <InfoCard icon={<CalendarAltIcon />} label="Founded" value="2012" />
        </GridItem>
        <GridItem sm={12} md={6} lg={3}>
          <InfoCard
            icon={<GlobeIcon />}
            label="Location"
            value="New York City, NY"
          />
        </GridItem>
        <GridItem sm={12} md={6} lg={3}>
          <InfoCard
            icon={
              <img src={CoreOSLogo} alt="CoreOS" style={{height: '42px'}} />
            }
            label="CoreOS"
            value="August, 2014"
          />
        </GridItem>
        <GridItem sm={12} md={6} lg={3}>
          <RedHatCard logo={RedHatLogo} value="January, 2018" />
        </GridItem>
      </Grid>
    </>
  );
};

export default TheBasics;
