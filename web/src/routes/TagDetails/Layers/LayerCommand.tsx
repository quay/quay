import React from 'react';
import {DockerfileCommand} from './DockerfileCommand';

interface LayerCommandProps {
  command: string[];
}

export function LayerCommand(props: LayerCommandProps) {
  const {command} = props;

  // Extract Dockerfile command from layer command
  const getDockerfileCommand = (command: string[]): string => {
    if (!command || !command.length) {
      return '';
    }

    // Join and split to normalize the command array
    const normalizedCommand = command.join(' ').split(' ');

    // Format: ["/bin/sh", "-c", "#(nop)", "RUN", "foo"]
    if (normalizedCommand[0] !== '/bin/sh' || normalizedCommand[1] !== '-c') {
      return '';
    }

    if (normalizedCommand[2]?.trim() !== '#(nop)') {
      return 'RUN ' + normalizedCommand.slice(2).join(' ');
    }

    return normalizedCommand.slice(3).join(' ');
  };

  const dockerfileCommand = getDockerfileCommand(command);

  return (
    <div className="image-command-element">
      {dockerfileCommand ? (
        <DockerfileCommand command={dockerfileCommand} />
      ) : (
        <div className="nondocker-command">{command.join(' ')}</div>
      )}
    </div>
  );
}
