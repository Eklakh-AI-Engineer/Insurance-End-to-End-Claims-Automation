import { useState, useEffect, useCallback } from 'react'
import { getDashboardStats, getClaims } from '../api'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell, Legend,
} from 'recharts'
import FraudHeatmap from './FraudHeatmap'
import ClaimsTable from './ClaimsTable'

const STAT_CONFIG = [
    { key: 'total_claims', label: 'Total Claims', icon: '📋', color: '#3b82f6' },
    { key: 'approved', label: 'Auto-Approved', icon: '✅', color: '#10b981' },
    { key: 'flagged', label: 'Flagged', icon: '🔴', color: '#f43f5e' },
    { key: 'total_payout', label: 'Total Paid Out', icon: '💰', color: '#06b6d4', isMoney: true },
    { key: 'avg_fraud_score', label: 'Avg Fraud Score', icon: '🛡️', color: '#f59e0b', isPct: true },
    { key: 'avg_claim_amount', label: 'Avg Claim Amount', icon: '📊', color: '#8b5cf6', isMoney: true },
]

const STATUS_FILTERS = [
    { value: '', label: 'All Claims' },
    { value: 'pending', label: '⏳ Pending' },
    { value: 'approved', label: '✅ Approved' },
    { value: 'flagged', label: '🔴 Flagged' },
    { value: 'rejected', label: '❌ Rejected' },
]

const PIE_COLORS = ['#3b82f6', '#10b981', '#f43f5e', '#64748b']

