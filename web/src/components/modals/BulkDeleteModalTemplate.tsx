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
  SearchInput,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useEffect, useState} from 'react';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';

export const BulkDeleteModalTemplate = <T,>(
  props: BulkDeleteModalTemplateProps<T>,
): JSX.Element => {
  const [itemsMarkedForDelete, setItemsMarkedForDelete] = useState<T[]>(
    props.selectedItems,
  );

  const colNames = Object.keys(props.mapOfColNamesToTableData);

  const [confirmDeletionInput, setConfirmDeletionInput] = useState<string>('');

  const [searchInput, setSearchInput] = useState<string>('');

  const [bulkModalPerPage, setBulkModalPerPage] = useState<number>(20);
  const [bulkModalPage, setBulkModalPage] = useState<number>(1);

  const paginatedBulkItemsList = itemsMarkedForDelete.slice(
    bulkModalPage * bulkModalPerPage - bulkModalPerPage,
    bulkModalPage * bulkModalPerPage - bulkModalPerPage + bulkModalPerPage,
  );

  const onSearch = (
    _event: React.FormEvent<HTMLInputElement>,
    value: string,
  ) => {
    setSearchInput(value);
    if (value === '') {
      setItemsMarkedForDelete(props.selectedItems);
    } else {
      /* Note: This search filter assumes that the search is always based on the 1st column,
         hence we do "colNames[0]" */
      const filteredTableRow = props.selectedItems.filter(
        (item) =>
          item[props.mapOfColNamesToTableData[colNames[0]].label]
            ?.toLowerCase()
            .includes(value.toLowerCase()),
      );
      setItemsMarkedForDelete(filteredTableRow);
    }
  };

  const bulkDelete = async () => {
    if (confirmDeletionInput === 'confirm') {
      await props.handleBulkDeletion(props.selectedItems);
    }
  };

  useEffect(() => {
    setItemsMarkedForDelete(props.selectedItems);
  }, []);

  /* Function that transforms a given cell value with the transformation function if present
  else returns the default cell value */
  const applyTransformFuncIfGiven = (item, name) =>
    props.mapOfColNamesToTableData[name].transformFunc
      ? props.mapOfColNamesToTableData[name].transformFunc(item)
      : item[props.mapOfColNamesToTableData[name].label];

  return (
    <Modal
      title={`Permanently delete ${props.resourceName}?`}
      id="bulk-delete-modal"
      titleIconVariant="warning"
      aria-label={`Permanently delete ${props.resourceName}?`}
      variant={ModalVariant.medium}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      actions={[
        <Button
          key="delete"
          variant="danger"
          onClick={bulkDelete}
          form="modal-with-form-form"
          isDisabled={confirmDeletionInput !== 'confirm'}
          data-testid="bulk-delete-confirm-btn"
        >
          Delete
        </Button>,
        <Button
          key="cancel"
          id="delete-org-cancel"
          variant="link"
          onClick={props.handleModalToggle}
        >
          Cancel
        </Button>,
      ]}
    >
      <span>
        This action deletes all {props.resourceName} and cannot be recovered.
      </span>
      <PageSection variant={PageSectionVariants.light}>
        <Toolbar>
          <ToolbarContent className="pf-v5-u-pl-0">
            <ToolbarItem>
              <SearchInput
                type="search"
                id="modal-with-form-form-name"
                name="search input"
                placeholder="Search"
                value={searchInput}
                onChange={onSearch}
              />
            </ToolbarItem>
            <ToolbarPagination
              page={bulkModalPage}
              perPage={bulkModalPerPage}
              itemsList={itemsMarkedForDelete}
              setPage={setBulkModalPage}
              setPerPage={setBulkModalPerPage}
              className="pf-v5-u-mr-md"
            />
          </ToolbarContent>
        </Toolbar>
        <Table aria-label="Simple table" variant="compact">
          <Thead>
            <Tr>
              {colNames.map((name, idx) => (
                <Th key={idx}>{name}</Th>
              ))}
            </Tr>
          </Thead>
          <Tbody>
            {paginatedBulkItemsList.map((item, idx) => (
              <Tr key={idx}>
                {colNames.map((name, index) => (
                  <Td
                    key={index}
                    dataLabel={item[props.mapOfColNamesToTableData[name].label]}
                  >
                    {applyTransformFuncIfGiven(item, name)}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
        <Toolbar>
          <ToolbarPagination
            page={bulkModalPage}
            perPage={bulkModalPerPage}
            itemsList={itemsMarkedForDelete}
            setPage={setBulkModalPage}
            setPerPage={setBulkModalPerPage}
          />
        </Toolbar>
        <p className="pf-v5-u-pt-md">
          Confirm deletion by typing <b>&quot;confirm&quot;</b> below:
        </p>
        <TextInput
          id="delete-confirmation-input"
          value={confirmDeletionInput}
          type="text"
          onChange={(_event, value) => setConfirmDeletionInput(value)}
          aria-label="text input example"
        />
      </PageSection>
    </Modal>
  );
};

type BulkDeleteModalTemplateProps<T> = {
  mapOfColNamesToTableData: {
    [key: string]: {label?: string; transformFunc?: (value) => any};
  };
  isModalOpen: boolean;
  handleModalToggle?: () => void;
  handleBulkDeletion: (items: T[]) => void;
  selectedItems: T[];
  resourceName: string;
};
