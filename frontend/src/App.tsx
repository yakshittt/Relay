import React, { useState, useEffect } from 'react';
import { fetchHealth } from './api';
import { Navbar } from './components/Navbar';
import { OverviewView } from './views/OverviewView';
import { SiteDetailView } from './views/SiteDetailView';
import { IncidentDetailView } from './views/IncidentDetailView';
import { VoiceConsoleView } from './views/VoiceConsoleView';
import { PlaygroundView } from './views/PlaygroundView';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [selectedSite, setSelectedSite] = useState<string>('jio-lab');
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [demoMode, setDemoMode] = useState<boolean>(true);

  const checkHealth = async () => {
    try {
      const res = await fetchHealth();
      setBackendHealthy(res.ok);
      setDemoMode((res as any).demo_mode ?? true);
    } catch {
      setBackendHealthy(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 8000);
    return () => clearInterval(timer);
  }, []);

  const handleSelectSite = (siteId: string) => {
    setSelectedSite(siteId);
    setActiveTab('site');
  };

  const handleSelectIncident = (incidentId: number) => {
    setSelectedIncidentId(incidentId);
    setActiveTab('incident');
  };

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          if (tab !== 'incident') {
            setSelectedIncidentId(null);
          }
          setActiveTab(tab);
        }}
        backendHealthy={backendHealthy}
        demoMode={demoMode}
      />

      <main className="main-content">
        {activeTab === 'overview' && (
          <OverviewView
            onSelectSite={handleSelectSite}
            onSelectIncident={handleSelectIncident}
            onOpenPlayground={() => setActiveTab('playground')}
          />
        )}

        {activeTab === 'site' && (
          <SiteDetailView
            siteId={selectedSite}
            onBack={() => setActiveTab('overview')}
            onSelectIncident={handleSelectIncident}
          />
        )}

        {activeTab === 'incident' && selectedIncidentId !== null && (
          <IncidentDetailView
            incidentId={selectedIncidentId}
            onBack={() => setActiveTab('overview')}
          />
        )}

        {activeTab === 'voice' && <VoiceConsoleView />}

        {activeTab === 'playground' && <PlaygroundView />}
      </main>
    </div>
  );
};

export default App;
