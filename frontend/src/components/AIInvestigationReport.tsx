
export type InvestigationReport = {
  transaction_id: string
  account_id: string
  risk_level: string
  risk_score: number
  fraud_indicators: string[]
  recommendation: string
  investigation_summary: string
  alert_status: string
  investigation_type: string
}

type Props = {
  report: InvestigationReport
}

export default function AIInvestigationReport({ report }: Props) {
  return (
    <section
      style={{
        marginTop: '20px',
        padding: '24px',
        border: '1px solid #334155',
        borderRadius: '10px',
        backgroundColor: '#172033',
        color: '#f8fafc',
      }}
    >
      <h3>Fraud Investigation Report</h3>

      <p>
        <strong>Transaction:</strong> {report.transaction_id}
      </p>

      <p>
        <strong>Risk Level:</strong> {report.risk_level}
      </p>

      <p>
        <strong>Risk Score:</strong> {report.risk_score}/100
      </p>

      <h4>Detected Fraud Indicators</h4>

      <ul>
        {report.fraud_indicators.map((indicator, index) => (
          <li key={`${index}-${indicator}`}>{indicator}</li>
        ))}
      </ul>

      <h4>Recommended Action</h4>
      <p>{report.recommendation}</p>

      <h4>Investigation Summary</h4>
      <p>{report.investigation_summary}</p>

      <p style={{ fontSize: '12px', color: '#94a3b8' }}>
        Investigation engine: {report.investigation_type}
      </p>
    </section>
  )
}
