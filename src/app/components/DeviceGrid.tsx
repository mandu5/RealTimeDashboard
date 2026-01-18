import { Badge } from "@/app/components/ui/badge";

interface DeviceStatus {
  name: string;
  connected: boolean;
  warning?: boolean;
}

interface DeviceGridProps {
  devices: DeviceStatus[];
}

export function DeviceGrid({ devices }: DeviceGridProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      {devices.map((device) => (
        <div key={device.name} className="flex flex-col items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              device.connected ? (device.warning ? "bg-orange-500" : "bg-green-500") : "bg-gray-300"
            }`}
          ></div>
          <div className="text-xs font-medium text-center">{device.name}</div>
        </div>
      ))}
    </div>
  );
}