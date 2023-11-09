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
import Conditional from 'src/components/empty/Conditional';

export default function EditExpirationModal(props: EditExpirationModalProps) {
  const [date, setDate] = useState<Date>(null);
  const {addAlert} = useAlerts();
  const {
    setExpiration,
    successSetExpiration,
    errorSetExpiration,
    errorSetExpirationDetails,
  } = useSetExpiration(props.org, props.repo);
  const [validDate, setValidDate] = useState<boolean>(true);
  const [timePickerError, setTimePickerError] = useState<string>(null);
  const initialDate: Date = isNullOrUndefined(props.expiration)
    ? null
    : new Date(props.expiration);

  const isToday = (date: Date) => {
    const today = new Date();
    return (
      date.getFullYear() == today.getFullYear() &&
      date.getMonth() == today.getMonth() &&
      date.getDate() == today.getDate()
    );
  };

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

  const onDateChange = (
    _event: React.FormEvent<HTMLInputElement>,
    _value: string,
    dateValue?: Date,
  ) => {
    const isInputInvalid = dateValue !== null && dateValue === undefined;
    if (!isInputInvalid) {
      const newDate = isNullOrUndefined(date) ? new Date() : new Date(date);
      newDate.setFullYear(dateValue.getFullYear());
      newDate.setMonth(dateValue.getMonth());
      newDate.setDate(dateValue.getDate());
      if (isNullOrUndefined(date) && isToday(newDate)) {
        newDate.setHours(newDate.getHours() + 1);
      } else if (isNullOrUndefined(date)) {
        newDate.setHours(0, 0, 0, 0);
      }
      setDate(newDate);
      if (newDate <= new Date()) {
        setValidDate(false);
        setTimePickerError('Time is before the allowable range.');
      } else {
        setValidDate(true);
        setTimePickerError(null);
      }
    } else {
      setValidDate(false);
    }
  };

  const onTimeChange = (
    _event: React.FormEvent<HTMLInputElement>,
    _time: string,
    hour?: number,
    minute?: number,
    _seconds?: number,
    isValid?: boolean,
  ) => {
    const isInputValid = hour !== null && minute !== null && isValid;
    if (isInputValid) {
      const newDate = isNullOrUndefined(date) ? new Date() : new Date(date);
      newDate.setHours(hour, minute);
      if (newDate > new Date()) {
        setValidDate(true);
        setTimePickerError(null);
        setDate(newDate);
      } else {
        setValidDate(false);
        setTimePickerError('Time is before the allowable range.');
      }
    } else {
      setValidDate(false);
    }
  };

  const rangeValidator = (date: Date) => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
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

  const onClear = () => {
    setDate(null);
    setValidDate(true);
    setTimePickerError(null);
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
          <Button
            key="modal-action-button"
            variant="primary"
            isDisabled={!validDate}
            onClick={onSave}
          >
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
                dateParse={(date: string) => new Date(date)}
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
              <Button variant={ButtonVariant.secondary} onClick={onClear}>
                Clear
              </Button>
              <Conditional
                if={timePickerError !== null && timePickerError.length > 0}
              >
                <div style={{color: 'red'}}>{timePickerError}</div>
              </Conditional>
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
