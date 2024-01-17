import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {ReactNode, useState} from 'react';
import './RegexMatchView.css';

export interface RegexMatchItem {
  icon: ReactNode;
  title: string;
  value: string;
}

export default function RegexMatchView(props: RegexMatchViewProps) {
  const {regex, items} = props;
  let invalid = false;

  try {
    const regexp = new RegExp(regex);
  } catch (ex) {
    invalid = true;
  }

  if (invalid) {
    return (
      <div style={{color: 'red'}}>
        <ExclamationTriangleIcon /> Invalid Regular Expression!
      </div>
    );
  }

  const filterMatches = (shouldMatch: boolean) => {
    return items.filter((item) => {
      const value: string = item.value;
      const m: RegExpMatchArray = value.match(regex);
      const matches = !!(m && m[0].length == value.length);
      return matches == shouldMatch;
    });
  };

  const matches = filterMatches(true);
  const notMatches = filterMatches(false);

  return (
    <div className="regex-match-view-element">
      <table className="match-table">
        <tr>
          <td>Matching:</td>
          <td>
            <ul className="match-list matching">
              {matches.map((item) => (
                <li key={item.title}>
                  {item.icon} {item.title}
                </li>
              ))}
            </ul>
          </td>
        </tr>
        <tr>
          <td>Not Matching:</td>
          <td>
            <ul className="match-list not-matching">
              {notMatches.map((item) => (
                <li key={item.title}>
                  {item.icon} {item.title}
                </li>
              ))}
            </ul>
          </td>
        </tr>
      </table>
    </div>
  );
}

interface RegexMatchViewProps {
  regex: string;
  items: RegexMatchItem[];
}
