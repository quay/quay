import {UsersIcon, UserIcon, CogIcon} from '@patternfly/react-icons';
import Conditional from './empty/Conditional';
import LinkOrPlainText from './LinkOrPlainText';
import {EntityKind} from 'src/resources/UserResource';

export default function Entity(props: EntityProps) {
  switch (props.type) {
    case EntityKind.team:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <UsersIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>Team</Conditional>{' '}
          <Conditional if={props.name != null}>
            <LinkOrPlainText
              href={
                props.includeLink
                  ? `/organization/${props.namespace}/teams/${props.name}`
                  : null
              }
            >
              {props.name}
            </LinkOrPlainText>
          </Conditional>
        </>
      );
    case EntityKind.robot:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <CogIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>Robot</Conditional>{' '}
          <Conditional if={props.name != null}>{props.name}</Conditional>
        </>
      );
    case EntityKind.user:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <UserIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>User</Conditional>{' '}
          <Conditional if={props.name != null}>
            <LinkOrPlainText
              href={props.includeLink ? `/user/${props.name}` : null}
            >
              {props.name}
            </LinkOrPlainText>
          </Conditional>
        </>
      );
    case EntityKind.organization:
      return (
        <>
          <Conditional
            if={props.includeIcon != null ? props.includeIcon : true}
          >
            <UserIcon />
          </Conditional>{' '}
          <Conditional if={props.includeText}>Organization</Conditional>{' '}
          <Conditional if={props.name != null}>
            <LinkOrPlainText
              href={props.includeLink ? `/organization/${props.name}` : null}
            >
              {props.name}
            </LinkOrPlainText>
          </Conditional>
        </>
      );
  }
}

interface EntityProps {
  type: EntityKind;
  namespace?: string;
  name?: string;
  includeIcon?: boolean;
  includeText?: boolean;
  includeLink?: boolean;
}
