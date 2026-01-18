import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";

interface AvailabilitySegment {
  start: number;
  end: number;
  status: "up" | "down";
}

interface AvailabilityTimelineProps {
  segments: AvailabilitySegment[];
  duration: number; // in seconds
}

export function AvailabilityTimeline({ segments, duration }: AvailabilityTimelineProps) {
  // Generate time labels in reverse (0m, -10m, -20m, -30m)
  const timeLabels = [];
  const intervalMinutes = Math.ceil(duration / 60 / 4); // Show about 4-5 labels
  for (let i = 0; i >= -duration / 60; i -= intervalMinutes) {
    timeLabels.push(i);
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-sm">가용성 타임라인 (1시간)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="relative h-8 bg-gray-100 rounded overflow-hidden">
            {segments.map((segment, idx) => {
              const left = (segment.start / duration) * 100;
              const width = ((segment.end - segment.start) / duration) * 100;
              return (
                <div
                  key={idx}
                  className={`absolute h-full ${segment.status === "up" ? "bg-green-500" : "bg-red-500"} group cursor-pointer`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={`${segment.status.toUpperCase()}: ${segment.start}s - ${segment.end}s (${segment.end - segment.start}s)`}
                >
                  <span className="hidden group-hover:block absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                    {segment.status.toUpperCase()}: {Math.floor(segment.start / 60)}m - {Math.floor(segment.end / 60)}m
                  </span>
                </div>
              );
            })}
          </div>
          
          {/* Time axis (reverse order) */}
          <div className="relative h-6">
            <div className="absolute left-0 right-0 flex justify-between">
              {timeLabels.map((time, idx) => (
                <div
                  key={idx}
                  className="flex flex-col items-center"
                >
                  <div className="w-px h-2 bg-gray-400"></div>
                  <div className="text-xs text-gray-500 mt-1">{time}m</div>
                </div>
              ))}
              <div className="flex flex-col items-center">
                <div className="w-px h-2 bg-gray-400"></div>
                <div className="text-xs text-gray-500 mt-1">0m</div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}