import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Button,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {
  IOAuthApplication,
  useBulkDeleteOAuthApplications,
  useFetchOAuthApplications,
} from 'src/hooks/UseOAuthApplications';
import CreateOAuthApplicationModal from './CreateOAuthApplicationModal';
import OAuthApplicationActionsKebab from './OAuthApplicationActionsKebab';
import OAuthApplicationsToolbar from './OAuthApplicationsToolbar';
import ManageOAuthApplicationDrawer from './ManageOAuthApplicationDrawer';
import Conditional from 'src/components/empty/Conditional';
import {BulkOperationError, addDisplayError} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import ErrorModal from 'src/components/errors/ErrorModal';
import Empty from 'src/components/empty/Empty';
import {KeyIcon} from '@patternfly/react-icons';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';

export const oauthApplicationColumnName = {
  name: 'Application Name',
  application_uri: 'Application URI',
};

export default function OAuthApplicationsList(
  props: OAuthApplicationsListProps,
) {
  const [createModalIsOpen, setCreateModalIsOpen] = useState<boolean>(false);
  const [bulkDeleteModalIsOpen, setBulkDeleteModalIsOpen] =
    useState<boolean>(false);
  const [manageDrawerIsOpen, setManageDrawerIsOpen] = useState<boolean>(false);
  const [selectedApplication, setSelectedApplication] =
    useState<IOAuthApplication | null>(null);
  const [selectedOAuthApplications, setSelectedOAuthApplications] = useState<
    IOAuthApplication[]
  >([]);
  const [error, setError] = useState<string[]>([]);
  const {addAlert} = useAlerts();

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

  const {bulkDeleteOAuthApplications} = useBulkDeleteOAuthApplications({
    orgName: props.orgName,
    onSuccess: () => {
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedOAuthApplications([]);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted OAuth applications`,
      });
    },
    onError: (err) => {
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        err.getErrors().forEach((error, perm) => {
          addAlert({
            variant: AlertVariant.Failure,
            title: `Could not delete OAuth application ${perm}: ${error.error}`,
          });
          errMessages.push(
            addDisplayError(
              `Failed to delete OAuth application: ${perm}`,
              error.error,
            ),
          );
        });
        setError(errMessages);
      } else {
        setError([addDisplayError('Failed to delete OAuth application', err)]);
      }
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedOAuthApplications([]);
    },
  });

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

  const handleBulkDeleteModalToggle = () => {
    setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
  };

  const handleManageDrawerToggle = () => {
    setManageDrawerIsOpen(!manageDrawerIsOpen);
    if (manageDrawerIsOpen) {
      setSelectedApplication(null); // Clear selection when closing
    }
  };

  const openManageApplication = (application: IOAuthApplication) => {
    setSelectedApplication(application);
    setManageDrawerIsOpen(true);
  };

  const mapOfColNamesToTableData: {
    [key: string]: {
      label: string;
      transformFunc: (oauthApplication: IOAuthApplication) => React.ReactNode;
    };
  } = {
    Name: {
      label: 'name',
      transformFunc: (oauthApplication: IOAuthApplication) => {
        return (
          <Button
            variant="link"
            isInline
            onClick={() => openManageApplication(oauthApplication)}
          >
            {oauthApplication.name}
          </Button>
        );
      },
    },
    ApplicationURI: {
      label: 'application_uri',
      transformFunc: (oauthApplication: IOAuthApplication) => {
        return `${oauthApplication.application_uri}`;
      },
    },
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
          <Button onClick={() => setCreateModalIsOpen(true)}>
            Create new application
          </Button>
        }
      />
    );
  }

  return (
    <>
      <CreateOAuthApplicationModal
        isModalOpen={createModalIsOpen}
        handleModalToggle={() => setCreateModalIsOpen(!createModalIsOpen)}
        orgName={props.orgName}
      />
      {manageDrawerIsOpen ? (
        <ManageOAuthApplicationDrawer
          isDrawerOpen={manageDrawerIsOpen}
          handleDrawerToggle={handleManageDrawerToggle}
          application={selectedApplication}
          orgName={props.orgName}
        >
          <PageSection variant={PageSectionVariants.light}>
            {error && error.length > 0 && (
              <ErrorModal
                title="OAuth application operation failed"
                error={error}
                setError={setError}
              />
            )}
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
              handleCreateModalToggle={() =>
                setCreateModalIsOpen(!createModalIsOpen)
              }
              handleBulkDeleteModalToggle={handleBulkDeleteModalToggle}
            />
            <Conditional if={oauthApplications?.length === 0}>
              <Empty
                title="No OAuth applications exist"
                icon={KeyIcon}
                body="Create an OAuth application for your organization by clicking the button above."
              />
            </Conditional>
            <Conditional if={oauthApplications && oauthApplications.length > 0}>
              <Table
                aria-label="OAuth Applications table"
                data-testid="oauth-applications-table"
                variant="compact"
                style={{tableLayout: 'fixed', width: '100%'}}
              >
                <Thead>
                  <Tr>
                    <Th style={{width: '5%'}} />
                    <Th style={{width: '30%'}}>Application Name</Th>
                    <Th style={{width: '35%'}}>Application URI</Th>
                    <Th style={{width: '10%'}} />
                    <Th style={{width: '20%'}} />
                  </Tr>
                </Thead>
                <Tbody>
                  {paginatedOAuthApplications?.map(
                    (oauthApplication, rowIndex) => (
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
                            isDisabled: false,
                          }}
                        />
                        <Td dataLabel={oauthApplicationColumnName.name}>
                          {mapOfColNamesToTableData.Name.transformFunc(
                            oauthApplication,
                          )}
                        </Td>
                        <Td
                          dataLabel={oauthApplicationColumnName.application_uri}
                        >
                          {mapOfColNamesToTableData.ApplicationURI.transformFunc(
                            oauthApplication,
                          )}
                        </Td>
                        <Td isActionCell>
                          <OAuthApplicationActionsKebab
                            orgName={props.orgName}
                            oauthApplication={oauthApplication}
                            onEdit={() =>
                              openManageApplication(oauthApplication)
                            }
                          />
                        </Td>
                        <Td />
                      </Tr>
                    ),
                  )}
                </Tbody>
              </Table>
              <ToolbarPagination
                itemsList={filteredOAuthApplications}
                perPage={perPage}
                page={page}
                setPage={setPage}
                setPerPage={setPerPage}
                bottom={true}
              />
            </Conditional>
          </PageSection>
        </ManageOAuthApplicationDrawer>
      ) : (
        <PageSection variant={PageSectionVariants.light}>
          {error && error.length > 0 && (
            <ErrorModal
              title="OAuth application operation failed"
              error={error}
              setError={setError}
            />
          )}
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
            handleCreateModalToggle={() =>
              setCreateModalIsOpen(!createModalIsOpen)
            }
            handleBulkDeleteModalToggle={handleBulkDeleteModalToggle}
          />
          <Conditional if={oauthApplications?.length === 0}>
            <Empty
              title="No OAuth applications exist"
              icon={KeyIcon}
              body="Create an OAuth application for your organization by clicking the button above."
            />
          </Conditional>
          <Conditional if={oauthApplications && oauthApplications.length > 0}>
            <Table
              aria-label="OAuth Applications table"
              data-testid="oauth-applications-table"
              variant="compact"
              style={{tableLayout: 'fixed', width: '100%'}}
            >
              <Thead>
                <Tr>
                  <Th style={{width: '5%'}} />
                  <Th style={{width: '30%'}}>Application Name</Th>
                  <Th style={{width: '35%'}}>Application URI</Th>
                  <Th style={{width: '10%'}} />
                  <Th style={{width: '20%'}} />
                </Tr>
              </Thead>
              <Tbody>
                {paginatedOAuthApplications?.map(
                  (oauthApplication, rowIndex) => (
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
                          isDisabled: false,
                        }}
                      />
                      <Td dataLabel={oauthApplicationColumnName.name}>
                        {mapOfColNamesToTableData.Name.transformFunc(
                          oauthApplication,
                        )}
                      </Td>
                      <Td
                        dataLabel={oauthApplicationColumnName.application_uri}
                      >
                        {mapOfColNamesToTableData.ApplicationURI.transformFunc(
                          oauthApplication,
                        )}
                      </Td>
                      <Td isActionCell>
                        <OAuthApplicationActionsKebab
                          orgName={props.orgName}
                          oauthApplication={oauthApplication}
                          onEdit={() => openManageApplication(oauthApplication)}
                        />
                      </Td>
                      <Td />
                    </Tr>
                  ),
                )}
              </Tbody>
            </Table>
            <ToolbarPagination
              itemsList={filteredOAuthApplications}
              perPage={perPage}
              page={page}
              setPage={setPage}
              setPerPage={setPerPage}
              bottom={true}
            />
          </Conditional>
        </PageSection>
      )}
      <BulkDeleteModalTemplate
        handleModalToggle={() =>
          setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen)
        }
        isModalOpen={bulkDeleteModalIsOpen}
        selectedItems={selectedOAuthApplications}
        resourceName={'OAuth application'}
        handleBulkDeletion={bulkDeleteOAuthApplications}
        mapOfColNamesToTableData={mapOfColNamesToTableData}
      />
    </>
  );
}

interface OAuthApplicationsListProps {
  orgName: string;
}
