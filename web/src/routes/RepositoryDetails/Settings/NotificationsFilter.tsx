import {
  MenuContent,
  MenuItem,
  Menu as PFMenu,
  MenuList,
  Checkbox,
} from '@patternfly/react-core';
import {useState} from 'react';
import Menu from 'src/components/Table/Menu';
import {useEvents} from 'src/hooks/UseEvents';
import {
  NotifiationStatus,
  NotificationFilter,
} from 'src/hooks/UseNotifications';
import {NotificationEventType} from 'src/resources/NotificationResource';

export default function NotificationsFilter(props: NotificationsFilterProps) {
  const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
  const {events} = useEvents();

  const selectEvent = (checked: boolean, event: NotificationEventType) => {
    props.setFilter((prev) => {
      const others = prev.event.filter((f) => f !== event);
      prev.event = checked ? [...others, event] : others;
      return {...prev, event: prev.event};
    });
  };

  const selectStatus = (checked: boolean, status: NotifiationStatus) => {
    props.setFilter((prev) => {
      const others = prev.status.filter((f) => f !== status);
      prev.status = checked ? [...others, status] : others;
      return {...prev, status: prev.status};
    });
  };

  return (
    <Menu
      toggle="Filter"
      isOpen={isMenuOpen}
      setIsOpen={setIsMenuOpen}
      items={[
        <MenuItem
          id="filter-events"
          key="filter-events"
          flyoutMenu={
            <PFMenu key={1}>
              <MenuContent>
                <MenuList>
                  {events.map((e) => (
                    <MenuItem key={e.type} style={{width: 'max-content'}}>
                      <Checkbox
                        id={`${e.title}-checkbox`}
                        label={e.title}
                        isChecked={props.filter.event.includes(e.type)}
                        onChange={(checked: boolean) => {
                          selectEvent(checked, e.type);
                        }}
                        name={`${e.title}-checkbox`}
                      />
                    </MenuItem>
                  ))}
                </MenuList>
              </MenuContent>
            </PFMenu>
          }
        >
          Events
        </MenuItem>,
        <MenuItem
          id="filter-status"
          key="filter-events"
          flyoutMenu={
            <PFMenu key={0}>
              <MenuContent>
                <MenuList>
                  <MenuItem
                    key="filter-status-enabled"
                    style={{width: 'max-content'}}
                  >
                    <Checkbox
                      id="enabled-checkbox"
                      label="Enabled"
                      isChecked={props.filter.status.includes(
                        NotifiationStatus.enabled,
                      )}
                      onChange={(checked: boolean) => {
                        selectStatus(checked, NotifiationStatus.enabled);
                      }}
                      name="enabled-checkbox"
                    />
                  </MenuItem>
                  <MenuItem
                    key="filter-status-disabled"
                    style={{width: 'max-content'}}
                  >
                    <Checkbox
                      id="disabled-checkbox"
                      label="Disabled"
                      isChecked={props.filter.status.includes(
                        NotifiationStatus.disabled,
                      )}
                      onChange={(checked: boolean) => {
                        selectStatus(checked, NotifiationStatus.disabled);
                      }}
                      name="disabled-checkbox"
                    />
                  </MenuItem>
                </MenuList>
              </MenuContent>
            </PFMenu>
          }
          itemId="next-menu-root"
        >
          Status
        </MenuItem>,
      ]}
    />
  );
}

interface NotificationsFilterProps {
  filter: NotificationFilter;
  setFilter(set: (prev: NotificationFilter) => NotificationFilter): void;
}
