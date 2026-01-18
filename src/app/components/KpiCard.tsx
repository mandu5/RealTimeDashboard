import { Card, CardContent } from "@/app/components/ui/card";

interface KpiCardProps {
  title: string;
  value: number | string;
  unit?: string;
  showProgress?: boolean;
  progressColor?: "blue" | "green" | "gray";
  progressValue?: number;
}

export function KpiCard({ title, value, unit, showProgress, progressColor = "blue", progressValue = 0 }: KpiCardProps) {
  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    gray: "bg-gray-300",
  };

  return (
    <Card className="shadow-sm">
      <CardContent className="pt-4 pb-3">
        <div className="text-xs text-gray-500 mb-2">{title}</div>
        <div className="flex items-baseline gap-1">
          <div className="text-2xl font-semibold">{value.toLocaleString()}</div>
          {unit && <div className="text-sm text-gray-400">{unit}</div>}
        </div>
        {showProgress && (
          <div className="mt-3 h-1 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${colorClasses[progressColor]} transition-all duration-300`}
              style={{ width: `${Math.min(100, progressValue)}%` }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}