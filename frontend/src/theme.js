// Chart colours for Recharts (SVG attributes can't read CSS variables).
// Kept in sync with styles/variables.css — GL Bajaj maroon & gold palette.
export const CHART = {
  grid: '#eadfc8',
  axis: '#8a6f58',
  line: '#592106',        // maroon fill-level line
  lineArea: '#f0b100',    // gold
  alertBar: '#b91c1c',
  // Normal / Warning / Critical
  status: ['#15803d', '#d97706', '#b91c1c'],
  tooltip: {
    background: '#ffffff',
    border: '1px solid #e8dcc4',
    borderRadius: '8px',
    color: '#2b1608',
    boxShadow: '0 6px 16px rgba(71, 37, 16, 0.12)',
  },
};
