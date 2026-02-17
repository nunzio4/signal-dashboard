import type { DashboardResponse } from "../../types";
import { ThesisPanel } from "./ThesisPanel";

interface DashboardGridProps {
  data: DashboardResponse;
}

export function DashboardGrid({ data }: DashboardGridProps) {
  return (
    <div className="dashboard-grid">
      {data.theses.map((thesis) => (
        <ThesisPanel key={thesis.thesis_id} thesis={thesis} />
      ))}
    </div>
  );
}
