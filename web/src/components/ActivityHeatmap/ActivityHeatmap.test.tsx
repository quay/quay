import {render, screen} from 'src/test-utils';
import ActivityHeatmap, {ActivityData} from './ActivityHeatmap';

function makeData(count: number, daysAgo: number): ActivityData {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return {date: d.toISOString(), count};
}

describe('ActivityHeatmap', () => {
  it('renders an SVG element', () => {
    const {container} = render(<ActivityHeatmap data={[]} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('renders day labels (Mon, Wed, Fri)', () => {
    render(<ActivityHeatmap data={[]} />);
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Wed')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();
  });

  it('renders at least one month label', () => {
    render(<ActivityHeatmap data={[]} />);
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    const found = months.some((m) => screen.queryByText(m) !== null);
    expect(found).toBe(true);
  });

  it('renders rect cells for each day in the 90-day window', () => {
    const {container} = render(
      <ActivityHeatmap data={[makeData(5, 10), makeData(3, 20)]} />,
    );
    const rects = container.querySelectorAll('rect');
    // At least 89 cells for the 90-day window
    expect(rects.length).toBeGreaterThanOrEqual(89);
  });

  it('applies different fill colors based on count intensity', () => {
    const {container} = render(
      <ActivityHeatmap data={[makeData(100, 5)]} itemName="action" />,
    );
    // count=100, max=100 → intensity=1.0 > 0.75 → blue-500 (highest tier)
    const cells = container.querySelectorAll('.activity-heatmap-cell');
    const highCountCell = Array.from(cells).find(
      (c) => (c as SVGElement).getAttribute('aria-label')?.includes('100'),
    );
    expect(highCountCell).toBeDefined();
    expect((highCountCell as SVGElement).getAttribute('fill')).toBe(
      'var(--pf-t--global--color--blue--500, #4682b4)',
    );
  });

  it('encodes itemName in cell aria-labels', () => {
    const {container} = render(
      <ActivityHeatmap data={[makeData(3, 2)]} itemName="push" />,
    );
    const cells = container.querySelectorAll('.activity-heatmap-cell');
    const labelledCell = Array.from(cells).find(
      (c) => (c as SVGElement).getAttribute('aria-label')?.includes('push'),
    );
    expect(labelledCell).toBeDefined();
  });

  it('renders with empty data without crashing', () => {
    const {container} = render(<ActivityHeatmap data={[]} />);
    expect(container).toBeInTheDocument();
  });

  it('handles data with a single max-count item without crashing', () => {
    const {container} = render(<ActivityHeatmap data={[makeData(1, 5)]} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});
