import { useState } from "react";
import { useDashboardData } from "./hooks/useDashboard";
import { AppShell } from "./components/layout/AppShell";
import { Header } from "./components/layout/Header";
import { DashboardGrid } from "./components/dashboard/DashboardGrid";
import { ManualSignalForm } from "./components/signals/ManualSignalForm";
import { FeedManager } from "./components/feeds/FeedManager";
import { DataSeriesManager } from "./components/feeds/DataSeriesManager";

type Tab = "dashboard" | "feeds" | "data-series";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const { data, isLoading, isError, error, refetch } =
    useDashboardData(270);

  return (
    <AppShell>
      <Header
        lastIngestion={data?.last_ingestion ?? null}
        lastDataFetch={data?.last_data_fetch ?? null}
        nextIngestion={data?.next_ingestion ?? null}
        nextDataFetch={data?.next_data_fetch ?? null}
        totalArticles={data?.total_articles ?? 0}
        articles24h={data?.articles_24h ?? 0}
        totalDataPoints={data?.total_data_points ?? 0}
        dataPoints24h={data?.data_points_24h ?? 0}
        totalNewsSignals={data?.total_news_signals ?? 0}
        newsSignals24h={data?.news_signals_24h ?? 0}
        totalDataSignals={data?.total_data_signals ?? 0}
        dataSignals24h={data?.data_signals_24h ?? 0}
      />

      <nav className="tab-bar">
        <button
          className={`tab-btn ${activeTab === "dashboard" ? "tab-btn--active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          <span className="tab-icon">&#9672;</span> Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === "feeds" ? "tab-btn--active" : ""}`}
          onClick={() => setActiveTab("feeds")}
        >
          <span className="tab-icon">&#8862;</span> News Feeds
        </button>
        <button
          className={`tab-btn ${activeTab === "data-series" ? "tab-btn--active" : ""}`}
          onClick={() => setActiveTab("data-series")}
        >
          <span className="tab-icon">&#9636;</span> Data Series
        </button>
      </nav>

      <main className="app-main">
        {activeTab === "dashboard" && (
          <>
            {isLoading && (
              <div className="loading-state">
                <div className="spinner" />
                <p>Loading dashboard data...</p>
              </div>
            )}

            {isError && (
              <div className="error-state">
                <h2>Connection Error</h2>
                <p>
                  Could not reach the backend API. Make sure the FastAPI server is
                  running on <code>http://localhost:8000</code>.
                </p>
                <p className="error-detail">{(error as Error).message}</p>
                <button onClick={() => refetch()} className="btn btn-primary">
                  Retry
                </button>
              </div>
            )}

            {data && (
              <>
                <DashboardGrid data={data} />
                <div className="manual-signal-section">
                  <ManualSignalForm
                    theses={data.theses.map((t) => ({
                      thesis_id: t.thesis_id,
                      thesis_name: t.thesis_name,
                    }))}
                  />
                </div>
              </>
            )}
          </>
        )}

        {activeTab === "feeds" && <FeedManager />}
        {activeTab === "data-series" && <DataSeriesManager />}
      </main>
    </AppShell>
  );
}

export default App;
