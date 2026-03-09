import React from 'react';
import {
  InputGroup,
  InputGroupItem,
  DatePicker,
  TimePicker,
} from '@patternfly/react-core';
import {
  parseDateTimeValue,
  dateFormat,
  dateParse,
  formatTimeForPicker,
  is24HourFormat,
  toFormString,
} from 'src/libs/dateTimeUtils';

interface FormDateTimePickerProps {
  value: string;
  onChange: (val: string) => void;
  dateAriaLabel?: string;
  timeAriaLabel?: string;
}

export const FormDateTimePicker: React.FC<FormDateTimePickerProps> = ({
  value,
  onChange,
  dateAriaLabel = 'Select date',
  timeAriaLabel = 'Select time',
}) => {
  const current = parseDateTimeValue(value);

  const onDateChange = (
    _event: React.FormEvent<HTMLInputElement>,
    _value: string,
    dateValue?: Date,
  ) => {
    if (!dateValue || isNaN(dateValue.getTime())) return;
    const newDate = current ? new Date(current) : new Date();
    // Set day to 1 first to avoid JS date rollover when changing months
    newDate.setDate(1);
    newDate.setFullYear(dateValue.getFullYear());
    newDate.setMonth(dateValue.getMonth());
    newDate.setDate(dateValue.getDate());
    if (!current) {
      newDate.setHours(0, 0, 0, 0);
    }
    onChange(toFormString(newDate));
  };

  const onTimeChange = (
    _event: React.FormEvent<HTMLInputElement>,
    _time: string,
    hour?: number,
    minute?: number,
    _seconds?: number,
    isValid?: boolean,
  ) => {
    if (hour == null || minute == null || !isValid || !current) return;
    const newDate = new Date(current);
    newDate.setHours(hour, minute);
    onChange(toFormString(newDate));
  };

  return (
    <InputGroup>
      <InputGroupItem>
        <DatePicker
          value={current ? dateFormat(current) : ''}
          dateFormat={dateFormat}
          dateParse={dateParse}
          onChange={onDateChange}
          aria-label={dateAriaLabel}
        />
      </InputGroupItem>
      <InputGroupItem>
        <TimePicker
          time={formatTimeForPicker(current)}
          onChange={onTimeChange}
          is24Hour={is24HourFormat()}
          stepMinutes={1}
          aria-label={timeAriaLabel}
          style={{width: '150px'}}
        />
      </InputGroupItem>
    </InputGroup>
  );
};
