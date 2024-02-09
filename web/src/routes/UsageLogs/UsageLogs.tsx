import React from 'react';
import {DatePicker, Split, SplitItem} from '@patternfly/react-core';
import ExportLogsModal from './UsageLogsExportModal';
import './css/UsageLogs.scss';

interface UsageLogsProps {
  organization: string;
  repository: string;
  type: string;
}

function defaultStartDate() {
  // should be 1 month before current date
  const currentDate = new Date();
  currentDate.setMonth(currentDate.getMonth() - 1);

  const year = currentDate.getFullYear();
  const month = (currentDate.getMonth() + 1).toString().padStart(2, '0');
  const day = currentDate.getDate().toString().padStart(2, '0');
  const formattedDate = `${year}-${month}-${day}`;

  return formattedDate;
}

function defaultEndDate() {
  // should be current date
  const date = new Date();

  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = (date.getDate() + 1).toString().padStart(2, '0');
  const formattedDate = `${year}-${month}-${day}`;

  return formattedDate;
}

function formatDate(date: string) {
  /**
   * change date string from y-m-d to m%d%y for api
   */
  const dates = date.split('-');
  const year = dates[0];
  const month = dates[1];
  const day = dates[2];

  return `${month}/${day}/${year}`;
}

export default function UsageLogs(props: UsageLogsProps) {
  const [logStartDate, setLogStartDate] = React.useState<string>(
    formatDate(defaultStartDate()),
  );
  const [logEndDate, setLogEndDate] = React.useState<string>(
    formatDate(defaultEndDate()),
  );
  const minDate = new Date(defaultStartDate());
  const maxDate = new Date(defaultEndDate());
  const rangeValidator = (date: Date) => {
    if (date < minDate) {
      return 'Date is before the allowable range';
    } else if (date > maxDate) {
      return 'Date is after the allowable range';
    }
    return '';
  };

  return (
    <Split hasGutter className="usage-logs-header">
      <SplitItem isFilled></SplitItem>
      <SplitItem>
        <DatePicker
          value={logStartDate}
          onChange={(_event, str, date) => {
            setLogStartDate(formatDate(str));
          }}
          validators={[rangeValidator]}
        />
      </SplitItem>
      <SplitItem>
        <DatePicker
          value={logEndDate}
          onChange={(_event, str, date) => {
            setLogEndDate(formatDate(str));
          }}
          validators={[rangeValidator]}
        />
      </SplitItem>
      <SplitItem>
        <ExportLogsModal
          organization={props.organization}
          repository={props.repository}
          starttime={logStartDate}
          endtime={logEndDate}
          type={props.type}
        />
      </SplitItem>
    </Split>
  );
}
