import React, {useState} from 'react';
import {DatePicker, TimePicker} from '@patternfly/react-core';
import PropTypes from 'prop-types';

export default function DateTimePicker(props) {
  const {id, value, setValue, futureDatesOnly, initialDate} = props;
  const userLocale = navigator.language;
  const date = value ?? initialDate;
  const [inputValue, setInputValue] = useState(
    value ? date.toLocaleDateString(userLocale) : '',
  );
  function onDateChange(_event, userInput, dateValue) {
    setInputValue(userInput);

    if (dateValue && !isNaN(dateValue.getTime())) {
      setValue((prev) => {
        const updated = new Date(dateValue);
        if (prev) {
          updated.setHours(prev.getHours());
          updated.setMinutes(prev.getMinutes());
        }
        return updated;
      });
    }
  }

  function onTimeChange(_event, _time, hour, minute, _seconds, isValid) {
    if (hour !== null && minute !== null && isValid) {
      const updated = new Date(value || initialDate || new Date());
      updated.setHours(hour);
      updated.setMinutes(minute);
      setValue(updated);
    }
  }
  function rangeValidator(date) {
    if (futureDatesOnly) {
      const now = new Date();
      now.setHours(0, 0, 0, 0);
      return date < now ? 'Date is before the allowable range.' : '';
    }
    return '';
  }

  function getFormattedTime(date) {
    return date
      ? `${date.getHours().toString().padStart(2, '0')}:${date
          .getMinutes()
          .toString()
          .padStart(2, '0')}`
      : '';
  }
  return (
    <span id={id || 'date-time-picker'}>
      <DatePicker
        value={inputValue}
        onChange={onDateChange}
        validators={[rangeValidator]}
      />
      <TimePicker
        placeholder="Select time"
        time={getFormattedTime(date)}
        onChange={onTimeChange}
        is24Hour
      />
    </span>
  );
}

DateTimePicker.propTypes = {
  id: PropTypes.string,
  value: PropTypes.instanceOf(Date),
  setValue: PropTypes.func.isRequired,
  futureDatesOnly: PropTypes.bool,
  initialDate: PropTypes.instanceOf(Date),
};
