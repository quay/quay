import {useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import ErrorModal from 'src/components/errors/ErrorModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import DeleteModalForRowTemplate from 'src/components/modals/DeleteModalForRowTemplate';
import Conditional from 'src/components/empty/Conditional';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import { ISuperuserOrgs, useDeleteOrg, useFetchSuperuserOrgs } from 'src/hooks/UseSuperuserOrgs';
import { SuperuserOrgsToolBar } from './SuperuserOrgsToolBar';
import SuperuserOrgsKebab from './SuperuserOrgsKebab';

export const superuserOrgsColumnNames = {
  name: 'Name',
};

function SuperuserOrgsListHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Organizations</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function SuperuserOrgsList(props: SuperuserOrgsListProps) {
  const [err, setErr] = useState<string[]>();
  const [selectedOrgs, setSelectedOrgs] = useState<ISuperuserOrgs[]>([]);

  const [isDeleteModalForRowOpen, setIsDeleteModalForRowOpen] = useState(false);
  const [orgToBeDeleted, setOrgToBeDeleted] = useState<ISuperuserOrgs>();
  const {addAlert} = useAlerts();

  const {
    orgs,
    paginatedOrgs,
    filteredOrgs,
    isLoadingOrgs,
    errorLoadingOrgs,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchSuperuserOrgs();

  const {removeOrg} = useDeleteOrg({
    onSuccess: () => {
      setIsDeleteModalForRowOpen(false);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted organization: ${orgToBeDeleted.name}`,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to delete user: ${orgToBeDeleted.name}, ${err}`,
      });
    },
  });

  const onSelectOrg = (
    org: ISuperuserOrgs,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedOrgs((prevSelected) => {
      const otherSelectedOrgs = prevSelected.filter(
        (o) => o.name !== org.name,
      );
      return isSelecting ? [...otherSelectedOrgs, org] : otherSelectedOrgs;
    });
  };

  const deleteUserRowModal = (
    <DeleteModalForRowTemplate
      deleteMsgTitle={'Remove Organization'}
      isModalOpen={isDeleteModalForRowOpen}
      toggleModal={() => setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen)}
      deleteHandler={removeOrg}
      itemToBeDeleted={orgToBeDeleted}
      keyToDisplay="name"
    />
  );

  if (isLoadingOrgs) {
    return <Spinner />;
  }

  return (
    <>
      <SuperuserOrgsListHeader />
      <ErrorModal title="Organization deletion failed" error={err} setError={setErr} />
      <PageSection variant={PageSectionVariants.light}>
        <SuperuserOrgsToolBar
          selectedOrgs={selectedOrgs}
          deSelectAll={() => setSelectedOrgs([])}
          allItems={filteredOrgs}
          paginatedItems={paginatedOrgs}
          onItemSelect={onSelectOrg}
          search={search}
          setSearch={setSearch}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
        />
        <Conditional if={isDeleteModalForRowOpen}>
          {deleteUserRowModal}
        </Conditional>
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th>{superuserOrgsColumnNames.name}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedOrgs?.map((org, rowIndex) => (
              <Tr key={org.name}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectOrg(org, rowIndex, isSelecting),
                    isSelected: selectedOrgs.some(
                      (o) => o.name === org.name,
                    ),
                  }}
                />
                <Td
                  dataLabel={superuserOrgsColumnNames.name}
                  data-testid={`organization-${org.name}`}
                >
                  {org.name}
                </Td>
                <Td data-label="kebab">
                  <SuperuserOrgsKebab
                    org={org}
                    deSelectAll={() => setSelectedOrgs([])}
                    onDeleteTeam={() => {
                      setOrgToBeDeleted(org);
                      setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen);
                    }}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredOrgs}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            bottom={true}
          />
        </PanelFooter>
      </PageSection>
    </>
  );
}

interface SuperuserOrgsListProps {}
