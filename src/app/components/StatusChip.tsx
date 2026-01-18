import { Badge } from "@/app/components/ui/badge";

interface StatusChipProps {
  label: string;
  value: string | number;
  variant?: "default" | "success" | "warning" | "destructive";
}

export function StatusChip({ label, value, variant = "default" }: StatusChipProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case "success":
        return "bg-emerald-50 border-emerald-200 text-emerald-700";
      case "warning":
        return "bg-amber-50 border-amber-200 text-amber-700";
      case "destructive":
        return "bg-red-50 border-red-200 text-red-700";
      default:
        return "bg-slate-50 border-slate-200 text-slate-700";
    }
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${getVariantStyles()}`}>
      <span className="text-xs font-medium opacity-70">{label}</span>
      <span className="text-xs font-semibold">{value}</span>
    </div>
  );
}