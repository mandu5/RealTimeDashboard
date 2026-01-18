import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Badge } from "@/app/components/ui/badge";
import { useState, useMemo } from "react";

interface DataPoint {
  timestamp: string;
  pps?: number;
  jitter?: number;
}

interface TimeSeriesChartProps {
  title: string;
  data: DataPoint[];
  showPps?: boolean;
  showJitter?: boolean;
  p95?: number;
  p99?: number;
  rangeOptions?: Array<{ label: string; seconds: number }>;
}

export function TimeSeriesChart({ 
  title, 
  data, 
  showPps = true,
  showJitter = true,
  p95, 
  p99, 
  rangeOptions = [
    { label: "30s", seconds: 30 },
    { label: "1m", seconds: 60 },
    { label: "5m", seconds: 300 },
  ] 
}: TimeSeriesChartProps) {
  const [selectedRange, setSelectedRange] = useState(rangeOptions[1].label);

  // Filter data based on selected range
  const filteredData = useMemo(() => {
    const range = rangeOptions.find(r => r.label === selectedRange);
    if (!range) return data;
    
    // Get the last N data points based on the range
    const pointsToShow = range.seconds; // Assuming 1 data point per second
    return data.slice(-pointsToShow);
  }, [data, selectedRange, rangeOptions]);

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{title}</CardTitle>
          <div className="flex items-center gap-3">
            {showPps && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-xs text-gray-600">PPS (좌)</span>
              </div>
            )}
            {showJitter && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                <span className="text-xs text-gray-600">지터 (우)</span>
              </div>
            )}
            <div className="flex gap-2 ml-4">
              {rangeOptions.map((range) => (
                <Badge
                  key={range.label}
                  variant={selectedRange === range.label ? "default" : "outline"}
                  className="cursor-pointer text-xs"
                  onClick={() => setSelectedRange(range.label)}
                >
                  {range.label}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
              interval="preserveStartEnd"
            />
            {showPps && (
              <YAxis
                yAxisId="left"
                label={{ value: "PPS", angle: -90, position: "insideLeft", style: { fontSize: 11 } }}
                tick={{ fontSize: 11 }}
                stroke="#3b82f6"
              />
            )}
            {showJitter && (
              <YAxis
                yAxisId="right"
                orientation="right"
                label={{ value: "ms", angle: 90, position: "insideRight", style: { fontSize: 11 } }}
                tick={{ fontSize: 11 }}
                stroke="#a855f7"
              />
            )}
            <Tooltip
              contentStyle={{ fontSize: 12, backgroundColor: "#fff", border: "1px solid #e5e7eb" }}
              labelStyle={{ fontWeight: "bold" }}
            />
            {showPps && <Line yAxisId="left" type="monotone" dataKey="pps" stroke="#3b82f6" strokeWidth={2} dot={false} name="PPS" />}
            {showJitter && <Line yAxisId="right" type="monotone" dataKey="jitter" stroke="#a855f7" strokeWidth={2} strokeDasharray="5 5" dot={false} name="지터 (ms)" />}
          </LineChart>
        </ResponsiveContainer>
        {(p95 || p99) && (
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
            {p95 && (
              <div className="flex items-center gap-2">
                <span>PPS: {filteredData[filteredData.length - 1]?.pps?.toLocaleString() || 0}</span>
              </div>
            )}
            {p99 && (
              <div className="flex items-center gap-2">
                <span>지터: {filteredData[filteredData.length - 1]?.jitter?.toFixed(1) || 0} ms</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}