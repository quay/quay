import {
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
} from '@patternfly/react-core';
import {useState} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function CreateBuildTriggerDropdown(
  props: CreateBuildTriggerDropdownProps,
) {
  const quayConfig = useQuayConfig();
  const [isOpen, setIsOpen] = useState(false);

  const dropdownItems = [
    <DropdownItem
      key="create-custom-git-trigger"
      onClick={() => {
        setIsOpen(false);
      }}
    >
      <a href={getRedirectUrl('customgit', props.namespace, props.repo)}>
        Custom Git Repository Push
      </a>
    </DropdownItem>,
  ];

  if (quayConfig?.features?.GITHUB_BUILD) {
    dropdownItems.push(
      <DropdownItem
        key="create-github-trigger"
        onClick={() => {
          setIsOpen(false);
        }}
      >
        <a
          id="create-github-trigger-link"
          href={getRedirectUrl('github', props.namespace, props.repo)}
        >
          GitHub Repository Push
        </a>
      </DropdownItem>,
    );
  }

  // To be enabled later
  // if(quayConfig?.features?.BITBUCKET_BUILD){
  //     dropdownItems.push(<DropdownItem
  //         key="create-bitbucket-trigger"
  //         onClick={() => {
  //             setIsOpen(false);
  //         }}
  //     >
  //         <a href={getRedirectUrl('bitbucket', props.namespace, props.repo)}>
  //             Bitbucket Repository Push
  //         </a>
  //     </DropdownItem>)
  // }

  if (quayConfig?.features?.GITLAB_BUILD) {
    dropdownItems.push(
      <DropdownItem
        key="create-gitlab-trigger"
        onClick={() => {
          setIsOpen(false);
        }}
      >
        <a href={getRedirectUrl('gitlab', props.namespace, props.repo)}>
          GitLab Repository Push
        </a>
      </DropdownItem>,
    );
  }

  return (
    <Dropdown
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          id="create-trigger-dropdown"
          data-testid="create-trigger-dropdown"
          aria-label="Create build trigger"
          variant="primary"
          onClick={() => setIsOpen(() => !isOpen)}
          isExpanded={isOpen}
        >
          Create Build Trigger
        </MenuToggle>
      )}
      isOpen={isOpen}
      onOpenChange={(isOpen) => setIsOpen(isOpen)}
      popperProps={{position: 'right'}}
      shouldFocusToggleOnSelect
    >
      <DropdownList>{dropdownItems}</DropdownList>
    </Dropdown>
  );
}

function getRedirectUrl(service: string, namespace: string, repo: string) {
  const quayConfig = useQuayConfig();
  const schemeAndDomain =
    quayConfig.config['PREFERRED_URL_SCHEME'] +
    '://' +
    quayConfig.config['SERVER_HOSTNAME'];
  switch (service) {
    case 'github': {
      const redirectUri =
        schemeAndDomain +
        '/oauth2/github/callback/trigger/' +
        namespace +
        '/' +
        repo;
      const clientId = quayConfig.oauth['GITHUB_TRIGGER_CONFIG']['CLIENT_ID'];
      const authorizeUrl =
        quayConfig.oauth['GITHUB_TRIGGER_CONFIG']['AUTHORIZE_ENDPOINT'] +
        '?' +
        'client_id=' +
        clientId +
        '&redirect_uri=' +
        redirectUri +
        '&scope=repo,user:email';
      return authorizeUrl;
    }
    case 'bitbucket':
      return schemeAndDomain + '/bitbucket/setup/' + namespace + '/' + repo;
    case 'gitlab': {
      const redirectUri = schemeAndDomain + '/oauth2/gitlab/callback/trigger';
      const clientId = quayConfig.oauth['GITLAB_TRIGGER_CONFIG']['CLIENT_ID'];
      const authorizeUrl =
        quayConfig.oauth['GITLAB_TRIGGER_CONFIG']['AUTHORIZE_ENDPOINT'] +
        '?' +
        'client_id=' +
        clientId +
        '&redirect_uri=' +
        redirectUri +
        '&scope=api%20write_repository%20openid&response_type=code&state=repo:' +
        namespace +
        '/' +
        repo;
      return authorizeUrl;
    }
    case 'customgit':
      return schemeAndDomain + '/customtrigger/setup/' + namespace + '/' + repo;
  }
}

interface CreateBuildTriggerDropdownProps {
  namespace: string;
  repo: string;
}
