import {isNullOrUndefined} from 'src/libs/utils';

export default function LinkOrPlainText(props: LinkOrPlainText) {
  return isNullOrUndefined(props.href) ? (
    <>{props.children}</>
  ) : (
    <a href={props.href}>{props.children}</a>
  );
}

interface LinkOrPlainText {
  children: React.ReactNode;
  href?: string;
}
