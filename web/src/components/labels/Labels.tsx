import ReadOnlyLabels from './LabelsReadOnly';
import EditableLabels from './LabelsEditable';
import {Label} from 'src/resources/TagResource';

export enum LabelsVariant {
  ReadOnly = 'readonly',
  Editable = 'editable',
}

export default function Labels(props: LabelsProps) {
  const variant = props.variant ? props.variant : LabelsVariant.ReadOnly;
  if (variant === LabelsVariant.ReadOnly) {
    return <ReadOnlyLabels {...props} />;
  } else if (variant === LabelsVariant.Editable) {
    return <EditableLabels {...props} />;
  }
}

interface LabelsProps {
  org: string;
  repo: string;
  digest: string;
  variant?: LabelsVariant;
  onComplete?: () => void;
  cache?: Record<string, Label[]>;
  setCache?: (cache: Record<string, Label[]>) => void;
}
