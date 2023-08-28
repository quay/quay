import {DatePicker, TimePicker} from '@patternfly/react-core';
import {isNullOrUndefined} from 'src/libs/utils';

export default function DateTimePicker(props: DateTimePickerProps) {
  const {id, value, setValue, futureDatesOnly, initialDate} = props;
  const date: Date = isNullOrUndefined(value) ? initialDate : value;

  const dateFormat = (date: Date) => {
    if (!isNullOrUndefined(date)) {
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }
  };

  const onDateChange = (value: string, dateValue: Date) => {
    if (!isNullOrUndefined(dateValue)) {
      if (isNullOrUndefined(date)) {
        setValue((prevDate) => dateValue);
      } else {
        setValue((prevDate) => {
          const newDate = new Date(prevDate);
          newDate.setFullYear(dateValue.getFullYear());
          newDate.setMonth(dateValue.getMonth());
          newDate.setDate(dateValue.getDate());
          return newDate;
        });
      }
    } else {
      setValue(null);
    }
  };

  const onTimeChange = (time, hour, minute, seconds, isValid) => {
    if (hour !== null && minute !== null && isValid) {
      if (isNullOrUndefined(date)) {
        const newDate = new Date();
        newDate.setHours(hour);
        newDate.setMinutes(minute);
        setValue((prevDate) => newDate);
      } else {
        setValue((prevDate) => {
          const newDate = new Date(prevDate);
          newDate.setHours(hour);
          newDate.setMinutes(minute);
          return newDate;
        });
      }
    } else {
      setValue(null);
    }
  };

  const rangeValidator = (date: Date) => {
    if (futureDatesOnly) {
      const now = new Date();
      now.setHours(0);
      now.setMinutes(0);
      return date < now ? 'Date is before the allowable range.' : '';
    }
    return '';
  };

  return (
    <>
      <span id={isNullOrUndefined(id) ? 'date-time-picker' : id}>
        <DatePicker
          placeholder="No date selected"
          value={dateFormat(date)}
          dateFormat={dateFormat}
          onChange={onDateChange}
          validators={[rangeValidator]}
          style={{width: '20ch'}}
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

interface DateTimePickerProps {
  initialDate?: Date;
  value: Date;
  setValue: (set: (prev: Date) => Date) => void;
  futureDatesOnly?: boolean;
  id?: string;
}
