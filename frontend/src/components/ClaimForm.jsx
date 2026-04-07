import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { submitClaim } from '../api'
import toast from 'react-hot-toast'

const CLAIM_TYPES = [
    { value: 'health', label: '🏥 Health', desc: 'Medical expenses, hospital bills' },
    { value: 'auto', label: '🚗 Auto', desc: 'Vehicle damage, accidents' },
    { value: 'property', label: '🏠 Property', desc: 'Home, rental, commercial property' },
    { value: 'life', label: '💙 Life', desc: 'Life insurance payout' },
    { value: 'travel', label: '✈️ Travel', desc: 'Trip cancellation, luggage loss' },
]

const STEPS = ['Your Info', 'Claim Details', 'Upload Docs', 'Review']

const AI_STEPS = [
    { icon: '🔍', name: 'OCR Extraction', desc: 'Reading your documents with AI…' },
    { icon: '🛡️', name: 'Fraud Analysis', desc: 'Running XGBoost + anomaly detection…' },
    { icon: '📷', name: 'Image Validation', desc: 'Verifying damage evidence…' },
    { icon: '💰', name: 'Payout Estimation', desc: 'Comparing with historical claim data…' },
    { icon: '⚖️', name: 'Final Decision', desc: 'Computing auto-settlement eligibility…' },
]

function StepIndicator({ current }) {
    return (
        <div className="steps mb-8">
            {STEPS.map((label, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                    <div className={`step ${i < current ? 'done' : i === current ? 'active' : ''}`}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div className="step-bubble">
                            {i < current ? '✓' : i + 1}
                        </div>
                        <span className="step-label">{label}</span>
                    </div>
                    {i < STEPS.length - 1 && (
                        <div style={{
                            flex: 1, height: '1px', margin: '0 0.5rem',
                            background: i < current ? 'var(--accent-emerald)' : 'var(--border)',
                            transition: 'background 0.3s'
                        }} />
                    )}
                </div>
            ))}
        </div>
    )
}

