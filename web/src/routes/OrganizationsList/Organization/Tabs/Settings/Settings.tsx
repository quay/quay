import {useEffect, useState} from 'react';
import {
  Tabs,
  Tab,
  TabTitleText,
  Flex,
  FlexItem,
  FormGroup,
  Form,
  TextInput,
  FormSelect,
  FormSelectOption,
  ActionGroup,
  Button,
} from '@patternfly/react-core';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';

const GeneralSettings = () => {
  const location = useLocation();
  const organizationName = location.pathname.split('/')[2];

  const {user} = useCurrentUser();
  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);

  // Time Machine
  const timeMachineOptions = ['1 week', '1 month', '1 year', 'Never'];
  const [timeMachineFormValue, setTimeMachineFormValue] = useState(
    timeMachineOptions[0],
  );

  // Email
  const [emailFormValue, setEmailFormValue] = useState('');
  useEffect(() => {
    if (!loading && organization) {
      setEmailFormValue((organization as any).email);
    } else if (isUserOrganization) {
      setEmailFormValue(user.email);
    }
  }, [loading, isUserOrganization]);

  return (
    <Form id="form-form" maxWidth="70%">
      <FormGroup
        isInline
        label="Organization"
        fieldId="form-organization"
        helperText={'Orgnization names cannot be changed once set.'}
      >
        <TextInput
          isDisabled
          type="text"
          id="form-name"
          value={organizationName}
        />
      </FormGroup>

      <FormGroup
        isInline
        label="Email"
        fieldId="form-email"
        helperText="The e-mail address associated with the organization."
      >
        <TextInput
          type="email"
          id="modal-with-form-form-name"
          value={emailFormValue}
          onChange={(val) => setEmailFormValue(val)}
        />
      </FormGroup>

      <FormGroup
        isInline
        label="Time Machine"
        fieldId="form-time-machine"
        helperText="The amount of time, after a tag is deleted, that the tag is accessible in time machine before being garbage collected."
      >
        <FormSelect
          placeholder="Time Machine"
          aria-label="Time Machine select"
          data-testid="arch-select"
          value={timeMachineFormValue}
          onChange={(val) => setTimeMachineFormValue(val)}
        >
          {timeMachineOptions.map((option, index) => (
            <FormSelectOption key={index} value={option} label={option} />
          ))}
        </FormSelect>
      </FormGroup>

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width={'100%'}
        >
          <Button variant="primary">Save</Button>
          <Button variant="link">Cancel</Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
};

// const BillingInformation = () => {
//   return <h1>Hello</h1>;
// };

export default function Settings() {
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  const handleTabClick = (event, tabIndex) => {
    setActiveTabIndex(tabIndex);
  };

  const tabs = [
    {
      name: 'General Settings',
      id: 'generalsettings',
      content: <GeneralSettings />,
    },
    // {
    //   name: 'Billing Information',
    //   id: 'billinginformation',
    //   content: <BillingInformation />,
    // },
  ];

  return (
    <Flex flexWrap={{default: 'nowrap'}}>
      <FlexItem>
        <Tabs
          activeKey={activeTabIndex}
          onSelect={handleTabClick}
          isVertical
          aria-label="Tabs in the vertical example"
          role="region"
        >
          {tabs.map((tab, tabIndex) => (
            <Tab
              key={tab.id}
              eventKey={tabIndex}
              title={<TabTitleText>{tab.name}</TabTitleText>}
            />
          ))}
        </Tabs>
      </FlexItem>

      <FlexItem
        alignSelf={{default: 'alignSelfCenter'}}
        style={{padding: '20px'}}
      >
        {tabs.at(activeTabIndex).content}
      </FlexItem>
    </Flex>
  );
}
