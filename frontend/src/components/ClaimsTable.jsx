import { useState } from 'react'

const STATUS_MAP = {
    approved: { cls: 'badge-approved', label: '✅ Approved' },
    flagged: { cls: 'badge-flagged', label: '🔴 Flagged' },
    pending: { cls: 'badge-pending', label: '⏳ Pending' },
    rejected: { cls: 'badge-rejected', label: '❌ Rejected' },
}

function fmt(amount) {
    return `$${Number(amount || 0).toLocaleString('en-US', { minimumFractionDigits: 0 })}`
}
function fmtDate(d) {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function ClaimsTable({ items = [], loading = false, total = 0, page = 1, totalPages = 1, onPageChange }) {
    const [sort, setSort] = useState({ col: 'submitted_at', dir: 'desc' })

    const sorted = [...items].sort((a, b) => {
        const av = a[sort.col], bv = b[sort.col]
        if (av == null) return 1
        if (bv == null) return -1
        const cmp = av < bv ? -1 : av > bv ? 1 : 0
        return sort.dir === 'asc' ? cmp : -cmp
    })

    const toggleSort = (col) => setSort(s => ({ col, dir: s.col === col && s.dir === 'asc' ? 'desc' : 'asc' }))
    const sortIcon = (col) => sort.col !== col ? '⇅' : sort.dir === 'asc' ? '↑' : '↓'

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <div className="spinner" />
        </div>
    )
    if (items.length === 0) return (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
            <div>No claims found</div>
        </div>
    )

    return (
        <div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            {[
                                ['full_name', 'Policyholder'],
                                ['claim_type', 'Type'],
                                ['requested_amount', 'Requested'],
                                ['estimated_payout', 'Est. Payout'],
                                ['fraud_score', 'Fraud Score'],
                                ['status', 'Status'],
                                ['submitted_at', 'Date'],
                            ].map(([col, label]) => (
                                <th key={col} onClick={() => toggleSort(col)}
                                    style={{ cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}>
                                    {label} <span style={{ opacity: 0.5 }}>{sortIcon(col)}</span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map(claim => {
                            const fs = claim.fraud_score
                            const fraudCls = fs == null ? '' : fs > 0.5 ? 'row-fraud-high' : 'row-fraud-low'
                            const badge = STATUS_MAP[claim.status] || STATUS_MAP.pending
                            return (
                                <tr key={claim.claim_id}>
                                    <td>
                                        <div style={{ fontWeight: 600 }}>{claim.full_name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            #{String(claim.claim_id).slice(0, 8)}
                                        </div>
                                    </td>
                                    <td>
                                        <span style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>{claim.claim_type}</span>
                                    </td>
                                    <td className="row-amount">{fmt(claim.requested_amount)}</td>
                                    <td style={{ color: 'var(--text-secondary)' }}>
                                        {claim.estimated_payout != null ? fmt(claim.estimated_payout) : '—'}
                                    </td>
                                    <td className={fraudCls}>
                                        {fs != null ? (
                                            <div className="flex items-center gap-2">
                                                <div style={{ width: 48, height: 5, background: 'var(--bg-secondary)', borderRadius: 100, overflow: 'hidden' }}>
                                                    <div style={{
                                                        height: '100%', borderRadius: 100,
                                                        width: `${fs * 100}%`,
                                                        background: fs > 0.5 ? 'var(--accent-rose)' : 'var(--accent-emerald)',
                                                    }} />
                                                </div>
                                                {(fs * 100).toFixed(0)}%
                                            </div>
                                        ) : '—'}
                                    </td>
                                    <td>
                                        <span className={`badge ${badge.cls}`}>{badge.label}</span>
                                    </td>
                                    <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                        {fmtDate(claim.submitted_at)}
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4" style={{ padding: '0.75rem 0' }}>
                    <div className="text-sm text-muted">
                        Showing {items.length} of {total} claims
                    </div>
                    <div className="flex gap-2">
                        <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
                            ← Prev
                        </button>
                        <span className="flex items-center" style={{ padding: '0.5rem 0.75rem', fontSize: '0.875rem' }}>
                            Page {page} of {totalPages}
                        </span>
                        <button className="btn btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
                            Next →
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
