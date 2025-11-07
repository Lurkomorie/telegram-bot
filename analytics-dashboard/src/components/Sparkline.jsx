export default function Sparkline({ data, width = 70, height = 24 }) {
  if (!data || data.length === 0) {
    return <div style={{ width, height }} />;
  }

  const maxValue = Math.max(...data, 1); // At least 1 to avoid division by zero
  const barWidth = width / data.length;
  const gap = 1;

  return (
    <svg width={width} height={height} className="inline-block">
      {data.map((value, index) => {
        const barHeight = value > 0 ? Math.max((value / maxValue) * height, 2) : 3;
        const x = index * barWidth;
        const y = height - barHeight;
        const color = value > 0 ? '#3b82f6' : '#ef4444'; // blue or red
        const barActualWidth = barWidth - gap;

        return (
          <rect
            key={index}
            x={x}
            y={y}
            width={barActualWidth}
            height={barHeight}
            fill={color}
            opacity={value > 0 ? 0.8 : 0.5}
          />
        );
      })}
    </svg>
  );
}

