import {useEffect, useState} from 'react';
import {
  Tabs,
  Tab,
  TabTitleText,
  Flex,
  FlexItem,
  FormGroup,
  Form,
  FormAlert,
  TextInput,
  FormSelect,
  FormSelectOption,
  ActionGroup,
  Button,
  Alert,
} from '@patternfly/react-core';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {humanizeTimeForExpiry, getSeconds, isValidEmail} from 'src/libs/utils';

type validate = 'success' | 'warning' | 'error' | 'default';

const GeneralSettings = (props: GeneralSettingsProps) => {
  const location = useLocation();
  const organizationName = props.organizationName;

  const {user} = useCurrentUser();
  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);
  const [error, setError] = useState<string>('');

  // Time Machine
  const timeMachineOptions = ['1 week', '2 weeks', '1 month', '1 year', 'Never'];
  const [timeMachineFormValue, setTimeMachineFormValue] = useState(
    timeMachineOptions[1],
  );
  const namespaceTimeMachineExpiry = isUserOrganization ? user.tag_expiration_s : (organization as any).tag_expiration_s;

  // Email
  const namespaceEmail = isUserOrganization ? user.email : (organization as any).email;
  const [emailFormValue, setEmailFormValue] = useState('');
  const [validated, setValidated] = useState<validate>('default');


  useEffect(() => {
    if (!loading){
      setEmailFormValue(namespaceEmail);
      const humanized_expiry = humanizeTimeForExpiry(parseInt(timeMachineFormValue));
      if (humanized_expiry == '7 days') {
        setTimeMachineFormValue(timeMachineOptions[0]);
      } else if (humanized_expiry == '14 days') {
        setTimeMachineFormValue(timeMachineOptions[1]);
      }
    }
  }, [loading, isUserOrganization]);


  const handleEmailChange = (emailFormValue: string) => {
    setEmailFormValue(emailFormValue);
    if (!emailFormValue) {
      setValidated('error');
      setError('Please enter email associate with organization');
      return;
    }

    if (namespaceEmail != emailFormValue) {
      if (isValidEmail(emailFormValue)) {
        setValidated('success');
        setError('');
      }
      else {
        setValidated('error');
        setError('Please enter a valid email address');
      }
    }
  }

  const checkForChanges = () => {
    if ((namespaceEmail != emailFormValue) && (validated == 'success')) {
      return true;
    } else {
      return false;
    }

    if (getSeconds(timeMachineFormValue) != namespaceTimeMachineExpiry) {
      return true;
    }
    return false;
  }

  function onSave() {

  }

  return (
    <Form id="form-form" maxWidth="70%">
      {validated === 'error' && (
        <FormAlert>
          <Alert variant="danger" title={error} aria-live="polite" isInline />
        </FormAlert>
      )}
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
          onChange={handleEmailChange}
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
          <Button
            variant="primary"
            type="submit"
            onClick={onSave}
            isDisabled={!checkForChanges()}
          >
            Save
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
};

// const BillingInformation = () => {
//   return <h1>Hello</h1>;
// };

export default function Settings(props: SettingsProps) {
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  const handleTabClick = (event, tabIndex) => {
    setActiveTabIndex(tabIndex);
  };

  const tabs = [
    {
      name: 'General Settings',
      id: 'generalsettings',
      content: <GeneralSettings organizationName={props.organizationName} />,
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

type SettingsProps = {
  organizationName: string;
};

type GeneralSettingsProps = {
  organizationName: string;
};
