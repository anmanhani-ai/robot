/**
 * API Service
 * จัดการการเรียก API ไปยัง Backend
 */

const API_BASE = '/api';

// Camera stream URL - use full URL when in development
export const CAMERA_STREAM_URL = `${window.location.protocol}//${window.location.hostname}:8000/api/camera/stream`;

// Helper function for API calls
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }

        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ==================== API Functions ====================

/**
 * ดึงสถานะปัจจุบันของหุ่นยนต์
 */
export async function getStatus() {
    return fetchAPI('/status');
}

/**
 * ส่งคำสั่งไปยังหุ่นยนต์
 * @param {string} command - start, stop, reset
 */
export async function sendCommand(command) {
    return fetchAPI('/command', {
        method: 'POST',
        body: JSON.stringify({ command }),
    });
}

/**
 * ดึง log entries
 * @param {number} limit - จำนวน log ที่ต้องการ
 */
export async function getLogs(limit = 50) {
    return fetchAPI(`/logs?limit=${limit}`);
}

/**
 * Download report เป็น CSV
 */
export async function downloadReport() {
    const response = await fetch(`${API_BASE}/download`);

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error('No data to download');
        }
        throw new Error('Download failed');
    }

    // Get filename from header
    const contentDisposition = response.headers.get('content-disposition');
    const filenameMatch = contentDisposition?.match(/filename=(.+)/);
    const filename = filenameMatch ? filenameMatch[1] : 'report.csv';

    // Create blob and download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    return { success: true, filename };
}

/**
 * Reset report และ status
 */
export async function resetReport() {
    return fetchAPI('/reset', {
        method: 'POST',
    });
}
