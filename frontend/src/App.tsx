import { useState } from "react";
import { useDashboardData, useRefreshAll } from "./hooks/useDashboard";
import { AppShell } from "./components/layout/AppShell";
import { Header } from "./components/layout/Header";
import { DashboardGrid } from "./components/dashboard/DashboardGrid";
import { ManualSignalForm } from "./components/signals/ManualSignalForm";
import { FeedManager } from "./components/feeds/FeedManager";

type Tab = "dashboard" | "feeds";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const { data, isLoading, isError, error, refetch } =
    useDashboardData(30);
  const refreshAll = useRefreshAll();

  const handleRefresh = () => {
    refreshAll.mutate(undefined, {
      onSettled: () => refetch(),
    });
  };

  return (
    <AppShell>
      <Header
        lastIngestion={data?.last_ingestion ?? null}
        lastDataFetch={data?.last_data_fetch ?? null}
        totalArticles={data?.total_articles ?? 0}
        totalSignals={data?.total_signals ?? 0}
        articles24h={data?.articles_24h ?? 0}
        signals24h={data?.signals_24h ?? 0}
        onRefresh={handleRefresh}
        isRefreshing={refreshAll.isPending}
      />

      <nav className="tab-bar">
        <button
          className={`tab-btn ${activeTab === "dashboard" ? "tab-btn--active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          <span className="tab-icon">◈</span> Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === "feeds" ? "tab-btn--active" : ""}`}
          onClick={() => setActiveTab("feeds")}
        >
          <span className="tab-icon">⊞</span> News Feeds
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
      </main>
    </AppShell>
  );
}

export default App;
