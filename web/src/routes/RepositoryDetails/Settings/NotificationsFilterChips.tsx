import {Toolbar, ToolbarFilter} from '@patternfly/react-core';
import {NotificationFilter} from 'src/hooks/UseNotifications';

export default function NotificationsFilterChips(
  props: NotificationsFilterChipsProps,
) {
  const deleteFilter = (category: string, chip: string) => {
    props.setFilter((prev) => {
      const others = prev[category].filter((e) => e != chip);
      return {
        ...prev,
        [category]: others,
      };
    });
  };

  return (
    <>
      <ToolbarFilter
        chips={props.filter.event}
        deleteChip={(category, chip) => deleteFilter('event', chip as string)}
        deleteChipGroup={() => props.resetFilter('event')}
        categoryName="Event"
      >
        {}
      </ToolbarFilter>
      <ToolbarFilter
        chips={props.filter.status}
        deleteChip={(category, chip) => deleteFilter('status', chip as string)}
        deleteChipGroup={() => props.resetFilter('status')}
        categoryName="Status"
      >
        {}
      </ToolbarFilter>
    </>
  );
}

interface NotificationsFilterChipsProps {
  filter: NotificationFilter;
  setFilter(set: (prev: NotificationFilter) => NotificationFilter): void;
  resetFilter(field?: string): void;
}
