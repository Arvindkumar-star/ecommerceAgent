import React, { useState, useEffect, useRef } from 'react';
import FormattedMessage from './FormattedMessage';

// API Base URL (Configurable via environment variable for Vercel/production or relative for local backend)
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [companies, setCompanies] = useState([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [companyModalOpen, setCompanyModalOpen] = useState(false);
  const [tenantDropdownOpen, setTenantDropdownOpen] = useState(false);
  const [newCompanyId, setNewCompanyId] = useState('');
  const [newCompanyName, setNewCompanyName] = useState('');
  const tenantDropdownRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (tenantDropdownRef.current && !tenantDropdownRef.current.contains(e.target)) {
        setTenantDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleDeleteCompany = async (e, companyIdToDelete) => {
    e.stopPropagation();
    if (companies.length <= 1) {
      showToast('Cannot delete the last remaining tenant.', 'error');
      return;
    }
    const compObj = companies.find(c => c.id === companyIdToDelete);
    const compName = compObj ? compObj.name : companyIdToDelete;
    if (!window.confirm(`Are you sure you want to delete workspace '${compName}' and all its documents?`)) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/companies/${companyIdToDelete}`, { method: 'DELETE' });
      if (res.ok) {
        showToast(`Workspace '${compName}' deleted successfully.`, 'success');
        const remaining = companies.filter(c => c.id !== companyIdToDelete);
        setCompanies(remaining);
        if (selectedCompanyId === companyIdToDelete) {
          setSelectedCompanyId(remaining[0].id);
        }
      } else {
        showToast('Failed to delete workspace', 'error');
      }
    } catch (err) {
      showToast(`Error deleting workspace: ${err.message}`, 'error');
    }
  };

  // Global Toast Notification
  const [toast, setToast] = useState(null);
  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch Companies on Mount
  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/companies`);
      const data = await res.json();
      if (data.companies && data.companies.length > 0) {
        setCompanies(data.companies);
        if (!selectedCompanyId) {
          setSelectedCompanyId(data.companies[0].id);
        }
      } else {
        // Create a default company if none exists
        const defaultComp = await fetch(`${API_BASE}/api/companies`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: 'apex_retail', name: 'Apex Retail Inc.' })
        });
        const defaultData = await defaultComp.json();
        if (defaultData.company) {
          setCompanies([defaultData.company]);
          setSelectedCompanyId(defaultData.company.id);
        }
      }
    } catch (err) {
      console.error('Failed to load companies:', err);
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    if (!newCompanyId.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: newCompanyId.trim(), name: newCompanyName.trim() || newCompanyId.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setCompanies((prev) => [...prev, data.company]);
        setSelectedCompanyId(data.company.id);
        setCompanyModalOpen(false);
        setNewCompanyId('');
        setNewCompanyName('');
        showToast(`Company '${data.company.name}' created successfully!`, 'success');
      } else {
        showToast(data.detail || 'Failed to create company', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className="app-layout">
      {/* Toast Alert */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: 20,
          right: 20,
          zIndex: 1000,
          padding: '12px 18px',
          borderRadius: 8,
          background: toast.type === 'error' ? '#f43f5e' : toast.type === 'success' ? '#10b981' : '#6366f1',
          color: 'white',
          fontWeight: 600,
          fontSize: 13,
          boxShadow: '0 8px 20px rgba(0,0,0,0.4)',
          animation: 'fadeIn 0.2s ease-out'
        }}>
          {toast.message}
        </div>
      )}

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div className="brand-info">
            <h2>NexusCX AI</h2>
            <span>Enterprise Support & RAG</span>
          </div>
        </div>

        {/* Modern Workspace / Tenant Switcher */}
        <div className="company-selector-box" ref={tenantDropdownRef}>
          <div className="company-selector-label">
            <span>Workspace</span>
            <button 
              onClick={() => setCompanyModalOpen(true)}
              className="btn-add-tenant"
              title="Add New Workspace"
            >
              + New
            </button>
          </div>
          
          <div className="custom-tenant-switcher">
            <button 
              type="button"
              className={`tenant-switcher-btn ${tenantDropdownOpen ? 'open' : ''}`}
              onClick={() => setTenantDropdownOpen(!tenantDropdownOpen)}
            >
              <div className="tenant-btn-avatar">
                {((companies.find(c => c.id === selectedCompanyId)?.name) || selectedCompanyId || 'W').charAt(0).toUpperCase()}
              </div>
              <div className="tenant-btn-info">
                <span className="tenant-btn-name">
                  {companies.find(c => c.id === selectedCompanyId)?.name || selectedCompanyId || 'Select Workspace'}
                </span>
                <span className="tenant-btn-id">{selectedCompanyId}</span>
              </div>
              <svg 
                className={`tenant-chevron ${tenantDropdownOpen ? 'rotated' : ''}`}
                width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {tenantDropdownOpen && (
              <div className="tenant-dropdown-menu">
                <div className="tenant-menu-header">
                  <span>Available Workspaces</span>
                  <span className="tenant-count">{companies.length}</span>
                </div>
                <div className="tenant-menu-list">
                  {companies.map((c) => {
                    const isSelected = c.id === selectedCompanyId;
                    return (
                      <div 
                        key={c.id} 
                        className={`tenant-menu-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedCompanyId(c.id);
                          setTenantDropdownOpen(false);
                        }}
                      >
                        <div className="tenant-item-avatar">
                          {c.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="tenant-item-details">
                          <span className="tenant-item-name">{c.name}</span>
                          <span className="tenant-item-id">{c.id}</span>
                        </div>
                        <div className="tenant-item-actions">
                          {isSelected && (
                            <span className="tenant-active-check">✓</span>
                          )}
                          {companies.length > 1 && (
                            <button
                              type="button"
                              className="tenant-btn-delete"
                              title={`Delete ${c.name}`}
                              onClick={(e) => handleDeleteCompany(e, c.id)}
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="tenant-menu-footer">
                  <button 
                    type="button" 
                    className="tenant-menu-create-btn"
                    onClick={() => {
                      setTenantDropdownOpen(false);
                      setCompanyModalOpen(true);
                    }}
                  >
                    + Register New Organization
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="sidebar-nav">
          <div 
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
            Overview
          </div>

          <div 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            AI Support Chat
          </div>

          <div 
            className={`nav-item ${activeTab === 'kb' ? 'active' : ''}`}
            onClick={() => setActiveTab('kb')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10M6 10h10"/></svg>
            Knowledge Base
          </div>

          <div 
            className={`nav-item ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18M16 10a4 4 0 0 1-8 0"/></svg>
            Orders & Inventory
          </div>

          <div 
            className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            Analytics
          </div>

          <div 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
            Settings & Integrations
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>Real Data Only</span>
          </div>
          <span>v2.0</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-wrapper">
        <header className="main-topbar">
          <div className="topbar-title">
            <h1>{tabTitles[activeTab]}</h1>
            <span className="topbar-badge">{selectedCompanyId || 'Select Company'}</span>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Grounded AI Agent</span>
          </div>
        </header>

        <div className="main-content">
          {activeTab === 'overview' && <OverviewView companyId={selectedCompanyId} onNavigate={setActiveTab} />}
          {activeTab === 'chat' && (
            <ChatView 
              companyId={selectedCompanyId} 
              companyName={companies.find(c => c.id === selectedCompanyId)?.name || selectedCompanyId}
              showToast={showToast} 
            />
          )}
          {activeTab === 'kb' && <KnowledgeBaseView companyId={selectedCompanyId} showToast={showToast} />}
          {activeTab === 'orders' && <OrdersInventoryView companyId={selectedCompanyId} onNavigate={setActiveTab} />}
          {activeTab === 'analytics' && <AnalyticsView companyId={selectedCompanyId} />}
          {activeTab === 'settings' && <SettingsView companyId={selectedCompanyId} showToast={showToast} />}
        </div>
      </main>

      {/* New Company Modal */}
      {companyModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Create New Company Tenant</h3>
              <button 
                onClick={() => setCompanyModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 18 }}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateCompany}>
              <div className="form-group">
                <label className="form-label">Company Identifier (Slug)</label>
                <input 
                  type="text" 
                  className="form-input"
                  placeholder="e.g. acme_corp"
                  value={newCompanyId}
                  onChange={(e) => setNewCompanyId(e.target.value)}
                  required 
                />
                <span className="form-help">Unique tenant key used for isolated vector store and caching.</span>
              </div>
              <div className="form-group">
                <label className="form-label">Company Name</label>
                <input 
                  type="text" 
                  className="form-input"
                  placeholder="e.g. Acme Corporation"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setCompanyModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Tenant</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const tabTitles = {
  overview: 'Overview Dashboard',
  chat: 'AI Customer Support Chat',
  kb: 'Knowledge Base Management',
  orders: 'Orders & Inventory Integrations',
  analytics: 'Telemetry & Observability',
  settings: 'Settings & Integrations'
};


// -------------------------------------------------------------
// 1. Overview View
// -------------------------------------------------------------
function OverviewView({ companyId, onNavigate }) {
  const [metrics, setMetrics] = useState(null);
  const [docs, setDocs] = useState([]);
  const [integrations, setIntegrations] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/api/metrics?company_id=${companyId}`).then(r => r.json()),
      fetch(`${API_BASE}/api/documents?company_id=${companyId}`).then(r => r.json()),
      fetch(`${API_BASE}/api/integrations?company_id=${companyId}`).then(r => r.json())
    ]).then(([metricsData, docsData, integrationsData]) => {
      setMetrics(metricsData.summary);
      setDocs(docsData.documents || []);
      setIntegrations(integrationsData);
    }).catch(console.error).finally(() => setLoading(false));
  }, [companyId]);

  if (loading) return <div style={{ color: '#94a3b8' }}>Loading tenant overview...</div>;

  const totalDocs = docs.length;
  const totalChunks = docs.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const totalQueries = metrics?.total_queries || 0;
  const cacheHitRate = metrics?.has_activity ? `${(metrics.cache_hit_rate * 100).toFixed(1)}%` : '0%';
  const ecommerceConfigured = integrations?.ecommerce?.configured;
  const inventoryConfigured = integrations?.inventory?.configured;

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Indexed Documents</span>
            <span className="badge badge-info">{totalChunks} Chunks</span>
          </div>
          <div className="stat-value">{totalDocs}</div>
          <div className="stat-subtext">Real company uploaded files</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Real Queries Logged</span>
            <span className="badge badge-neutral">Observed</span>
          </div>
          <div className="stat-value">{totalQueries}</div>
          <div className="stat-subtext">{metrics?.has_activity ? `Avg ${metrics.avg_latency_ms}ms latency` : 'No queries yet'}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Cache Hit Rate</span>
            <span className="badge badge-success">Multi-Tenant</span>
          </div>
          <div className="stat-value">{cacheHitRate}</div>
          <div className="stat-subtext">{metrics?.cache_hits || 0} exact & semantic hits</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Live Integrations</span>
            <span className={`badge ${ecommerceConfigured ? 'badge-success' : 'badge-warning'}`}>
              {ecommerceConfigured ? 'Connected' : 'Setup Required'}
            </span>
          </div>
          <div className="stat-value" style={{ fontSize: 18, marginTop: 4 }}>
            Orders: {ecommerceConfigured ? 'Active' : 'Not configured'}<br/>
            Stock: {inventoryConfigured ? 'Active' : 'Not configured'}
          </div>
          <div className="stat-subtext">Zero fake fallback data</div>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div className="content-card" style={{ marginBottom: 0 }}>
          <h3 className="content-card-title">Knowledge Base Grounding</h3>
          <p className="content-card-desc">Upload company return policies, warranties, shipping guidelines, and product catalogues in PDF, DOCX, TXT, or CSV.</p>
          <div style={{ marginTop: 16 }}>
            <button className="btn btn-primary btn-sm" onClick={() => onNavigate('kb')}>Manage Documents</button>
          </div>
        </div>

        <div className="content-card" style={{ marginBottom: 0 }}>
          <h3 className="content-card-title">Test Support Agent</h3>
          <p className="content-card-desc">Interact with the LangGraph customer support agent using live document grounding and safety guardrails.</p>
          <div style={{ marginTop: 16 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('chat')}>Open AI Chat</button>
          </div>
        </div>
      </div>

      {/* Real Recent Uploads */}
      <div className="content-card">
        <h3 className="content-card-title">Recent Company Documents</h3>
        <p className="content-card-desc">Real indexed source files available for vector retrieval for {companyId}.</p>
        <div style={{ marginTop: 16 }}>
          {docs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📄</div>
              <h3>No Documents Indexed Yet</h3>
              <p>Upload your company return policy or FAQ documents to ground AI customer support answers in real evidence.</p>
              <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }} onClick={() => onNavigate('kb')}>
                Upload Document
              </button>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Chunks</th>
                    <th>Status</th>
                    <th>Indexed At</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.slice(0, 5).map((d) => (
                    <tr key={d.id}>
                      <td style={{ fontWeight: 600 }}>{d.filename}</td>
                      <td><span className="badge badge-neutral">{d.file_type}</span></td>
                      <td>{(d.file_size / 1024).toFixed(1)} KB</td>
                      <td>{d.chunk_count}</td>
                      <td><span className="badge badge-success">{d.status}</span></td>
                      <td style={{ fontSize: 12, color: '#94a3b8' }}>{new Date(d.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


// -------------------------------------------------------------
// 2. AI Support Chat View
// -------------------------------------------------------------
function ChatView({ companyId, companyName, showToast }) {
  const [customerId, setCustomerId] = useState('');
  const [inputQuery, setInputQuery] = useState('');
  
  const getGreeting = (name) => 
    `Hello! I am NexusCX AI, your customer support assistant for **${name || 'Apex Retail Inc.'}**. How can I assist you with return policies, order status, or product stock today?`;

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: getGreeting(companyName),
      sources: []
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);

  // Sync greeting when company changes if user hasn't chatted yet
  useEffect(() => {
    if (companyName) {
      setMessages((prev) => {
        if (prev.length <= 1) {
          return [{
            role: 'assistant',
            content: getGreeting(companyName),
            sources: []
          }];
        }
        return prev;
      });
    }
  }, [companyId, companyName]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText) => {
    const q = queryText || inputQuery;
    if (!q.trim() || loading) return;

    const userMessage = { role: 'user', content: q.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          query: q.trim(),
          customer_id: customerId.trim() || null
        })
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.response,
            sources: data.sources || [],
            citations: data.citations || [],
            grounded: data.grounded,
            fromCache: data.from_cache,
            latency: data.latency_seconds,
            cacheType: data.cache_type
          }
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `I encountered an issue processing your query: ${data.detail || 'Internal error'}.`,
            sources: []
          }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Connection error: ${err.message}`,
          sources: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (index) => {
    setExpandedSources((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedQuestions = [
    'What is your return policy?',
    'Where is my order #12345?',
    'Is product PROD-10 in stock?',
    'Can I return delivered order #12345?'
  ];

  return (
    <div className="chat-container">
      {/* Customer Auth Simulation Bar */}
      <div className="chat-auth-header">
        <div className="chat-auth-input-group">
          <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', whiteSpace: 'nowrap' }}>Customer ID:</span>
          <input 
            type="text"
            className="chat-auth-input"
            placeholder="e.g. john@example.com (Optional for auth lookups)"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
          />
        </div>
        <button 
          className="btn btn-secondary btn-sm"
          onClick={() => setMessages([{
            role: 'assistant',
            content: `Conversation reset for ${companyId}. Ask any policy or order question.`,
            sources: []
          }])}
        >
          Clear Chat
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`message-row ${m.role}`}>
            <div className={`message-avatar ${m.role === 'user' ? 'avatar-user' : 'avatar-assistant'}`}>
              {m.role === 'user' ? 'U' : 'AI'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="message-bubble">
                <FormattedMessage content={m.content} isUser={m.role === 'user'} />

                {/* Sources & Citations Panel */}
                {m.sources && m.sources.length > 0 && (
                  <div className="citations-drawer">
                    <button 
                      className="citations-toggle"
                      onClick={() => toggleSources(idx)}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                      {expandedSources[idx] ? 'Hide Verified Sources' : `View ${m.sources.length} Verified Source(s)`}
                    </button>

                    {expandedSources[idx] && (
                      <div className="citations-list">
                        {m.sources.map((s, sIdx) => (
                          <div key={sIdx} className="citation-card">
                            <div className="citation-title">
                              <span>📄 {s.filename || s.source || 'Verified Source'}</span>
                              <span style={{ fontSize: 11, color: '#94a3b8' }}>{s.location || s.type}</span>
                            </div>
                            {s.content && (
                              <div className="citation-excerpt">
                                {s.content}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Message Meta Info */}
              {m.role === 'assistant' && m.latency !== undefined && (
                <div className="message-meta">
                  {m.fromCache ? (
                    <span className="badge badge-success">Cached ({m.cacheType})</span>
                  ) : (
                    <span className="badge badge-info">Live Agent</span>
                  )}
                  <span>Response in {m.latency}s</span>
                  {m.grounded && <span style={{ color: '#10b981' }}>✓ Grounded in documents</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row assistant">
            <div className="message-avatar avatar-assistant">AI</div>
            <div className="message-bubble" style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>Thinking & inspecting verified sources...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      <div className="suggested-queries">
        {suggestedQuestions.map((q, idx) => (
          <div 
            key={idx}
            className="suggestion-pill"
            onClick={() => handleSend(q)}
          >
            {q}
          </div>
        ))}
      </div>

      {/* Input Box */}
      <div className="chat-input-area">
        <textarea 
          className="chat-textarea"
          placeholder="Ask a customer support question (Enter to send, Shift+Enter for new line)..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />
        <button 
          className="btn btn-primary"
          onClick={() => handleSend()}
          disabled={loading || !inputQuery.trim()}
          style={{ height: 44, padding: '0 20px' }}
        >
          Send
        </button>
      </div>
    </div>
  );
}


// -------------------------------------------------------------
// 3. Knowledge Base View
// -------------------------------------------------------------
function KnowledgeBaseView({ companyId, showToast }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleteConfirmDoc, setDeleteConfirmDoc] = useState(null);
  const fileInputRef = useRef(null);

  const fetchDocs = async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/documents?company_id=${companyId}`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [companyId]);

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('company_id', companyId);
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message, 'success');
        fetchDocs();
      } else {
        showToast(data.detail || 'Upload failed', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/${docId}?company_id=${companyId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Document and vector chunks deleted.', 'success');
        setDeleteConfirmDoc(null);
        fetchDocs();
      } else {
        showToast(data.detail || 'Delete failed', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div>
      {/* Upload Zone */}
      <div className="content-card">
        <h3 className="content-card-title">Upload Company Knowledge</h3>
        <p className="content-card-desc">Supported formats: PDF, DOCX, TXT, CSV (max 25MB). Chunks are indexed with metadata into company-isolated vector storage.</p>
        
        <div 
          className="dropzone"
          style={{ marginTop: 16 }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept=".pdf,.docx,.txt,.csv,.md"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
          />
          <div className="dropzone-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
          </div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>
            {uploading ? 'Processing & Vectorizing Document...' : 'Drag & drop document here, or click to browse'}
          </div>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>PDF, DOCX, TXT, CSV</span>
        </div>
      </div>

      {/* Documents Table */}
      <div className="content-card">
        <div className="content-card-header">
          <div>
            <h3 className="content-card-title">Indexed Documents ({documents.length})</h3>
            <p className="content-card-desc">Documents currently grounding AI answers for {companyId}.</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchDocs}>Refresh</button>
        </div>

        {documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <h3>Knowledge Base is Empty</h3>
            <p>Upload your first company policy, product manual, or warranty document above. Answers will be strictly grounded in uploaded content.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Format</th>
                  <th>File Size</th>
                  <th>Indexed Chunks</th>
                  <th>Status</th>
                  <th>Upload Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 600 }}>{d.filename}</td>
                    <td><span className="badge badge-neutral">{d.file_type}</span></td>
                    <td>{(d.file_size / 1024).toFixed(1)} KB</td>
                    <td style={{ fontWeight: 600, color: '#818cf8' }}>{d.chunk_count}</td>
                    <td>
                      <span className={`badge ${d.status === 'indexed' ? 'badge-success' : 'badge-danger'}`}>
                        {d.status}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: '#94a3b8' }}>{new Date(d.created_at).toLocaleString()}</td>
                    <td>
                      <button 
                        className="btn btn-danger btn-sm"
                        onClick={() => setDeleteConfirmDoc(d)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmDoc && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Confirm Deletion</h3>
              <button 
                onClick={() => setDeleteConfirmDoc(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 18 }}
              >✕</button>
            </div>
            <p style={{ fontSize: 13.5, color: '#cbd5e1' }}>
              Are you sure you want to delete <strong>{deleteConfirmDoc.filename}</strong>?
              This will remove all {deleteConfirmDoc.chunk_count} vector chunks and invalidate the tenant cache.
            </p>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeleteConfirmDoc(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={() => handleDelete(deleteConfirmDoc.id)}>Delete Document</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// -------------------------------------------------------------
// 4. Orders & Inventory Integrations View
// -------------------------------------------------------------
function OrdersInventoryView({ companyId, onNavigate }) {
  const [integrations, setIntegrations] = useState(null);
  const [loading, setLoading] = useState(true);

  // Live tester state
  const [testOrderId, setTestOrderId] = useState('');
  const [orderResult, setOrderResult] = useState(null);
  const [orderTesting, setOrderTesting] = useState(false);

  const [testProductId, setTestProductId] = useState('');
  const [inventoryResult, setInventoryResult] = useState(null);
  const [inventoryTesting, setInventoryTesting] = useState(false);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    fetch(`${API_BASE}/api/integrations?company_id=${companyId}`)
      .then(r => r.json())
      .then(setIntegrations)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [companyId]);

  const handleTestOrder = async () => {
    if (!testOrderId.trim()) return;
    setOrderTesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          query: `What is the status of order #${testOrderId.trim()}?`
        })
      });
      const data = await res.json();
      setOrderResult(data);
    } catch (err) {
      setOrderResult({ error: err.message });
    } finally {
      setOrderTesting(false);
    }
  };

  const handleTestInventory = async () => {
    if (!testProductId.trim()) return;
    setInventoryTesting(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          query: `Is product #${testProductId.trim()} in stock?`
        })
      });
      const data = await res.json();
      setInventoryResult(data);
    } catch (err) {
      setInventoryResult({ error: err.message });
    } finally {
      setInventoryTesting(false);
    }
  };

  if (loading) return <div style={{ color: '#94a3b8' }}>Checking integration statuses...</div>;

  const ecommerceActive = integrations?.ecommerce?.configured;
  const inventoryActive = integrations?.inventory?.configured;

  return (
    <div>
      {/* Integration Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div className="content-card" style={{ marginBottom: 0 }}>
          <div className="content-card-header">
            <div>
              <h3 className="content-card-title">E-Commerce Orders API</h3>
              <p className="content-card-desc">Live customer orders, shipping, tracking, and delivery dates.</p>
            </div>
            <span className={`badge ${ecommerceActive ? 'badge-success' : 'badge-warning'}`}>
              {ecommerceActive ? 'Connected' : 'Not Configured'}
            </span>
          </div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
            {ecommerceActive ? (
              <span>Provider: {integrations.ecommerce.provider}</span>
            ) : (
              <span>No live order integration connected. System explicitly reports unconfigured status and never invents fake orders.</span>
            )}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('settings')}>
            Configure in Settings
          </button>
        </div>

        <div className="content-card" style={{ marginBottom: 0 }}>
          <div className="content-card-header">
            <div>
              <h3 className="content-card-title">Inventory Stock API</h3>
              <p className="content-card-desc">Real-time product availability and warehouse stock counts.</p>
            </div>
            <span className={`badge ${inventoryActive ? 'badge-success' : 'badge-warning'}`}>
              {inventoryActive ? 'Connected' : 'Not Configured'}
            </span>
          </div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
            {inventoryActive ? (
              <span>Provider: {integrations.inventory.provider}</span>
            ) : (
              <span>No live inventory source connected. System explicitly informs users without fabricating stock levels.</span>
            )}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('settings')}>
            Configure in Settings
          </button>
        </div>
      </div>

      {/* Live System Query Verification */}
      <div className="content-card">
        <h3 className="content-card-title">Live System Query Verifier</h3>
        <p className="content-card-desc">Test how the agent interacts with live integrations or reports unconfigured statuses truthfully.</p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 20 }}>
          {/* Order Test Box */}
          <div style={{ background: '#101827', padding: 18, borderRadius: 10, border: '1px solid #1e2c44' }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Test Order Lookup</h4>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input 
                type="text" 
                className="form-input"
                placeholder="Enter Order ID (e.g. 12345)"
                value={testOrderId}
                onChange={(e) => setTestOrderId(e.target.value)}
              />
              <button className="btn btn-primary btn-sm" onClick={handleTestOrder} disabled={orderTesting}>
                {orderTesting ? 'Checking...' : 'Lookup'}
              </button>
            </div>
            {orderResult && (
              <div style={{ background: '#131c2e', padding: 12, borderRadius: 8, fontSize: 12.5, whiteSpace: 'pre-wrap' }}>
                {orderResult.response || JSON.stringify(orderResult, null, 2)}
              </div>
            )}
          </div>

          {/* Inventory Test Box */}
          <div style={{ background: '#101827', padding: 18, borderRadius: 10, border: '1px solid #1e2c44' }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Test Inventory Lookup</h4>
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input 
                type="text" 
                className="form-input"
                placeholder="Enter Product ID (e.g. SKU-50)"
                value={testProductId}
                onChange={(e) => setTestProductId(e.target.value)}
              />
              <button className="btn btn-primary btn-sm" onClick={handleTestInventory} disabled={inventoryTesting}>
                {inventoryTesting ? 'Checking...' : 'Lookup'}
              </button>
            </div>
            {inventoryResult && (
              <div style={{ background: '#131c2e', padding: 12, borderRadius: 8, fontSize: 12.5, whiteSpace: 'pre-wrap' }}>
                {inventoryResult.response || JSON.stringify(inventoryResult, null, 2)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


// -------------------------------------------------------------
// 5. Analytics & Telemetry View
// -------------------------------------------------------------
function AnalyticsView({ companyId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    fetch(`${API_BASE}/api/metrics?company_id=${companyId}`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [companyId]);

  if (loading) return <div style={{ color: '#94a3b8' }}>Loading telemetry...</div>;

  const summary = data?.summary;
  const logs = data?.recent_logs || [];

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Total Queries</span>
            <span className="badge badge-info">Real</span>
          </div>
          <div className="stat-value">{summary?.total_queries || 0}</div>
          <div className="stat-subtext">Real queries recorded in SQLite</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Average Latency</span>
            <span className="badge badge-neutral">Observed</span>
          </div>
          <div className="stat-value">{summary?.has_activity ? `${summary.avg_latency_ms} ms` : '—'}</div>
          <div className="stat-subtext">{summary?.has_activity ? `P95: ${summary.p95_latency_ms} ms` : 'No queries yet'}</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Cache Hit Rate</span>
            <span className="badge badge-success">Optimized</span>
          </div>
          <div className="stat-value">{summary?.has_activity ? `${(summary.cache_hit_rate * 100).toFixed(1)}%` : '—'}</div>
          <div className="stat-subtext">{summary?.cache_hits || 0} hits</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Agent Avg Steps</span>
            <span className="badge badge-neutral">ReAct Loop</span>
          </div>
          <div className="stat-value">{summary?.has_activity ? summary.avg_steps : '—'}</div>
          <div className="stat-subtext">Planning to resolution</div>
        </div>
      </div>

      {/* Tool Usage Breakdown */}
      {summary?.has_activity && summary.tool_usage && Object.keys(summary.tool_usage).length > 0 && (
        <div className="content-card">
          <h3 className="content-card-title">Observed Tool Invocations</h3>
          <p className="content-card-desc">Actual tools chosen by the LangGraph planner.</p>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 16 }}>
            {Object.entries(summary.tool_usage).map(([tool, count]) => (
              <div key={tool} style={{ background: '#101827', padding: '12px 18px', borderRadius: 8, border: '1px solid #1e2c44' }}>
                <span style={{ fontSize: 12, color: '#94a3b8' }}>{tool}</span>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginTop: 4 }}>{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Real Query Log Table */}
      <div className="content-card">
        <h3 className="content-card-title">Actual Query Log</h3>
        <p className="content-card-desc">Telemetry records from real user sessions for {companyId}.</p>
        <div style={{ marginTop: 16 }}>
          {logs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <h3>No Activity Yet</h3>
              <p>Test queries in the AI Support Chat to generate real telemetry and latency statistics.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Query</th>
                    <th>Source</th>
                    <th>Latency</th>
                    <th>Steps</th>
                    <th>Tools Called</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td style={{ fontSize: 12, color: '#94a3b8', whiteSpace: 'nowrap' }}>
                        {new Date(l.timestamp).toLocaleTimeString()}
                      </td>
                      <td style={{ fontWeight: 600, maxWidth: 350 }}>{l.query}</td>
                      <td>
                        {l.from_cache ? (
                          <span className="badge badge-success">Cache</span>
                        ) : (
                          <span className="badge badge-info">Agent</span>
                        )}
                      </td>
                      <td>{l.total_latency_ms} ms</td>
                      <td>{l.steps}</td>
                      <td style={{ fontSize: 12, color: '#818cf8' }}>
                        {l.tools_used && l.tools_used.length > 0 ? l.tools_used.join(', ') : 'None'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


// -------------------------------------------------------------
// 6. Settings & Integrations View
// -------------------------------------------------------------
function SettingsView({ companyId, showToast }) {
  const [ecomUrl, setEcomUrl] = useState('');
  const [ecomKey, setEcomKey] = useState('');
  const [ecomActive, setEcomActive] = useState(false);

  const [invUrl, setInvUrl] = useState('');
  const [invKey, setInvKey] = useState('');
  const [invActive, setInvActive] = useState(false);

  const [saving, setSaving] = useState(false);
  const [testingEcom, setTestingEcom] = useState(false);
  const [testingInv, setTestingInv] = useState(false);

  useEffect(() => {
    if (!companyId) return;
    fetch(`${API_BASE}/api/integrations?company_id=${companyId}`)
      .then(r => r.json())
      .then(data => {
        if (data.ecommerce?.configured) setEcomActive(true);
        if (data.inventory?.configured) setInvActive(true);
      })
      .catch(console.error);
  }, [companyId]);

  const handleSaveEcom = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          integration_type: 'ecommerce',
          provider: 'rest_api',
          config: { endpoint_url: ecomUrl.trim(), api_key: ecomKey.trim() },
          is_active: ecomActive
        })
      });
      if (res.ok) {
        showToast('E-Commerce integration configuration saved.', 'success');
      } else {
        showToast('Failed to save settings', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveInv = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          integration_type: 'inventory',
          provider: 'rest_api',
          config: { endpoint_url: invUrl.trim(), api_key: invKey.trim() },
          is_active: invActive
        })
      });
      if (res.ok) {
        showToast('Inventory integration configuration saved.', 'success');
      } else {
        showToast('Failed to save settings', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleTestEcom = async () => {
    setTestingEcom(true);
    try {
      const res = await fetch(`${API_BASE}/api/integrations/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          integration_type: 'ecommerce',
          provider: 'rest_api',
          config: { endpoint_url: ecomUrl.trim(), api_key: ecomKey.trim() }
        })
      });
      const data = await res.json();
      showToast(data.message, data.success ? 'success' : 'error');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setTestingEcom(false);
    }
  };

  const handleTestInv = async () => {
    setTestingInv(true);
    try {
      const res = await fetch(`${API_BASE}/api/integrations/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,
          integration_type: 'inventory',
          provider: 'rest_api',
          config: { endpoint_url: invUrl.trim(), api_key: invKey.trim() }
        })
      });
      const data = await res.json();
      showToast(data.message, data.success ? 'success' : 'error');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setTestingInv(false);
    }
  };

  return (
    <div>
      {/* Platform & Model Overview */}
      <div className="content-card">
        <h3 className="content-card-title">AI Engine & Model Architecture</h3>
        <p className="content-card-desc">Grounded agent settings and safety parameters.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginTop: 16 }}>
          <div style={{ background: '#101827', padding: 14, borderRadius: 8, border: '1px solid #1e2c44' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>LLM Model</span>
            <div style={{ fontWeight: 600, color: '#fff', marginTop: 4 }}>Gemini 3.5 Flash</div>
          </div>
          <div style={{ background: '#101827', padding: 14, borderRadius: 8, border: '1px solid #1e2c44' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Embedding Model</span>
            <div style={{ fontWeight: 600, color: '#fff', marginTop: 4 }}>models/gemini-embedding-001</div>
          </div>
          <div style={{ background: '#101827', padding: 14, borderRadius: 8, border: '1px solid #1e2c44' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Vector Store</span>
            <div style={{ fontWeight: 600, color: '#fff', marginTop: 4 }}>SQLite Persistent Vector Store</div>
          </div>
          <div style={{ background: '#101827', padding: 14, borderRadius: 8, border: '1px solid #1e2c44' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Safety Guardrails</span>
            <div style={{ fontWeight: 600, color: '#10b981', marginTop: 4 }}>PII Masking & Step Limits Active</div>
          </div>
        </div>
      </div>

      {/* E-Commerce Config */}
      <div className="content-card">
        <h3 className="content-card-title">Live E-Commerce Orders Integration</h3>
        <p className="content-card-desc">Connect an authorized orders API or database for real order lookups.</p>
        <form onSubmit={handleSaveEcom} style={{ marginTop: 18 }}>
          <div className="form-group">
            <label className="form-label">Orders REST API Base URL</label>
            <input 
              type="url" 
              className="form-input" 
              placeholder="https://api.yourcompany.com/v1"
              value={ecomUrl}
              onChange={(e) => setEcomUrl(e.target.value)}
            />
            <span className="form-help">Must provide endpoint: <code>/orders/{'{order_id}'}</code> and <code>/health</code></span>
          </div>

          <div className="form-group">
            <label className="form-label">API Bearer Token / Key</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder="••••••••••••••••"
              value={ecomKey}
              onChange={(e) => setEcomKey(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
            <input 
              type="checkbox" 
              id="ecomActive"
              checked={ecomActive}
              onChange={(e) => setEcomActive(e.target.checked)}
            />
            <label htmlFor="ecomActive" style={{ fontSize: 13, cursor: 'pointer' }}>Enable this integration for {companyId}</label>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleTestEcom} disabled={testingEcom || !ecomUrl}>
              {testingEcom ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </form>
      </div>

      {/* Inventory Config */}
      <div className="content-card">
        <h3 className="content-card-title">Live Inventory Stock Integration</h3>
        <p className="content-card-desc">Connect an authorized warehouse or ERP inventory API.</p>
        <form onSubmit={handleSaveInv} style={{ marginTop: 18 }}>
          <div className="form-group">
            <label className="form-label">Inventory REST API Base URL</label>
            <input 
              type="url" 
              className="form-input" 
              placeholder="https://inventory.yourcompany.com/v1"
              value={invUrl}
              onChange={(e) => setInvUrl(e.target.value)}
            />
            <span className="form-help">Must provide endpoint: <code>/inventory/{'{product_id}'}</code> and <code>/health</code></span>
          </div>

          <div className="form-group">
            <label className="form-label">API Bearer Token / Key</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder="••••••••••••••••"
              value={invKey}
              onChange={(e) => setInvKey(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
            <input 
              type="checkbox" 
              id="invActive"
              checked={invActive}
              onChange={(e) => setInvActive(e.target.checked)}
            />
            <label htmlFor="invActive" style={{ fontSize: 13, cursor: 'pointer' }}>Enable this integration for {companyId}</label>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleTestInv} disabled={testingInv || !invUrl}>
              {testingInv ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
