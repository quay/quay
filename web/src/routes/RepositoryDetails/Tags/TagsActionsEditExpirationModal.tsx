import {
  Button,
  ButtonVariant,
  DatePicker,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Label,
  Modal,
  ModalVariant,
  TimePicker,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useSetExpiration} from 'src/hooks/UseTags';
import {AlertVariant} from 'src/atoms/AlertState';
import {formatDate, isNullOrUndefined} from 'src/libs/utils';

export default function EditExpirationModal(props: EditExpirationModalProps) {
  const [date, setDate] = useState<Date>(null);
  const {addAlert} = useAlerts();
  const {
    setExpiration,
    successSetExpiration,
    errorSetExpiration,
    errorSetExpirationDetails,
  } = useSetExpiration(props.org, props.repo);
  const initialDate: Date = isNullOrUndefined(props.expiration)
    ? null
    : new Date(props.expiration);

  useEffect(() => {
    setDate(initialDate);
  }, [props.expiration]);

  useEffect(() => {
    if (successSetExpiration) {
      const dateMessage: string = isNullOrUndefined(date)
        ? 'never'
        : formatDate(date.getTime() / 1000);
      const title: string =
        props.tags.length === 1
          ? `Successfully set expiration for tag ${props.tags[0]} to ${dateMessage}`
          : `Successfully updated tag expirations to ${dateMessage}`;
      addAlert({variant: AlertVariant.Success, title: title});
      props.loadTags();
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [successSetExpiration]);

  useEffect(() => {
    if (errorSetExpiration) {
      const title: string =
        props.tags.length === 1
          ? `Could not set expiration for tag ${props.tags[0]}`
          : 'Could not update tag expirations';
      const errorDisplayMessage = (
        <>
          {Array.from(errorSetExpirationDetails.getErrors()).map(
            ([tag, error]) => (
              <p key={tag}>
                Could not update expiration for tag {tag}: {error.error.message}
              </p>
            ),
          )}
        </>
      );
      addAlert({
        variant: AlertVariant.Failure,
        title: title,
        message: errorDisplayMessage,
      });
      props.setIsOpen(false);
      if (!isNullOrUndefined(props.onComplete)) {
        props.onComplete();
      }
    }
  }, [errorSetExpiration]);

  const dateFormat = (date: Date) => {
    if (!isNullOrUndefined(date)) {
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }
  };

  const onDateChange = (value: string, dateValue: Date) => {
    if (!isNullOrUndefined(dateValue)) {
      if (isNullOrUndefined(date)) {
        setDate(dateValue);
      } else {
        setDate((prevDate) => {
          const newDate = new Date(prevDate);
          newDate.setFullYear(dateValue.getFullYear());
          newDate.setMonth(dateValue.getMonth());
          newDate.setDate(dateValue.getDate());
          return newDate;
        });
      }
    } else {
      setDate(null);
    }
  };

  const onTimeChange = (time, hour, minute, seconds, isValid) => {
    if (hour !== null && minute !== null && isValid) {
      if (isNullOrUndefined(date)) {
        const newDate = new Date();
        newDate.setHours(hour);
        newDate.setMinutes(minute);
        setDate(newDate);
      } else {
        setDate((prevDate) => {
          const newDate = new Date(prevDate);
          newDate.setHours(hour);
          newDate.setMinutes(minute);
          return newDate;
        });
      }
    } else {
      setDate(null);
    }
  };

  const rangeValidator = (date: Date) => {
    const now = new Date();
    now.setHours(0);
    now.setMinutes(0);
    return date < now ? 'Date is before the allowable range.' : '';
  };

  const onSave = () => {
    const requestedDate =
      date === null || date === undefined ? null : date.getTime() / 1000;
    setExpiration({tags: props.tags, expiration: requestedDate});
  };

  const onClose = () => {
    props.setIsOpen(false);
    setDate(initialDate);
  };

  return (
    <>
      <Modal
        id="edit-expiration-modal"
        title="Change Tags Expiration"
        isOpen={props.isOpen}
        onClose={onClose}
        variant={ModalVariant.medium}
        actions={[
          <Button key="cancel" variant="primary" onClick={onClose}>
            Cancel
          </Button>,
          <Button key="modal-action-button" variant="primary" onClick={onSave}>
            Change Expiration
          </Button>,
        ]}
        style={{
          overflowX: 'visible',
          overflowY: 'visible',
        }}
      >
        <DescriptionList>
          <DescriptionListGroup>
            <DescriptionListTerm>Tags that will be updated</DescriptionListTerm>
            <DescriptionListDescription id="edit-expiration-tags">
              {props.tags.map((tag) => (
                <Label key={tag}>{tag}</Label>
              ))}
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup>
            <DescriptionListTerm>Expiration date</DescriptionListTerm>
            <DescriptionListDescription>
              <DatePicker
                placeholder="No date selected"
                value={dateFormat(date)}
                dateFormat={dateFormat}
                onChange={onDateChange}
                validators={[rangeValidator]}
              />
              <TimePicker
                id="expiration-time-picker"
                placeholder="No time selected"
                time={date === null ? ' ' : date.toLocaleTimeString()}
                onChange={onTimeChange}
              />
              <span style={{paddingRight: '1em'}} />
              <Button
                variant={ButtonVariant.secondary}
                onClick={() => setDate(null)}
              >
                Clear
              </Button>
            </DescriptionListDescription>
          </DescriptionListGroup>
        </DescriptionList>
      </Modal>
    </>
  );
}

interface EditExpirationModalProps {
  org: string;
  repo: string;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  tags: string[];
  loadTags: () => void;
  expiration?: string;
  onComplete?: () => void;
}
