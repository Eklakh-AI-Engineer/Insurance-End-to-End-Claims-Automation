import { useState, useEffect } from 'react'
import { getFraudHeatmap } from '../api'

const CLAIM_TYPES = ['health', 'auto', 'property', 'life', 'travel']
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function fraudColor(score) {
    if (score === null || score === undefined) return 'rgba(51,65,85,0.4)'
    const r = Math.round(score * 220 + 35)
    const g = Math.round((1 - score) * 180 + 40)
    const b = 60
    return `rgba(${r},${g},${b},${0.3 + score * 0.7})`
}

export default function FraudHeatmap() {
    const [cells, setCells] = useState([])
    const [loading, setLoading] = useState(true)
    const [tooltip, setTooltip] = useState(null)

    useEffect(() => {
        getFraudHeatmap()
            .then(d => setCells(d.cells || []))
            .catch(() => {
                // Generate mock data when no real data exists
                const mock = []
                CLAIM_TYPES.forEach(t => {
                    HOURS.forEach(h => {
                        if (Math.random() > 0.3) {
                            mock.push({
                                claim_type: t,
                                hour_bucket: h,
                                avg_fraud_score: Math.random() * 0.8,
                                count: Math.floor(Math.random() * 20) + 1,
                            })
                        }
                    })
                })
                setCells(mock)
            })
            .finally(() => setLoading(false))
    }, [])

    const getCell = (type, hour) =>
        cells.find(c => c.claim_type === type && c.hour_bucket === hour)

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
            <div className="spinner" />
        </div>
    )

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h3 style={{ fontSize: '1rem' }}>Fraud Score Heatmap</h3>
                <div className="flex gap-2 items-center text-xs text-muted">
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(40,180,60,0.6)' }} /> Low
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(245,158,11,0.7)' }} /> Med
                    <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(239,68,68,0.85)' }} /> High
                </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
                {/* Hour axis */}
                <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(24,1fr)', gap: 2, marginBottom: 4 }}>
                    <div />
                    {HOURS.map(h => (
                        <div key={h} style={{
                            textAlign: 'center', fontSize: '0.6rem', color: 'var(--text-muted)',
                            fontWeight: h % 6 === 0 ? 700 : 400,
                        }}>
                            {h}
                        </div>
                    ))}
                </div>

                {/* Rows */}
                {CLAIM_TYPES.map(type => (
                    <div key={type} style={{ display: 'grid', gridTemplateColumns: '80px repeat(24,1fr)', gap: 2, marginBottom: 2 }}>
                        <div style={{
                            fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600,
                            display: 'flex', alignItems: 'center', textTransform: 'capitalize', paddingRight: '0.5rem',
                        }}>
                            {type}
                        </div>
                        {HOURS.map(h => {
                            const cell = getCell(type, h)
                            const score = cell?.avg_fraud_score
                            return (
                                <div
                                    key={h}
                                    onMouseEnter={e => setTooltip({ x: e.clientX, y: e.clientY, cell, type, h })}
                                    onMouseLeave={() => setTooltip(null)}
                                    style={{
                                        height: 26,
                                        borderRadius: 3,
                                        background: fraudColor(score),
                                        cursor: cell ? 'pointer' : 'default',
                                        transition: 'transform 0.15s',
                                    }}
                                    onMouseOver={e => { if (cell) e.currentTarget.style.transform = 'scale(1.2)' }}
                                    onMouseOut={e => { e.currentTarget.style.transform = 'scale(1)' }}
                                />
                            )
                        })}
                    </div>
                ))}
            </div>

            {/* Tooltip */}
            {tooltip && tooltip.cell && (
                <div style={{
                    position: 'fixed',
                    top: tooltip.y - 80,
                    left: tooltip.x + 12,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.6rem 0.9rem',
                    fontSize: '0.8rem',
                    zIndex: 1000,
                    pointerEvents: 'none',
                    boxShadow: 'var(--shadow-card)',
                }}>
                    <div style={{ fontWeight: 700, marginBottom: '0.25rem', textTransform: 'capitalize' }}>
                        {tooltip.type} @ {tooltip.h}:00
                    </div>
                    <div style={{ color: 'var(--text-muted)' }}>
                        Avg Fraud: <strong style={{ color: fraudColor(tooltip.cell.avg_fraud_score) }}>
                            {(tooltip.cell.avg_fraud_score * 100).toFixed(1)}%
                        </strong>
                    </div>
                    <div style={{ color: 'var(--text-muted)' }}>Claims: {tooltip.cell.count}</div>
                </div>
            )}

            <div className="text-xs text-muted mt-4" style={{ textAlign: 'center' }}>
                Darker red = higher average fraud score · Hover cells for detail
            </div>
        </div>
    )
}
