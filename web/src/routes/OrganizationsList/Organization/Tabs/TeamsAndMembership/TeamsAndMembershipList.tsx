import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {useState} from 'react';
import TeamsViewList from './TeamsView/TeamsViewList';
import CollaboratorsViewList from './CollaboratorsView/CollaboratorsViewList';
import MembersViewList from './MembersView/MembersViewList';

export enum TableModeType {
  Teams = 'Teams',
  Members = 'Members',
  Collaborators = 'Collaborators',
}

export default function TeamsAndMembershipList(
  props: TeamsAndMembershipListProps,
) {
  const [tableMode, setTableMode] = useState<TableModeType>(
    TableModeType.Teams,
  );

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
    const id = event.currentTarget.id;
    setTableMode(id);
    fetchTableItems();
  };

  const viewToggle = (
    <Toolbar>
      <ToolbarContent>
        <ToolbarItem>
          <ToggleGroup aria-label="Team and membership toggle view">
            <ToggleGroupItem
              text="Team View"
              buttonId={TableModeType.Teams}
              isSelected={tableMode == TableModeType.Teams}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Members View"
              buttonId={TableModeType.Members}
              isSelected={tableMode == TableModeType.Members}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Collaborators View"
              buttonId={TableModeType.Collaborators}
              isSelected={tableMode == TableModeType.Collaborators}
              onChange={onTableModeChange}
            />
          </ToggleGroup>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const fetchTableItems = () => {
    if (tableMode == TableModeType.Teams) {
      return (
        <TeamsViewList organizationName={props.organizationName}>
          {viewToggle}
        </TeamsViewList>
      );
    } else if (tableMode == TableModeType.Members) {
      return (
        <MembersViewList organizationName={props.organizationName}>
          {viewToggle}
        </MembersViewList>
      );
    } else if (tableMode == TableModeType.Collaborators) {
      return (
        <CollaboratorsViewList organizationName={props.organizationName}>
          {viewToggle}
        </CollaboratorsViewList>
      );
    }
  };

  return fetchTableItems();
}

interface TeamsAndMembershipListProps {
  organizationName: string;
}
