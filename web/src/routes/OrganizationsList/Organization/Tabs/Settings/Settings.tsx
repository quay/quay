import {useEffect, useState, ReactNode} from 'react';
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
  AlertGroup,
} from '@patternfly/react-core';
import {useLocation} from 'react-router-dom';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {IOrganization} from 'src/resources/OrganizationResource';
import {humanizeTimeForExpiry, getSeconds, isValidEmail} from 'src/libs/utils';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

type validate = 'success' | 'warning' | 'error' | 'default';
const timeMachineOptions = {
  '0s': 'a few seconds',
  '1d': 'a day',
  '1w': '7 days',
  '2w': '14 days',
  '4w': 'a month',
};

const GeneralSettings = (props: GeneralSettingsProps) => {
  const location = useLocation();
  const quayConfig = useQuayConfig();
  const organizationName = props.organizationName;
  const {user, loading: isUserLoading} = useCurrentUser();
  const {organization, isUserOrganization, loading} =
    useOrganization(organizationName);
  const [error, setError] = useState<string>('');

  const {updateOrgSettings} = useOrganizationSettings({
    name: props.organizationName,
    onSuccess: (result) => {
      setAlerts((prevAlerts) => {
        return [
          ...prevAlerts,
          <Alert
            key="alert"
            variant="success"
            title="Successfully updated settings"
            isInline={true}
            timeout={5000}
          />,
        ];
      });
    },
    onError: (err) => {
      setAlerts((prevAlerts) => {
        return [
          ...prevAlerts,
          <Alert
            key="alert"
            variant="danger"
            title={err.response.data.error_message}
            isInline={true}
            timeout={5000}
          />,
        ];
      });
    },
  });

  const [alerts, setAlerts] = useState<ReactNode[]>([]);

  // Time Machine
  const [timeMachineFormValue, setTimeMachineFormValue] = useState(
    timeMachineOptions[quayConfig?.config?.TAG_EXPIRATION_OPTIONS[0]],
  );
  const namespaceTimeMachineExpiry = isUserOrganization
    ? user?.tag_expiration_s
    : (organization as IOrganization)?.tag_expiration_s;

  // Email
  const namespaceEmail = isUserOrganization
    ? user?.email || ''
    : (organization as any)?.email || '';
  const [emailFormValue, setEmailFormValue] = useState<string>('');
  const [validated, setValidated] = useState<validate>('default');

  useEffect(() => {
    setEmailFormValue(namespaceEmail);
    const humanized_expiry = humanizeTimeForExpiry(namespaceTimeMachineExpiry);
    for (const key of Object.keys(timeMachineOptions)) {
      if (humanized_expiry == timeMachineOptions[key]) {
        setTimeMachineFormValue(key);
        break;
      }
    }
  }, [loading, isUserLoading, isUserOrganization]);

  const handleEmailChange = (emailFormValue: string) => {
    setEmailFormValue(emailFormValue);
    if (namespaceEmail == emailFormValue) {
      setValidated('default');
      setError('');
      return;
    }

    if (!emailFormValue) {
      setValidated('error');
      setError('Please enter email associate with namespace');
      return;
    }

    if (namespaceEmail != emailFormValue) {
      if (isValidEmail(emailFormValue)) {
        setValidated('success');
        setError('');
      } else {
        setValidated('error');
        setError('Please enter a valid email address');
      }
    }
  };

  const checkForChanges = () => {
    if (namespaceEmail != emailFormValue) {
      return validated == 'success';
    }

    return getSeconds(timeMachineFormValue) != namespaceTimeMachineExpiry;
  };

  const updateSettings = async () => {
    try {
      const response = await updateOrgSettings({
        namespace: props.organizationName,
        tag_expiration_s:
          getSeconds(timeMachineFormValue) != namespaceTimeMachineExpiry
            ? getSeconds(timeMachineFormValue)
            : null,
        email: namespaceEmail != emailFormValue ? emailFormValue : null,
        isUser: isUserOrganization,
      });
      return response;
    } catch (error) {
      addDisplayError('Unable to update namespace settings', error);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    updateSettings();
  };

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
        helperText={'Namespace names cannot be changed once set.'}
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
          {quayConfig?.config?.TAG_EXPIRATION_OPTIONS.map((option, index) => (
            <FormSelectOption
              key={index}
              value={option}
              label={timeMachineOptions[option]}
            />
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
            onClick={(event) => onSubmit(event)}
            isDisabled={!checkForChanges()}
          >
            Save
          </Button>
        </Flex>
      </ActionGroup>
      <AlertGroup isLiveRegion>{alerts}</AlertGroup>
    </Form>
  );
};

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
