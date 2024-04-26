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
  Split,
  SplitItem,
  TimePicker,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useSetExpiration} from 'src/hooks/UseTags';
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
  const [validDate, setValidDate] = useState<boolean>(true);
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
      return date.toLocaleDateString(navigator.language, {
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
      } else {
        setValidDate(true);
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
        setDate(newDate);
      } else {
        setValidDate(false);
      }
    } else {
      setValidDate(false);
    }
  };

  const rangeValidator = (date: Date) => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return date < now ? 'Cannot set expiration date to the past.' : '';
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
  };

  const is24HourFormat = () => {
    const dateString = new Date().toLocaleTimeString();
    const lastTwoCharacters = dateString.slice(-2);
    return lastTwoCharacters !== 'AM' && lastTwoCharacters !== 'PM';
  };

  const minExpirationDateTime = () => {
    if (date !== null && isToday(date)) {
      return new Date(); // now
    } else {
      const newDate = new Date();
      newDate.setHours(0, 0, 0);
      return newDate;
    }
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
              <Split hasGutter style={{height: '4em'}}>
                <SplitItem>
                  <DatePicker
                    placeholder="No date selected"
                    value={dateFormat(date)}
                    dateFormat={dateFormat}
                    dateParse={(date: string) => new Date(date)}
                    onChange={onDateChange}
                    validators={[rangeValidator]}
                  />
                </SplitItem>
                <SplitItem>
                  <TimePicker
                    id="expiration-time-picker"
                    placeholder="No time selected"
                    time={
                      date === null || !validDate
                        ? ' '
                        : date.toLocaleTimeString()
                    }
                    onChange={onTimeChange}
                    is24Hour={is24HourFormat()}
                    minTime={minExpirationDateTime()}
                    invalidMinMaxErrorMessage="Cannot set expiration date to the past."
                    style={{width: '150px', whiteSpace: 'normal'}}
                  />
                </SplitItem>
                <SplitItem>
                  <Button variant={ButtonVariant.secondary} onClick={onClear}>
                    Clear
                  </Button>
                </SplitItem>
              </Split>
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
