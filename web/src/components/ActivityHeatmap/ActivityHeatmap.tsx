import {useState, useMemo} from 'react';
import './ActivityHeatmap.css';

export interface ActivityData {
  date: string; // ISO date string
  count: number;
}

interface ActivityHeatmapProps {
  data: ActivityData[];
  itemName?: string;
}

interface DayCell {
  date: Date;
  count: number;
  weekIndex: number;
  dayOfWeek: number;
}

export default function ActivityHeatmap(props: ActivityHeatmapProps) {
  const {data = [], itemName = 'action'} = props;
  const [hoveredCell, setHoveredCell] = useState<DayCell | null>(null);
  const [mousePosition, setMousePosition] = useState({x: 0, y: 0});

  const cellSize = 10;
  const cellMargin = 2;
  const labelOffset = 30;

  // Process data into a map for quick lookup
  const dataMap = useMemo(() => {
    const map = new Map<string, number>();
    data.forEach((item) => {
      const date = new Date(item.date);
      const key = date.toISOString().split('T')[0]; // 'YYYY-MM-DD'
      map.set(key, item.count);
    });
    return map;
  }, [data]);

  // Calculate max count for color scaling
  const maxCount = useMemo(() => {
    return Math.max(...data.map((d) => d.count), 1);
  }, [data]);

  // Get color based on count
  const getColor = (count: number): string => {
    if (count === 0) return 'var(--pf-t--global--color--grey--50, #f4f4f4)';

    const intensity = count / maxCount;
    if (intensity <= 0.25)
      return 'var(--pf-t--global--color--blue--200, #c9e9fb)';
    if (intensity <= 0.5)
      return 'var(--pf-t--global--color--blue--300, #7ec9e8)';
    if (intensity <= 0.75)
      return 'var(--pf-t--global--color--blue--400, #4ba9d6)';
    return 'var(--pf-t--global--color--blue--500, #4682b4)';
  };

  // Generate continuous calendar data for the last 3 months
  const {calendarData, monthLabels, numWeeks} = useMemo(() => {
    const cells: DayCell[] = [];
    const monthLabels: {month: string; weekIndex: number}[] = [];
    const today = new Date();

    // Start from 90 days ago
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - 89);

    // Find the Sunday before the start date to align weeks
    const dayOfWeek = startDate.getDay();
    const alignedStartDate = new Date(startDate);
    alignedStartDate.setDate(alignedStartDate.getDate() - dayOfWeek);

    // Calculate number of weeks needed
    const endDate = new Date(today);
    const daysSinceStart = Math.ceil(
      (endDate.getTime() - alignedStartDate.getTime()) / (1000 * 60 * 60 * 24),
    );
    const weeks = Math.ceil(daysSinceStart / 7);

    let currentMonth = -1;

    // Generate cells for each day in the range
    for (let week = 0; week < weeks; week++) {
      for (let day = 0; day < 7; day++) {
        const currentDate = new Date(alignedStartDate);
        currentDate.setDate(alignedStartDate.getDate() + week * 7 + day);

        // Only include cells within our actual date range
        if (currentDate >= startDate && currentDate <= endDate) {
          const key = currentDate.toISOString().split('T')[0]; // 'YYYY-MM-DD'
          const count = dataMap.get(key) || 0;

          // Track month changes for labels
          if (currentDate.getMonth() !== currentMonth && day === 0) {
            currentMonth = currentDate.getMonth();
            monthLabels.push({
              month: currentDate.toLocaleDateString('en-US', {month: 'short'}),
              weekIndex: week,
            });
          }

          cells.push({
            date: currentDate,
            count,
            weekIndex: week,
            dayOfWeek: day,
          });
        }
      }
    }

    return {calendarData: cells, monthLabels, numWeeks: weeks};
  }, [dataMap]);

  const handleMouseEnter = (cell: DayCell, event: React.MouseEvent) => {
    setHoveredCell(cell);
    setMousePosition({
      x: event.clientX,
      y: event.clientY,
    });
  };

  const handleMouseLeave = () => {
    setHoveredCell(null);
  };

  const formatDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Calculate total dimensions
  const totalWidth = numWeeks * (cellSize + cellMargin) + labelOffset;
  const totalHeight = 7 * (cellSize + cellMargin) + 20;

  return (
    <div className="activity-heatmap">
      <svg
        className="activity-heatmap-svg"
        viewBox={`0 0 ${totalWidth} ${totalHeight}`}
        preserveAspectRatio="none"
      >
        {/* Month labels */}
        {(() => {
          // Filter month labels to avoid crowding - keep months that are at least 3 weeks apart
          const filteredLabels = [];
          let lastShownIndex = -1;

          for (let i = 0; i < monthLabels.length; i++) {
            if (lastShownIndex === -1) {
              // First label - check if we should skip it for the next one
              if (
                i + 1 < monthLabels.length &&
                monthLabels[i + 1].weekIndex - monthLabels[i].weekIndex < 3
              ) {
                // Skip this one, prefer the next month which likely has more weeks
                continue;
              }
              filteredLabels.push(monthLabels[i]);
              lastShownIndex = i;
            } else if (
              monthLabels[i].weekIndex -
                monthLabels[lastShownIndex].weekIndex >=
              3
            ) {
              filteredLabels.push(monthLabels[i]);
              lastShownIndex = i;
            }
          }

          return filteredLabels.map((label, index) => (
            <text
              key={index}
              x={labelOffset + label.weekIndex * (cellSize + cellMargin)}
              y={12}
              className="activity-heatmap-month-label"
              fontSize="7"
            >
              {label.month}
            </text>
          ));
        })()}

        {/* Day of week labels */}
        {['Mon', 'Wed', 'Fri'].map((day, index) => (
          <text
            key={day}
            x={20}
            y={20 + (index * 2 + 1) * (cellSize + cellMargin) + cellSize / 2}
            className="activity-heatmap-day-label"
            fontSize="7"
            textAnchor="end"
            dominantBaseline="middle"
          >
            {day}
          </text>
        ))}

        {/* Heatmap cells */}
        <g transform={`translate(${labelOffset}, 20)`}>
          {calendarData.map((cell, index) => {
            const x = cell.weekIndex * (cellSize + cellMargin);
            const y = cell.dayOfWeek * (cellSize + cellMargin);

            return (
              <rect
                key={index}
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                fill={getColor(cell.count)}
                stroke="var(--pf-t--global--color--grey--200)"
                strokeWidth="0.5"
                rx="2"
                className="activity-heatmap-cell"
                onMouseEnter={(e) => handleMouseEnter(cell, e)}
                onMouseLeave={handleMouseLeave}
                role="img"
                aria-label={`${formatDate(cell.date)}: ${
                  cell.count
                } ${itemName}${cell.count !== 1 ? 's' : ''}`}
              />
            );
          })}
        </g>
      </svg>

      {/* Tooltip */}
      {hoveredCell && (
        <div
          className="activity-heatmap-tooltip"
          style={{
            position: 'fixed',
            left: mousePosition.x + 10,
            top: mousePosition.y + 10,
            pointerEvents: 'none',
          }}
        >
          <div className="tooltip-content">
            <div className="tooltip-date">{formatDate(hoveredCell.date)}</div>
            <div className="tooltip-count">
              {hoveredCell.count} {itemName}
              {hoveredCell.count !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
