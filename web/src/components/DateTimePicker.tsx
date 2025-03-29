import React, {useState} from 'react';
import {DatePicker, TimePicker} from '@patternfly/react-core';
import {isNullOrUndefined} from 'src/libs/utils';
import PropTypes from 'prop-types';

export default function DateTimePicker(props) {
  const {id, value, setValue, futureDatesOnly, initialDate} = props;
  const [inputValue, setInputValue] = useState(value ? dateFormat(value) : '');

  const date = isNullOrUndefined(value) ? initialDate : value;

  function dateFormat(date) {
    if (!isNullOrUndefined(date)) {
      return date
        .toLocaleDateString('en-GB', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        })
        .replace(/ /g, ' ');
    }
    return '';
  }

  function dateParse(value) {
    const parts = value.trim().split(' ');
    if (parts.length < 2 || parts.length > 3) return null; // Allow partial input

    const [day, month, year = new Date().getFullYear()] = parts;
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    const monthIndex = months.indexOf(month);
    if (monthIndex === -1 || isNaN(day) || (year && isNaN(year))) return null;

    return new Date(parseInt(year, 10), monthIndex, parseInt(day, 10));
  }

  function onDateChange(_event, userInput, dateValue) {
    setInputValue(userInput); // Preserve user's input while typing

    if (dateValue && !isNaN(dateValue.getTime())) {
      setValue(dateValue); // Set only valid dates
    }
  }

  function onTimeChange(_event, _time, hour, minute, _seconds, isValid) {
    if (hour !== null && minute !== null && isValid) {
      setValue((prevDate) => {
        const newDate = new Date(prevDate || new Date());
        newDate.setHours(hour);
        newDate.setMinutes(minute);
        return newDate;
      });
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

  return (
    <>
      <span id={isNullOrUndefined(id) ? 'date-time-picker' : id}>
        <DatePicker
          placeholder="DD MMM YYYY"
          value={inputValue}
          dateFormat={dateFormat}
          dateParse={dateParse}
          onChange={onDateChange}
          validators={[rangeValidator]}
          style={{width: '20ch', paddingRight: '10px'}}
        />
        <TimePicker
          placeholder="No time selected"
          time={isNullOrUndefined(date) ? ' ' : date.toLocaleTimeString()}
          onChange={onTimeChange}
        />
      </span>
    </>
  );
}
DateTimePicker.propTypes = {
  id: PropTypes.string,
  value: PropTypes.instanceOf(Date),
  setValue: PropTypes.func.isRequired,
  futureDatesOnly: PropTypes.bool,
  initialDate: PropTypes.instanceOf(Date),
};
