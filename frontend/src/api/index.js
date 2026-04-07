import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '',
    timeout: 60000,
})

// ── Claims ────────────────────────────────────────────────────────────────────

export async function submitClaim(formData) {
    const response = await api.post('/api/submit-claim', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
}

export async function checkFraud(claimId) {
    const response = await api.post('/api/check-fraud', { claim_id: claimId })
    return response.data
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function getDashboardStats() {
    const response = await api.get('/admin/dashboard')
    return response.data
}

export async function getClaims({ status, page = 1, pageSize = 20 } = {}) {
    const params = { page, page_size: pageSize }
    if (status) params.status = status
    const response = await api.get('/admin/claims', { params })
    return response.data
}

export async function getFraudHeatmap() {
    const response = await api.get('/admin/heatmap')
    return response.data
}

export default api
