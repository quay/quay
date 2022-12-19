// Renders conditional components in a more markup friendly way
export default function Conditional(props: ConditionalProps) {
  return props.if ? <>{props.children}</> : null;
}

interface ConditionalProps {
  children: React.ReactNode;
  if: boolean;
}
