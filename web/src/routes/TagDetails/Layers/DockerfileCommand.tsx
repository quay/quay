import React from 'react';
import {Label} from '@patternfly/react-core';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

interface DockerfileCommandProps {
  command: string;
}

export function DockerfileCommand(props: DockerfileCommandProps) {
  const {command} = props;
  const quayConfig = useQuayConfig();

  // Color-coded dockerfile commands
  const getCommandColor = (
    instruction: string,
  ): 'blue' | 'cyan' | 'green' | 'orange' | 'purple' | 'red' | 'grey' => {
    const colorMap: {
      [key: string]:
        | 'blue'
        | 'cyan'
        | 'green'
        | 'orange'
        | 'purple'
        | 'red'
        | 'grey';
    } = {
      FROM: 'cyan',
      ARG: 'orange', // yellow not available in PatternFly, using orange
      ONBUILD: 'purple',
      CMD: 'blue',
      EXPOSE: 'blue',
      ENTRYPOINT: 'blue',
      RUN: 'green',
      ADD: 'green',
      COPY: 'green',
      ENV: 'orange',
      VOLUME: 'orange',
      USER: 'orange',
      WORKDIR: 'orange',
      HEALTHCHECK: 'orange',
      STOPSIGNAL: 'orange',
      SHELL: 'orange',
      MAINTAINER: 'grey',
    };
    return colorMap[instruction.toUpperCase()] || 'grey';
  };

  // Split command into instruction and arguments
  const parts = command.trim().split(/\s+/);
  if (parts.length === 0) {
    return <div className="dockerfile-command-element">{command}</div>;
  }

  const instruction = parts[0].toUpperCase();
  const args = parts.slice(1).join(' ');

  // Special handling for FROM commands - create clickable links to base images
  const renderFromCommand = (args: string): React.ReactNode => {
    const argParts = args.split(' ');
    const imageRef = argParts[0];
    const restArgs = argParts.slice(1).join(' ');

    const pieces = imageRef.split('/');
    const registry = pieces.length < 3 ? '' : pieces[0];

    // Registry handlers
    const registryHandlers: {[domain: string]: (pieces: string[]) => string} = {
      'quay.io': (pieces) => {
        const rnamespace = pieces[pieces.length - 2];
        const rname = pieces[pieces.length - 1].split(':')[0];
        return `/repository/${rnamespace}/${rname}/`;
      },
      '': (pieces) => {
        const rnamespace = pieces.length === 1 ? '_' : `u/${pieces[0]}`;
        const rname = pieces[pieces.length - 1].split(':')[0];
        return `https://registry.hub.docker.com/${rnamespace}/${rname}/`;
      },
    };

    // Add current domain handler if available
    if (quayConfig?.config.SERVER_HOSTNAME) {
      registryHandlers[quayConfig.config.SERVER_HOSTNAME] =
        registryHandlers['quay.io'];
    }

    const handler = registryHandlers[registry];
    if (handler) {
      const link = handler(pieces);
      return (
        <>
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="from-image-link"
            aria-label={`View ${imageRef} base image in registry`}
          >
            {imageRef}
          </a>
          {restArgs && ` ${restArgs}`}
        </>
      );
    }

    return args;
  };

  return (
    <div className="dockerfile-command-element">
      <Label
        color={getCommandColor(instruction)}
        className="dockerfile-instruction"
      >
        {instruction}
      </Label>
      <span className="command-title">
        {instruction === 'FROM' ? renderFromCommand(args) : args}
      </span>
    </div>
  );
}