function ProcessingView({ step: currentStep }) {
    return (
        <div className="loading-screen">
            <div style={{ position: 'relative' }}>
                <div className="spinner" style={{ width: 60, height: 60 }} />
                <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.5rem'
                }}>🤖</div>
            </div>
            <div>
                <div className="loading-title">AI Pipeline Running</div>
                <div className="loading-sub">Please wait while we analyse your claim…</div>
            </div>
            <div className="ai-steps" style={{ width: '100%', maxWidth: 440 }}>
                {AI_STEPS.map((s, i) => (
                    <div key={i} className={`ai-step ${i < currentStep ? 'done' : i === currentStep ? 'processing' : ''}`}>
                        <div className="ai-step-icon">{s.icon}</div>
                        <div className="ai-step-text">
                            <div className="ai-step-name">{s.name}</div>
                            <div className="ai-step-desc">{i <= currentStep ? s.desc : '—'}</div>
                        </div>
                        <div className="ai-step-status">
                            {i < currentStep && <span className="text-emerald">✓</span>}
                            {i === currentStep && <span className="text-blue">⟳</span>}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

function ResultView({ result, onReset }) {
    const approved = result.status === 'approved'
    const fs = result.ai_scores

    return (
        <div className={`card p-8 animate-fade-up ${approved ? 'result-approved' : 'result-flagged'}`}
            style={{ textAlign: 'center' }}>
            <div className="result-icon">{approved ? '✅' : '🔴'}</div>
            <h2 style={{ marginBottom: '0.5rem' }}>
                {approved ? 'Claim Auto-Approved!' : 'Flagged for Manual Review'}
            </h2>
            <p style={{ marginBottom: '1.5rem' }}>{result.decision_reason}</p>

            {approved && (
                <div style={{
                    background: 'rgba(16,185,129,0.15)',
                    border: '1px solid rgba(16,185,129,0.3)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1rem 1.5rem',
                    marginBottom: '1.5rem',
                    display: 'inline-block',
                }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                        Settled Amount
                    </div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                        ${(result.settled_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                </div>
            )}

            <div className="score-bar" style={{ marginBottom: '2rem', textAlign: 'left' }}>
                <div className="score-row">
                    <span className="score-label">Fraud Score</span>
                    <div className="score-track">
                        <div className="score-fill-fraud" style={{ width: `${fs.fraud_score * 100}%` }} />
                    </div>
                    <span className="score-value">{(fs.fraud_score * 100).toFixed(0)}%</span>
                </div>
                <div className="score-row">
                    <span className="score-label">Payout Match</span>
                    <div className="score-track">
                        <div className="score-fill-payout" style={{ width: `${fs.payout_match_pct * 100}%` }} />
                    </div>
                    <span className="score-value">{(fs.payout_match_pct * 100).toFixed(0)}%</span>
                </div>
                <div className="score-row">
                    <span className="score-label">Est. Fair Payout</span>
                    <div className="score-track">
                        <div className="score-fill-image" style={{ width: '70%' }} />
                    </div>
                    <span className="score-value">${(fs.estimated_payout || 0).toLocaleString()}</span>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button className="btn btn-outline" onClick={onReset}>Submit Another Claim</button>
                {!approved && (
                    <div className="badge badge-pending">Claim ID: {String(result.claim_id).slice(0, 8)}…</div>
                )}
            </div>
        </div>
    )
}

export default function ClaimForm() {
    const [step, setStep] = useState(0)
    const [processing, setProcessing] = useState(false)
    const [aiStep, setAiStep] = useState(0)
    const [result, setResult] = useState(null)
    const [files, setFiles] = useState([])

    const [form, setForm] = useState({
        full_name: '', email: '', phone: '', policy_number: '',
        claim_type: '', description: '', requested_amount: '', incident_date: '',
    })

    const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        accept: { 'image/*': [], 'application/pdf': [] },
        maxSize: 10 * 1024 * 1024,
        onDrop: useCallback(accepted => setFiles(f => [...f, ...accepted].slice(0, 5)), []),
    })

    const removeFile = (i) => setFiles(f => f.filter((_, idx) => idx !== i))

    const handleSubmit = async () => {
        setProcessing(true)
        setAiStep(0)

        // Simulate AI step progression
        const ticker = setInterval(() => {
            setAiStep(s => {
                if (s >= AI_STEPS.length - 1) { clearInterval(ticker); return s; }
                return s + 1
            })
        }, 1200)

        try {
            const fd = new FormData()
            Object.entries(form).forEach(([k, v]) => fd.append(k, v))
            files.forEach(f => fd.append('files', f))
            const res = await submitClaim(fd)
            clearInterval(ticker)
            setAiStep(AI_STEPS.length)
            setResult(res)
        } catch (err) {
            clearInterval(ticker)
            toast.error(err?.response?.data?.detail || 'Submission failed. Please try again.')
            setProcessing(false)
        }
    }

    const reset = () => {
        setStep(0); setAiStep(0); setResult(null); setFiles([])
        setProcessing(false)
        setForm({ full_name: '', email: '', phone: '', policy_number: '', claim_type: '', description: '', requested_amount: '', incident_date: '' })
    }

    if (result) return (
        <div className="page">
            <div className="container" style={{ maxWidth: 680 }}>
                <ResultView result={result} onReset={reset} />
            </div>
        </div>
    )

    if (processing) return (
        <div className="page">
            <div className="container" style={{ maxWidth: 560 }}>
                <div className="card">
                    <ProcessingView step={aiStep} />
                </div>
            </div>
        </div>
    )

    return (
        <div className="page">
            <div className="container" style={{ maxWidth: 720 }}>
                {/* Header */}
                <div className="mb-8" style={{ textAlign: 'center' }}>
                    <div className="hero-tag" style={{
                        display: 'inline-flex', margin: '0 auto 1rem',
                        background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)',
                        borderRadius: 100, padding: '0.35rem 0.9rem', fontSize: '0.8rem', fontWeight: 600, gap: '0.4rem',
                    }}>
                        ⚡ AI-Powered Settlement in Minutes
                    </div>
                    <h1 style={{ marginBottom: '0.5rem' }}>File Your Claim</h1>
                    <p>Complete the steps below. Our AI pipeline will analyse your submission and decide in seconds.</p>
                </div>

                <div className="card p-8 animate-fade-up">
                    <StepIndicator current={step} />

                    {/* Progress */}
                    <div className="progress-track mb-8">
                        <div className="progress-fill" style={{ width: `${((step) / (STEPS.length - 1)) * 100}%` }} />
                    </div>

                    {/* ── Step 0: Your Info ── */}
                    {step === 0 && (
                        <div className="flex-col gap-4">
                            <div className="grid-2">
                                <div className="form-group">
                                    <label className="form-label">Full Name *</label>
                                    <input className="form-input" placeholder="John Doe"
                                        value={form.full_name} onChange={e => set('full_name', e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email *</label>
                                    <input className="form-input" type="email" placeholder="john@example.com"
                                        value={form.email} onChange={e => set('email', e.target.value)} />
                                </div>
                            </div>
                            <div className="grid-2">
                                <div className="form-group">
                                    <label className="form-label">Phone</label>
                                    <input className="form-input" placeholder="+1 (555) 000-0000"
                                        value={form.phone} onChange={e => set('phone', e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Policy Number</label>
                                    <input className="form-input" placeholder="POL-XXXXXXXX"
                                        value={form.policy_number} onChange={e => set('policy_number', e.target.value)} />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── Step 1: Claim Details ── */}
                    {step === 1 && (
                        <div className="flex-col gap-4">
                            <div className="form-group">
                                <label className="form-label">Claim Type *</label>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem' }}>
                                    {CLAIM_TYPES.map(ct => (
                                        <div key={ct.value}
                                            onClick={() => set('claim_type', ct.value)}
                                            style={{
                                                padding: '0.875rem 1rem',
                                                border: `2px solid ${form.claim_type === ct.value ? 'var(--accent-blue)' : 'var(--border)'}`,
                                                borderRadius: 'var(--radius-md)',
                                                cursor: 'pointer',
                                                background: form.claim_type === ct.value ? 'rgba(59,130,246,0.08)' : 'var(--bg-secondary)',
                                                transition: 'all 0.15s',
                                            }}>
                                            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>{ct.label}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ct.desc}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="grid-2">
                                <div className="form-group">
                                    <label className="form-label">Requested Amount ($) *</label>
                                    <input className="form-input" type="number" min="1" placeholder="5000"
                                        value={form.requested_amount} onChange={e => set('requested_amount', e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Incident Date</label>
                                    <input className="form-input" type="date"
                                        value={form.incident_date} onChange={e => set('incident_date', e.target.value)} />
                                </div>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Description of Incident *</label>
                                <textarea className="form-textarea" rows={5}
                                    placeholder="Describe what happened in detail — include date, location, and circumstances…"
                                    value={form.description} onChange={e => set('description', e.target.value)} />
                                <div className="text-xs text-muted mt-2">{form.description.length} / 5000 characters (min 20)</div>
                            </div>
                        </div>
                    )}

                    {/* ── Step 2: Upload Docs ── */}
                    {step === 2 && (
                        <div>
                            <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''} mb-4`}>
                                <input {...getInputProps()} />
                                <div className="dropzone-icon">📁</div>
                                <div className="dropzone-label">
                                    {isDragActive ? 'Drop files here…' : 'Drag & drop files, or click to browse'}
                                </div>
                                <div className="dropzone-hint">JPG, PNG, PDF up to 10 MB each · Max 5 files</div>
                            </div>

                            {files.length > 0 && (
                                <div className="file-list">
                                    {files.map((f, i) => (
                                        <div key={i} className="file-item">
                                            {f.type.startsWith('image/') ? (
                                                <img className="file-thumb" src={URL.createObjectURL(f)} alt="" />
                                            ) : (
                                                <div className="file-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem' }}>📄</div>
                                            )}
                                            <div className="flex-col gap-1" style={{ flex: 1, minWidth: 0 }}>
                                                <div className="file-name truncate">{f.name}</div>
                                                <div className="file-size">{(f.size / 1024).toFixed(1)} KB</div>
                                            </div>
                                            <button className="btn btn-ghost btn-sm" onClick={() => removeFile(i)}>✕</button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {files.length === 0 && (
                                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                                    ⚠️ Uploading damage photos improves auto-approval chances
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── Step 3: Review ── */}
                    {step === 3 && (
                        <div className="flex-col gap-4">
                            {[
                                { label: 'Name', value: form.full_name },
                                { label: 'Email', value: form.email },
                                { label: 'Phone', value: form.phone || '—' },
                                { label: 'Policy No.', value: form.policy_number || '—' },
                                { label: 'Claim Type', value: CLAIM_TYPES.find(c => c.value === form.claim_type)?.label || '—' },
                                { label: 'Amount', value: form.requested_amount ? `$${Number(form.requested_amount).toLocaleString()}` : '—' },
                                { label: 'Incident Date', value: form.incident_date || '—' },
                                { label: 'Files', value: files.length > 0 ? `${files.length} file(s)` : 'None' },
                            ].map(row => (
                                <div key={row.label} className="flex justify-between items-center" style={{
                                    padding: '0.75rem 0', borderBottom: '1px solid var(--border)'
                                }}>
                                    <span className="text-sm text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>{row.label}</span>
                                    <span className="text-sm font-bold">{row.value}</span>
                                </div>
                            ))}
                            <div style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '1rem', marginTop: '0.5rem' }}>
                                <div className="text-xs text-muted mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>Description</div>
                                <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>{form.description}</p>
                            </div>
                        </div>
                    )}

                    {/* Nav buttons */}
                    <div className="flex justify-between mt-8">
                        {step > 0
                            ? <button className="btn btn-ghost" onClick={() => setStep(s => s - 1)}>← Back</button>
                            : <span />
                        }
                        {step < STEPS.length - 1 ? (
                            <button className="btn btn-primary"
                                onClick={() => {
                                    if (step === 0 && (!form.full_name || !form.email)) { toast.error('Name and email are required.'); return }
                                    if (step === 1 && (!form.claim_type || !form.requested_amount || form.description.length < 20)) { toast.error('Fill all required fields (min 20 chars description).'); return }
                                    setStep(s => s + 1)
                                }}>
                                Next →
                            </button>
                        ) : (
                            <button className="btn btn-primary btn-lg animate-pulse-glow" onClick={handleSubmit}>
                                🚀 Submit & Analyse
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
