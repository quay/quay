import React from 'react';
import {Label} from '@patternfly/react-core';

interface DockerfileCommandProps {
  command: string;
}

export function DockerfileCommand(props: DockerfileCommandProps) {
  const {command} = props;

  // Split command into instruction and arguments
  const parts = command.trim().split(/\s+/);
  if (parts.length === 0) {
    return <div className="dockerfile-command-element">{command}</div>;
  }

  const instruction = parts[0].toUpperCase();
  const args = parts.slice(1).join(' ');

  return (
    <div className="dockerfile-command-element">
      <Label color="blue" className="dockerfile-instruction">
        {instruction}
      </Label>
      <span className="command-title">{args}</span>
    </div>
  );
}
