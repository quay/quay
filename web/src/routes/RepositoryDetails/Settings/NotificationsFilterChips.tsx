import {ToolbarFilter} from '@patternfly/react-core';
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
        labels={props.filter.event}
        deleteLabel={(_category, chip) => deleteFilter('event', chip as string)}
        deleteLabelGroup={() => props.resetFilter('event')}
        categoryName="Event"
      >
        {}
      </ToolbarFilter>
      <ToolbarFilter
        labels={props.filter.status}
        deleteLabel={(_category, chip) =>
          deleteFilter('status', chip as string)
        }
        deleteLabelGroup={() => props.resetFilter('status')}
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
