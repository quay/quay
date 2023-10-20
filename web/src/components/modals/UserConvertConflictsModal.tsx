import {
  Button,
  Modal,
  ModalVariant,
  PageSection,
  PageSectionVariants,
  TextInput,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {IOrganization} from 'src/resources/OrganizationResource';

export const UserConvertConflictsModal = (
  props: UserConvertConflictsModal,
): JSX.Element => {
  const [itemsMarkedForDelete, setItemsMarkedForDelete] = useState<
    IOrganization[]
  >(props.items);

  const [searchInput, setSearchInput] = useState<string>('');

  const [bulkModalPerPage, setBulkModalPerPage] = useState<number>(10);
  const [bulkModalPage, setBulkModalPage] = useState<number>(1);

  const paginatedBulkItemsList = itemsMarkedForDelete.slice(
    bulkModalPage * bulkModalPerPage - bulkModalPerPage,
    bulkModalPage * bulkModalPerPage - bulkModalPerPage + bulkModalPerPage,
  );

  const onSearch = (value: string) => {
    setSearchInput(value);
    if (value === '') {
      setItemsMarkedForDelete(props.items);
    } else {
      /* Note: This search filter assumes that the search is always based on the 1st column,
         hence we do "colNames[0]" */
      const filteredTableRow = props.items.filter(
        (item) => item.name?.toLowerCase().includes(value.toLowerCase()),
      );
      setItemsMarkedForDelete(filteredTableRow);
    }
  };

  return (
    <Modal
      title={`Change account type`}
      id="bulk-delete-modal"
      titleIconVariant="warning"
      aria-label={`Change account type`}
      variant={ModalVariant.medium}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          key="cancel"
          id="delete-org-cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Close
        </Button>,
      ]}
    >
      <span>
        This account cannot be converted into an organization, as it is a member
        of another organization. Please leave the following organization(s)
        first:
      </span>
      <PageSection variant={PageSectionVariants.light}>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem>
              <TextInput
                isRequired
                type="search"
                id="modal-with-form-form-name"
                name="search input"
                placeholder="Search"
                value={searchInput}
                onChange={(_, val) => onSearch(val)}
              />
            </ToolbarItem>
            <ToolbarPagination
              page={bulkModalPage}
              perPage={bulkModalPerPage}
              itemsList={props.items}
              setPage={setBulkModalPage}
              setPerPage={setBulkModalPerPage}
            />
          </ToolbarContent>
        </Toolbar>
        <Table aria-label="Simple table" variant="compact">
          <Thead>
            <Tr>
              <Th>Organization</Th>
              <Th>Role</Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedBulkItemsList.map((item, idx) => (
              <Tr key={idx}>
                <Td>{item.name}</Td>
                <Td>{item.is_org_admin ? 'Admin' : 'User'}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <Toolbar>
          <ToolbarPagination
            page={bulkModalPage}
            perPage={bulkModalPerPage}
            itemsList={props.items}
            setPage={setBulkModalPage}
            setPerPage={setBulkModalPerPage}
            bottom={true}
          />
        </Toolbar>
      </PageSection>
    </Modal>
  );
};

type UserConvertConflictsModal = {
  mapOfColNamesToTableData: {
    [key: string]: {label?: string; transformFunc?: (value) => any};
  };
  isModalOpen: boolean;
  handleModalToggle?: () => void;
  items: IOrganization[];
};
