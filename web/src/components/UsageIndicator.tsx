import {isNullOrUndefined} from 'src/libs/utils';
import './UsageIndicator.css';

export default function UsageIndicator(props: UsageIndicatorProps) {
  const {value, max, logBase} = props;
  let strengthClass = '';

  if (value !== null && max !== null) {
    const base = isNullOrUndefined(logBase) ? 10 : logBase;
    let val = Math.round((value / max) * 4);
    const currentValue = Math.log(value) / Math.log(base * 1);
    const maximum = Math.log(max) / Math.log(base * 1);
    val = Math.round((currentValue / maximum) * 4);

    switch (true) {
      case val <= 0:
        strengthClass = 'none';
        break;
      case val <= 1:
        strengthClass = 'poor';
        break;
      case val <= 2:
        strengthClass = 'barely';
        break;
      case val <= 3:
        strengthClass = 'fair';
        break;
      default:
        strengthClass = 'good';
    }
  }

  return (
    <span className="strength-indicator">
      <span className={`strength-indicator-element ${strengthClass}`}>
        <span className="indicator-sliver"></span>
        <span className="indicator-sliver"></span>
        <span className="indicator-sliver"></span>
        <span className="indicator-sliver"></span>
      </span>
    </span>
  );
}

interface UsageIndicatorProps {
  value: number;
  max: number;
  logBase?: number;
}
