import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Button,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {
  IOAuthApplication,
  useBulkDeleteOAuthApplications,
  useFetchOAuthApplications,
} from 'src/hooks/UseOAuthApplications';
import OAuthApplicationsToolbar from './OAuthApplicationsToolbar';
import DeleteOAuthApplicationKebab from './DeleteOAuthApplicationsKebab';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import Conditional from 'src/components/empty/Conditional';
import {BulkOperationError, addDisplayError} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import ErrorModal from 'src/components/errors/ErrorModal';
import Empty from 'src/components/empty/Empty';
import {KeyIcon} from '@patternfly/react-icons';

export const oauthApplicationColumnName = {
  name: 'Application Name',
  application_uri: 'Application URI',
};

export default function OAuthApplicationsList(
  props: OAuthApplicationsListProps,
) {
  const {
    loading,
    errorLoadingOAuthApplications,
    oauthApplications,
    paginatedOAuthApplications,
    filteredOAuthApplications,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchOAuthApplications(props.orgName);

  console.log(oauthApplications);

  const [selectedOAuthApplications, setSelectedOAuthApplications] = useState<
    IOAuthApplication[]
  >([]);

  const [bulkDeleteModalIsOpen, setBulkDeleteModalIsOpen] = useState(false);
  const [err, setError] = useState<string[]>();
  const {addAlert} = useAlerts();

  const onSelectPermission = (
    permission: IOAuthApplication,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedOAuthApplications((prevSelected) => {
      const otherSelectedOAuthApplications = prevSelected.filter(
        (p) => p.name !== permission.name,
      );
      return isSelecting
        ? [...otherSelectedOAuthApplications, permission]
        : otherSelectedOAuthApplications;
    });
  };

  const mapOfColNamesToTableData = {
    Name: {
      label: 'name',
      transformFunc: (oauthApplication: IOAuthApplication) => {
        return `${oauthApplication.name}`;
      },
    },
    // 'Permission Applied To': {
    //   label: 'appliedTo',
    //   transformFunc: (perm: IOAuthApplication) => perm.appliedTo,
    // },
    // Permission: {
    //   label: 'permission',
    //   transformFunc: (perm: IOAuthApplication) => (
    //     <Dropdown
    //       toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
    //         <MenuToggle ref={toggleRef} id="toggle-disabled" isDisabled>
    //           {perm.permission}
    //         </MenuToggle>
    //       )}
    //       isOpen={false}
    //     >
    //       <DropdownList>
    //         <DropdownItem>{perm.permission}</DropdownItem>
    //       </DropdownList>
    //     </Dropdown>
    //   ),
    // },
  };

  const {bulkDeleteOAuthApplications} = useBulkDeleteOAuthApplications({
    orgName: props.orgName,
    onSuccess: () => {
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedOAuthApplications([]);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted default permissions`,
      });
    },
    onError: (err) => {
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        err.getErrors().forEach((error, perm) => {
          addAlert({
            variant: AlertVariant.Failure,
            title: `Could not delete  default permission for ${perm}: ${error.error}`,
          });
          errMessages.push(
            addDisplayError(
              `Failed to delete default permission created by: ${perm}`,
              error.error,
            ),
          );
        });
        setError(errMessages);
      } else {
        setError([addDisplayError('Failed to delete default permission', err)]);
      }
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedOAuthApplications([]);
    },
  });

  const handleBulkDeleteModalToggle = () => {
    setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
  };

  if (loading) {
    return <Spinner />;
  }

  if (errorLoadingOAuthApplications) {
    return (
      <>
        <RequestError message={'Unable to load OAuth Applications'} />
      </>
    );
  }

  if (!loading && !oauthApplications?.length) {
    return (
      <Empty
        title="This organization doesn't have any OAuth applications defined."
        icon={KeyIcon}
        body="The OAuth Applications panel allows organizations to define custom OAuth applications that can be used by internal or external customers to access Quay Container Registry data on behalf of the customers. More information about the Quay Container Registry API can be found by contacting support."
        button={
          <Button
            onClick={() =>
              props.setDrawerContent(
                OrganizationDrawerContentType.CreateOAuthApplicationDrawer,
              )
            }
          >
            Create new application
          </Button>
        }
      />
    );
  }

  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <ErrorModal
          title="Default permission deletion failed"
          error={err}
          setError={setError}
        />
        <OAuthApplicationsToolbar
          selectedItems={selectedOAuthApplications}
          deSelectAll={() => setSelectedOAuthApplications([])}
          allItems={filteredOAuthApplications}
          paginatedItems={paginatedOAuthApplications}
          onItemSelect={onSelectPermission}
          page={page}
          setPage={setPage}
          perPage={perPage}
          setPerPage={setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[oauthApplicationColumnName.name]}
          setDrawerContent={props.setDrawerContent}
          handleBulkDeleteModalToggle={handleBulkDeleteModalToggle}
        >
          <Conditional if={bulkDeleteModalIsOpen}>
            <BulkDeleteModalTemplate
              mapOfColNamesToTableData={mapOfColNamesToTableData}
              handleModalToggle={handleBulkDeleteModalToggle}
              handleBulkDeletion={bulkDeleteOAuthApplications}
              isModalOpen={bulkDeleteModalIsOpen}
              selectedItems={oauthApplications?.filter((perm) =>
                selectedOAuthApplications.some(
                  (selected) => perm.name === selected.name,
                ),
              )}
              resourceName={'OAuth Applications'}
            />
          </Conditional>
          <Table
            aria-label="Selectable table"
            data-testid="default-permissions-table"
            variant="compact"
          >
            <Thead>
              <Tr>
                <Th />
                <Th>{oauthApplicationColumnName.name}</Th>
                <Th>{oauthApplicationColumnName.application_uri}</Th>
                <Th />
              </Tr>
            </Thead>
            <Tbody>
              {paginatedOAuthApplications?.map((oauthApplication, rowIndex) => (
                <Tr key={rowIndex}>
                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectPermission(
                          oauthApplication,
                          rowIndex,
                          isSelecting,
                        ),
                      isSelected: selectedOAuthApplications.some(
                        (p) => p.name === oauthApplication.name,
                      ),
                    }}
                  />
                  <Td dataLabel={oauthApplicationColumnName.name}>
                    {oauthApplication.name}
                  </Td>
                  <Td dataLabel={oauthApplicationColumnName.application_uri}>
                    {oauthApplication.application_uri}
                  </Td>
                  <Td data-label="kebab">
                    <DeleteOAuthApplicationKebab
                      orgName={props.orgName}
                      oauthApplication={oauthApplication}
                    />
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </OAuthApplicationsToolbar>
      </PageSection>
    </>
  );
}

interface OAuthApplicationsListProps {
  setDrawerContent: (any) => void;
  orgName: string;
}
