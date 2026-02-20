import type { ThesisDashboardData } from "../../types";
import { getThesisAccent } from "../../utils/colors";
import { SignalGauge } from "./SignalGauge";
import { TrendChart } from "./TrendChart";
import { EvidenceList } from "./EvidenceList";
import { DataSeriesPanel } from "./DataSeriesPanel";
import { PredictionMarketPanel } from "./PredictionMarketPanel";

interface ThesisPanelProps {
  thesis: ThesisDashboardData;
}

export function ThesisPanel({ thesis }: ThesisPanelProps) {
  const accent = getThesisAccent(thesis.thesis_id);

  return (
    <section className="thesis-panel" style={{ borderTopColor: accent }}>
      <div className="thesis-panel__header">
        <h2 className="thesis-name" style={{ color: accent }}>
          {thesis.thesis_name}
        </h2>
        <p className="thesis-description">{thesis.thesis_description}</p>
        <div className="thesis-stats">
          <span className="stat">
            <strong>{thesis.news_signals_7d}</strong> News Signals (7d)
          </span>
          <span className="stat">
            <strong>{thesis.news_signals_24h}</strong> News Signals (24h)
          </span>
          <span className="stat">
            <strong>{thesis.data_signals_7d}</strong> Data Signals (7d)
          </span>
          <span className="stat">
            <strong>{thesis.data_signals_24h}</strong> Data Signals (24h)
          </span>
        </div>
      </div>

      <div className="thesis-panel__gauge">
        <SignalGauge
          score={thesis.current_score}
          trend={thesis.score_trend}
          previousScore={thesis.previous_score}
          accent={accent}
        />
      </div>

      <div className="thesis-panel__chart">
        <TrendChart data={thesis.trend_data} accent={accent} />
      </div>

      <div className="thesis-panel__evidence-row">
        <div className="thesis-panel__evidence">
          <EvidenceList signals={thesis.recent_signals} />
        </div>
        <div className="thesis-panel__data-series">
          <DataSeriesPanel thesisId={thesis.thesis_id} accentColor={accent} />
        </div>
        <div className="thesis-panel__prediction-markets">
          <PredictionMarketPanel thesisId={thesis.thesis_id} accentColor={accent} />
        </div>
      </div>
    </section>
  );
}