function fmt(v, isMoney, isPct) {
    if (isMoney) return `$${Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
    if (isPct) return `${(Number(v || 0) * 100).toFixed(1)}%`
    return Number(v || 0).toLocaleString()
}

function StatCard({ stat, value }) {
    const cfg = STAT_CONFIG.find(s => s.key === stat) || {}
    return (
        <div className="stat-card" style={{ '--accent-gradient': `linear-gradient(90deg, ${cfg.color}, ${cfg.color}88)` }}>
            <div className="stat-icon" style={{ background: `${cfg.color}22`, color: cfg.color }}>
                {cfg.icon}
            </div>
            <div className="stat-value">{fmt(value, cfg.isMoney, cfg.isPct)}</div>
            <div className="stat-label">{cfg.label}</div>
        </div>
    )
}

// Generate dummy trend data for the chart
function generateTrend(days = 14) {
    return Array.from({ length: days }, (_, i) => {
        const d = new Date(); d.setDate(d.getDate() - (days - 1 - i))
        return {
            date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            claims: Math.floor(Math.random() * 30 + 10),
            fraud: Math.floor(Math.random() * 8 + 1),
            payout: Math.floor(Math.random() * 50000 + 10000),
        }
    })
}

export default function AdminDashboard() {
    const [stats, setStats] = useState(null)
    const [claims, setClaims] = useState([])
    const [loading, setLoading] = useState(true)
    const [claimsLoading, setClaimsLoading] = useState(true)
    const [statusFilter, setStatusFilter] = useState('')
    const [page, setPage] = useState(1)
    const [pagination, setPagination] = useState({ total: 0, totalPages: 1 })
    const [tab, setTab] = useState('overview')
    const [trend] = useState(generateTrend)

    const loadStats = useCallback(() => {
        getDashboardStats()
            .then(d => setStats(d))
            .catch(() => setStats({
                total_claims: 0, approved: 0, flagged: 0, pending: 0, rejected: 0,
                total_payout: 0, avg_fraud_score: 0, avg_claim_amount: 0,
            }))
            .finally(() => setLoading(false))
    }, [])

    const loadClaims = useCallback(() => {
        setClaimsLoading(true)
        getClaims({ status: statusFilter || undefined, page, pageSize: 15 })
            .then(d => {
                setClaims(d.items || [])
                setPagination({ total: d.total, totalPages: d.total_pages })
            })
            .catch(() => setClaims([]))
            .finally(() => setClaimsLoading(false))
    }, [statusFilter, page])

    useEffect(() => { loadStats(); const id = setInterval(loadStats, 30000); return () => clearInterval(id) }, [loadStats])
    useEffect(() => { loadClaims() }, [loadClaims])

    const pieData = stats ? [
        { name: 'Approved', value: stats.approved },
        { name: 'Flagged', value: stats.flagged },
        { name: 'Pending', value: stats.pending },
        { name: 'Rejected', value: stats.rejected },
    ] : []

    return (
        <div className="page">
            <div className="container">
                {/* Hero */}
                <div className="hero mb-8">
                    <div className="hero-content">
                        <div className="hero-tag">🤖 AI Dashboard · Live</div>
                        <h1>Claims Control Centre</h1>
                        <p>Real-time fraud monitoring, payout tracking, and claim management in one place.</p>
                    </div>
                </div>

                {/* Stat Cards */}
                <div className="stat-grid mb-8">
                    {loading
                        ? STAT_CONFIG.map(s => (
                            <div key={s.key} className="stat-card" style={{ animation: 'pulse 1.4s ease-in-out infinite' }}>
                                <div style={{ width: 44, height: 44, borderRadius: 8, background: 'var(--bg-secondary)', marginBottom: '1rem' }} />
                                <div style={{ width: '60%', height: 32, borderRadius: 6, background: 'var(--bg-secondary)' }} />
                            </div>
                        ))
                        : STAT_CONFIG.map(s => (
                            <StatCard key={s.key} stat={s.key} value={stats?.[s.key]} />
                        ))
                    }
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    {[['overview', '📊 Overview'], ['claims', '📋 Claims'], ['heatmap', '🌡️ Fraud Heatmap']].map(([t, label]) => (
                        <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-ghost'} btn-sm`}
                            onClick={() => setTab(t)}>{label}</button>
                    ))}
                    <button className="btn btn-ghost btn-sm" onClick={() => { loadStats(); loadClaims() }} style={{ marginLeft: 'auto' }}>
                        ↻ Refresh
                    </button>
                </div>

                {/* Overview Tab */}
                {tab === 'overview' && (
                    <div className="flex-col gap-6">
                        {/* Trend chart */}
                        <div className="card p-6">
                            <h3 style={{ marginBottom: '1.5rem', fontSize: '1rem' }}>Claims & Fraud Trend (Last 14 Days)</h3>
                            <ResponsiveContainer width="100%" height={260}>
                                <AreaChart data={trend}>
                                    <defs>
                                        <linearGradient id="gradClaims" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.4} />
                                            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="gradFraud" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.4} />
                                            <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                    <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                                    <Tooltip
                                        contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10 }}
                                        labelStyle={{ color: '#f1f5f9', fontWeight: 700 }}
                                        itemStyle={{ color: '#94a3b8' }}
                                    />
                                    <Area type="monotone" dataKey="claims" stroke="#3b82f6" fill="url(#gradClaims)" strokeWidth={2} name="Claims" />
                                    <Area type="monotone" dataKey="fraud" stroke="#f43f5e" fill="url(#gradFraud)" strokeWidth={2} name="Fraud Flags" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Pie + Quick stats */}
                        <div className="grid-2">
                            <div className="card p-6">
                                <h3 style={{ fontSize: '1rem', marginBottom: '1.5rem' }}>Claim Status Distribution</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <PieChart>
                                        <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                                            paddingAngle={3} dataKey="value">
                                            {pieData.map((_, i) => (
                                                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Legend
                                            iconType="circle"
                                            iconSize={8}
                                            wrapperStyle={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}
                                        />
                                        <Tooltip
                                            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10 }}
                                            itemStyle={{ color: '#94a3b8' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>

                            <div className="card p-6">
                                <h3 style={{ fontSize: '1rem', marginBottom: '1.5rem' }}>Payout Trend ($)</h3>
                                <ResponsiveContainer width="100%" height={220}>
                                    <LineChart data={trend}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                        <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} />
                                        <YAxis stroke="#64748b" tick={{ fontSize: 10 }}
                                            tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                                        <Tooltip
                                            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10 }}
                                            labelStyle={{ color: '#f1f5f9', fontWeight: 700 }}
                                            formatter={v => [`$${v.toLocaleString()}`, 'Payout']}
                                        />
                                        <Line type="monotone" dataKey="payout" stroke="#06b6d4" strokeWidth={2.5}
                                            dot={false} activeDot={{ r: 5, fill: '#06b6d4' }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                )}

                {/* Claims Tab */}
                {tab === 'claims' && (
                    <div className="card p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h3 style={{ fontSize: '1rem' }}>All Claims</h3>
                            <div className="flex gap-2">
                                {STATUS_FILTERS.map(f => (
                                    <button key={f.value}
                                        className={`btn btn-sm ${statusFilter === f.value ? 'btn-primary' : 'btn-ghost'}`}
                                        onClick={() => { setStatusFilter(f.value); setPage(1) }}>
                                        {f.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <ClaimsTable
                            items={claims}
                            loading={claimsLoading}
                            total={pagination.total}
                            page={page}
                            totalPages={pagination.totalPages}
                            onPageChange={setPage}
                        />
                    </div>
                )}

                {/* Heatmap Tab */}
                {tab === 'heatmap' && (
                    <div className="card p-6">
                        <FraudHeatmap />
                    </div>
                )}
            </div>
        </div>
    )
}
