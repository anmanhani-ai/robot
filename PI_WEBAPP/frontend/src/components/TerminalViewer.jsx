/**
 * TerminalViewer Component
 * แสดง Terminal Output จาก Robot แบบ Real-time
 * แสดงการคำนวณ คำสั่ง และสถานะต่างๆ
 */

import { Terminal, Trash2, RefreshCw } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';

// Log type colors
const logTypeColors = {
    info: 'text-gray-300',
    success: 'text-green-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
    calc: 'text-cyan-400',
    cmd: 'text-purple-400',
};

const logTypePrefix = {
    info: '📋',
    success: '✅',
    warning: '⚠️',
    error: '❌',
    calc: '📏',
    cmd: '🤖',
};

export default function TerminalViewer({ maxHeight = '300px' }) {
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(true);
    const [autoScroll, setAutoScroll] = useState(true);
    const scrollRef = useRef(null);

    // Fetch logs from API
    const fetchLogs = useCallback(async () => {
        try {
            const response = await fetch('/api/terminal?limit=50');
            if (response.ok) {
                const data = await response.json();
                setLogs(data);
                setIsConnected(true);
            }
        } catch (err) {
            console.error('Failed to fetch terminal logs:', err);
            setIsConnected(false);
        }
    }, []);

    // Clear logs
    const clearLogs = async () => {
        try {
            await fetch('/api/terminal', { method: 'DELETE' });
            setLogs([]);
        } catch (err) {
            console.error('Failed to clear logs:', err);
        }
    };

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    // Polling effect
    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 500); // Poll every 500ms
        return () => clearInterval(interval);
    }, [fetchLogs]);

    return (
        <div className="glass-dark p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-green-400" />
                    Terminal Output
                    {!isConnected && (
                        <span className="text-xs text-red-400">(Disconnected)</span>
                    )}
                </h2>

                <div className="flex items-center gap-2">
                    {/* Auto-scroll toggle */}
                    <button
                        onClick={() => setAutoScroll(!autoScroll)}
                        className={`text-xs px-2 py-1 rounded ${autoScroll
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-gray-700 text-gray-400'
                            }`}
                        title={autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
                    >
                        Auto ↓
                    </button>

                    {/* Refresh button */}
                    <button
                        onClick={fetchLogs}
                        className="p-1 rounded hover:bg-gray-700 text-gray-400"
                        title="Refresh"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>

                    {/* Clear button */}
                    <button
                        onClick={clearLogs}
                        className="p-1 rounded hover:bg-gray-700 text-gray-400"
                        title="Clear"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Terminal content */}
            <div
                ref={scrollRef}
                className="bg-gray-900 rounded-lg p-3 font-mono text-xs overflow-y-auto"
                style={{ maxHeight }}
            >
                {logs.length === 0 ? (
                    <div className="text-gray-500 text-center py-4">
                        <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>รอข้อมูลจาก Robot...</p>
                        <p className="text-xs mt-1">กด "เริ่ม Mission" เพื่อดูการทำงาน</p>
                    </div>
                ) : (
                    logs.map((log, index) => (
                        <div
                            key={index}
                            className={`flex gap-2 py-0.5 ${logTypeColors[log.type] || 'text-gray-300'}`}
                        >
                            <span className="text-gray-500 select-none">[{log.timestamp}]</span>
                            <span className="select-none">{logTypePrefix[log.type] || '📋'}</span>
                            <span className="flex-1">{log.message}</span>
                        </div>
                    ))
                )}
            </div>

            {/* Status bar */}
            <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                <span>{logs.length} logs</span>
                <span className="flex items-center gap-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
                    {isConnected ? 'Connected' : 'Disconnected'}
                </span>
            </div>
        </div>
    );
}
