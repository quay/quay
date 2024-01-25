import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function RegistryName(props: RegistryNameProps) {
  const config = useQuayConfig();
  return (
    <span>
      {props.short
        ? config.config.REGISTRY_TITLE_SHORT
        : config.config.REGISTRY_TITLE}
    </span>
  );
}

interface RegistryNameProps {
  short?: boolean;
}
