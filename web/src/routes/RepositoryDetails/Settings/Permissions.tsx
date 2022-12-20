import {Spinner} from '@patternfly/react-core';
import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {useState} from 'react';
import {useRepositoryPermissions} from 'src/hooks/UseRepositoryPermissions';
import PermissionsToolbar from './PermissionsToolbar';
import ColumnNames from './ColumnNames';
import PermissionsDropdown from './PermissionsDropdown';
import {RepoMember} from 'src/resources/RepositoryResource';
import PermissionsKebab from './PermissionsKebab';
import {DrawerContentType} from '../Types';

export default function Permissions(props: PermissionsProps) {
  const {
    members,
    paginatedMembers,
    loading,
    error,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useRepositoryPermissions(props.org, props.repo);
  const [selectedMembers, setSelectedMembers] = useState<RepoMember[]>([]);

  const onSelectMember = (
    member: RepoMember,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedMembers((prevSelected) => {
      const others = prevSelected.filter((r) => r.name !== member.name);
      return isSelecting ? [...others, member] : others;
    });
  };

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <>Unable to load permissions list</>;
  }

  return (
    <>
      <PermissionsToolbar
        org={props.org}
        repo={props.repo}
        allItems={members}
        paginatedItems={paginatedMembers}
        selectedItems={selectedMembers}
        page={page}
        setPage={setPage}
        perPage={perPage}
        setPerPage={setPerPage}
        searchOptions={[ColumnNames.account]}
        search={search}
        setSearch={setSearch}
        onItemSelect={onSelectMember}
        deselectAll={() => setSelectedMembers([])}
        setDrawerContent={props.setDrawerContent}
      />
      <TableComposable aria-label="Repository permissions table">
        <Thead>
          <Tr>
            <Th />
            <Th>{ColumnNames.account}</Th>
            <Th>{ColumnNames.type}</Th>
            <Th>{ColumnNames.permissions}</Th>
            <Th />
          </Tr>
        </Thead>
        <Tbody>
          {paginatedMembers?.map((member, rowIndex) => (
            <Tr key={member.name}>
              <Td
                select={{
                  rowIndex,
                  onSelect: (e, isSelecting) =>
                    onSelectMember(member, rowIndex, isSelecting),
                  isSelected: selectedMembers.some(
                    (r) => r.name === member.name,
                  ),
                }}
              />
              <Td data-label="membername">{member.name}</Td>
              <Td data-label="type">{member.type}</Td>
              <Td data-label="role">
                <PermissionsDropdown member={member} />
              </Td>
              <Td data-label="kebab">
                <PermissionsKebab member={member} />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </TableComposable>
    </>
  );
}

interface PermissionsProps {
  org: string;
  repo: string;
  setDrawerContent: (content: DrawerContentType) => void;
}
