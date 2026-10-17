
import { useEffect, useRef, useState } from 'react'
import AIInvestigationReport, {
  type InvestigationReport,
} from './components/AIInvestigationReport'
import './App.css'

type DashboardSummary = {
  total_alerts: number
  open_alerts: number
  high_risk_alerts: number
  average_risk_score: number
}

type FraudAlert = {
  transaction_id: string
  account_id: string
  risk_level: string
  risk_score: number
  reason: string
  status: string
  created_at: string
}

type FraudAlertsResponse = {
  total_alerts: number
  alerts: FraudAlert[]
}

type StatusUpdateResponse = {
  message: string
  alert: FraudAlert
}

const API_BASE_URL = 'http://127.0.0.1:8000'

const buttonStyle = {
  padding: '8px 14px',
  border: '1px solid #5265a8',
  borderRadius: '6px',
  backgroundColor: '#283c80',
  color: '#ffffff',
  cursor: 'pointer',
  fontWeight: 600,
} as const

function App() {
  const [summary, setSummary] =
    useState<DashboardSummary | null>(null)

  const [alerts, setAlerts] = useState<FraudAlert[]>([])

  const [selectedAlert, setSelectedAlert] =
    useState<FraudAlert | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [updatingStatus, setUpdatingStatus] = useState(false)
  const [updateError, setUpdateError] = useState('')
  const [updateSuccess, setUpdateSuccess] = useState('')

  const [investigationReport, setInvestigationReport] =
    useState<InvestigationReport | null>(null)

  const [investigationLoading, setInvestigationLoading] =
    useState(false)

  const [investigationError, setInvestigationError] =
    useState('')

  const investigationController =
    useRef<AbortController | null>(null)

  function clearInvestigation() {
    investigationController.current?.abort()
    investigationController.current = null

    setInvestigationReport(null)
    setInvestigationLoading(false)
    setInvestigationError('')
  }

  async function generateInvestigationReport(
    transactionId: string
  ) {
    investigationController.current?.abort()

    const controller = new AbortController()
    investigationController.current = controller

    setInvestigationLoading(true)
    setInvestigationError('')
    setInvestigationReport(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/fraud-alerts/${encodeURIComponent(
          transactionId
        )}/investigate`,
        {
          signal: controller.signal,
        }
      )

      if (!response.ok) {
        let message =
          `Investigation failed (${response.status})`

        try {
          const errorData = await response.json()

          if (typeof errorData.detail === 'string') {
            message = errorData.detail
          }
        } catch {
          // Keep the default HTTP error message.
        }

        throw new Error(message)
      }

      const report: InvestigationReport =
        await response.json()

      if (!controller.signal.aborted) {
        setInvestigationReport(report)
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setInvestigationError(
          err instanceof Error
            ? err.message
            : 'Unable to generate investigation report'
        )
      }
    } finally {
      if (!controller.signal.aborted) {
        setInvestigationLoading(false)
      }
    }
  }

  async function fetchDashboardData(
    signal?: AbortSignal
  ) {
    const [summaryResponse, alertsResponse] =
      await Promise.all([
        fetch(`${API_BASE_URL}/dashboard/summary`, {
          signal,
        }),
        fetch(`${API_BASE_URL}/fraud-alerts`, {
          signal,
        }),
      ])

    if (!summaryResponse.ok || !alertsResponse.ok) {
      throw new Error(
        'Failed to load dashboard data'
      )
    }

    const summaryData: DashboardSummary =
      await summaryResponse.json()

    const alertsData: FraudAlertsResponse =
      await alertsResponse.json()

    return {
      summaryData,
      alertsData,
    }
  }

  useEffect(() => {
    const controller = new AbortController()

    async function loadDashboard() {
      try {
        const { summaryData, alertsData } =
          await fetchDashboardData(
            controller.signal
          )

        if (controller.signal.aborted) return

        setSummary(summaryData)
        setAlerts(alertsData.alerts)
        setError('')
      } catch (err) {
        if (controller.signal.aborted) return

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to connect to FastAPI'
        )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadDashboard()

    return () => {
      controller.abort()
      investigationController.current?.abort()
    }
  }, [])

  async function updateAlertStatus(
    newStatus: string
  ) {
    if (!selectedAlert || updatingStatus) return

    setUpdatingStatus(true)
    setUpdateError('')
    setUpdateSuccess('')

    try {
      const response = await fetch(
        `${API_BASE_URL}/fraud-alerts/${encodeURIComponent(
          selectedAlert.transaction_id
        )}/status`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: newStatus,
          }),
        }
      )

      if (!response.ok) {
        let message =
          `Status update failed (${response.status})`

        try {
          const errorData = await response.json()

          if (typeof errorData.detail === 'string') {
            message = errorData.detail
          }
        } catch {
          // Keep the default HTTP error message.
        }

        throw new Error(message)
      }

      const result: StatusUpdateResponse =
        await response.json()

      // Update the selected alert immediately.
      setSelectedAlert(result.alert)

      // Update the matching alert in the table.
      setAlerts((currentAlerts) =>
        currentAlerts.map((alert) =>
          alert.transaction_id ===
          result.alert.transaction_id
            ? result.alert
            : alert
        )
      )

      setUpdateSuccess(
        `Alert status updated to ${result.alert.status}`
      )

      // Refresh metrics and alerts from the backend.
      try {
        const { summaryData, alertsData } =
          await fetchDashboardData()

        setSummary(summaryData)
        setAlerts(alertsData.alerts)

        const refreshedAlert =
          alertsData.alerts.find(
            (alert) =>
              alert.transaction_id ===
              result.alert.transaction_id
          )

        if (refreshedAlert) {
          setSelectedAlert(refreshedAlert)
        }
      } catch {
        setUpdateError(
          'Status saved, but dashboard refresh failed. ' +
          'Reload the page to refresh metrics.'
        )
      }
    } catch (err) {
      setUpdateError(
        err instanceof Error
          ? err.message
          : 'Unable to update fraud alert'
      )
    } finally {
      setUpdatingStatus(false)
    }
  }

  if (loading) {
    return (
      <div className="dashboard">
        <main className="dashboard-main">
          <h2>Loading dashboard...</h2>
        </main>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="dashboard">
        <main className="dashboard-main">
          <h2>Unable to load dashboard</h2>

          <p>
            {error || 'Dashboard data unavailable'}
          </p>

          <p>
            Please check that FastAPI is running.
          </p>
        </main>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="brand">
          <div className="brand-icon">🛡️</div>

          <div>
            <h1>BankFraud AI</h1>
            <p>Fraud Investigation Center</p>
          </div>
        </div>

        <span className="environment-badge">
          DEMO ENVIRONMENT
        </span>
      </header>

      <main className="dashboard-main">
        <div className="page-heading">
          <div>
            <h2>Fraud Overview</h2>

            <p>
              Monitor suspicious banking activity
              and fraud investigation alerts.
            </p>
          </div>
        </div>

        <section className="metrics-grid">
          <div className="metric-card">
            <p>Total Alerts</p>
            <h3>{summary.total_alerts}</h3>
            <span>All detected fraud alerts</span>
          </div>

          <div className="metric-card">
            <p>Open Alerts</p>
            <h3>{summary.open_alerts}</h3>
            <span>Awaiting investigation</span>
          </div>

          <div className="metric-card">
            <p>High-Risk Alerts</p>

            <h3 className="danger">
              {summary.high_risk_alerts}
            </h3>

            <span>Require priority review</span>
          </div>

          <div className="metric-card">
            <p>Average Risk Score</p>

            <h3>
              {summary.average_risk_score}
              <small>/100</small>
            </h3>

            <span>Across all fraud alerts</span>
          </div>
        </section>

        <section className="alerts-panel">
          <div className="panel-heading">
            <div>
              <h3>Recent Fraud Alerts</h3>

              <p>
                Transactions flagged by the
                fraud detection engine
              </p>
            </div>
          </div>

          <div className="alerts-table-wrapper">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Account ID</th>
                  <th>Risk Level</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      No fraud alerts found.
                    </td>
                  </tr>
                ) : (
                  alerts.map((alert) => (
                    <tr key={alert.transaction_id}>
                      <td>{alert.transaction_id}</td>
                      <td>{alert.account_id}</td>

                      <td>
                        <span className="risk-badge">
                          {alert.risk_level}
                        </span>
                      </td>

                      <td>{alert.risk_score}</td>

                      <td>
                        <span className="status-badge">
                          {alert.status}
                        </span>
                      </td>

                      <td>
                        <button
                          type="button"
                          onClick={() => {
                            clearInvestigation()
                            setSelectedAlert(alert)
                            setUpdateError('')
                            setUpdateSuccess('')
                          }}
                          style={buttonStyle}
                        >
                          Investigate
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {selectedAlert && (
          <section
            className="alerts-panel"
            style={{ marginTop: '20px' }}
          >
            <div
              className="panel-heading"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '16px',
              }}
            >
              <div>
                <h3>Fraud Investigation Details</h3>

                <p>
                  Selected transaction:{' '}
                  {selectedAlert.transaction_id}
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  clearInvestigation()
                  setSelectedAlert(null)
                  setUpdateError('')
                  setUpdateSuccess('')
                }}
                disabled={updatingStatus}
                style={buttonStyle}
              >
                Close
              </button>
            </div>

            <div
              style={{
                padding: '24px',
                display: 'grid',
                gap: '12px',
              }}
            >
              <div>
                <strong>Transaction ID:</strong>{' '}
                {selectedAlert.transaction_id}
              </div>

              <div>
                <strong>Account ID:</strong>{' '}
                {selectedAlert.account_id}
              </div>

              <div>
                <strong>Risk Level:</strong>{' '}
                {selectedAlert.risk_level}
              </div>

              <div>
                <strong>Risk Score:</strong>{' '}
                {selectedAlert.risk_score}/100
              </div>

              <div>
                <strong>Status:</strong>{' '}
                {selectedAlert.status}
              </div>

              <div>
                <strong>Detection Time:</strong>{' '}
                {new Date(
                  selectedAlert.created_at
                ).toLocaleString()}
              </div>

              <div>
                <strong>Fraud Detection Reason:</strong>
              </div>

              <div>{selectedAlert.reason}</div>

              {updateSuccess && (
                <p
                  role="status"
                  style={{ color: '#4ade80' }}
                >
                  {updateSuccess}
                </p>
              )}

              {updateError && (
                <p
                  role="alert"
                  style={{ color: '#fb7185' }}
                >
                  {updateError}
                </p>
              )}

              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  flexWrap: 'wrap',
                  marginTop: '12px',
                }}
              >
                {selectedAlert.status === 'OPEN' && (
                  <button
                    type="button"
                    disabled={updatingStatus}
                    onClick={() =>
                      updateAlertStatus('UNDER_REVIEW')
                    }
                    style={buttonStyle}
                  >
                    {updatingStatus
                      ? 'Updating...'
                      : 'Start Review'}
                  </button>
                )}

                {selectedAlert.status === 'UNDER_REVIEW' && (
                  <button
                    type="button"
                    disabled={updatingStatus}
                    onClick={() =>
                      updateAlertStatus('RESOLVED')
                    }
                    style={{
                      ...buttonStyle,
                      backgroundColor: '#166534',
                      borderColor: '#15803d',
                    }}
                  >
                    {updatingStatus
                      ? 'Updating...'
                      : 'Resolve Alert'}
                  </button>
                )}

                {selectedAlert.status === 'RESOLVED' && (
                  <span style={{ color: '#4ade80' }}>
                    Investigation completed
                  </span>
                )}

                <button
                  type="button"
                  onClick={() =>
                    generateInvestigationReport(
                      selectedAlert.transaction_id
                    )
                  }
                  disabled={investigationLoading}
                  style={buttonStyle}
                >
                  {investigationLoading
                    ? 'Generating Report...'
                    : 'Generate Investigation Report'}
                </button>
              </div>

              {investigationError && (
                <p
                  role="alert"
                  style={{ color: '#fb7185' }}
                >
                  {investigationError}
                </p>
              )}

              {investigationReport &&
                investigationReport.transaction_id ===
                  selectedAlert.transaction_id && (
                  <AIInvestigationReport
                    report={investigationReport}
                  />
                )}
            </div>
          </section>
        )}

        <footer className="dashboard-footer">
          BankFraud AI | Synthetic Banking
          Fraud Detection Platform
        </footer>
      </main>
    </div>
  )
}

export default App
