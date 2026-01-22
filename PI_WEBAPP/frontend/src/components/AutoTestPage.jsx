/**
 * AutoTestPage.jsx
 * หน้าทดสอบระบบอัตโนมัติ
 * - แสดงสถานะ ESP32 และ Camera
 * - ปุ่มเริ่ม/หยุด Mission
 * - แสดง Live Camera Feed พร้อม Detection
 * - แสดง Log การทำงาน
 */

import { useState, useEffect, useRef } from 'react';
import {
    Play, Square, RefreshCw, AlertTriangle, CheckCircle2, XCircle,
    Camera, Cpu, Activity, Zap, Target, ArrowDown, ArrowUp,
    MoveHorizontal, Droplets, TestTube2
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function AutoTestPage({ onBack }) {
    const [status, setStatus] = useState(null);
    const [isRunning, setIsRunning] = useState(false);
    const [logs, setLogs] = useState([]);
    const [message, setMessage] = useState(null);
    const [loading, setLoading] = useState(true);
    const logEndRef = useRef(null);

    // Fetch status every second
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/status`);
                if (res.ok) {
                    const data = await res.json();
                    setStatus(data);
                    setIsRunning(data.state === 'Moving' || data.state === 'Spraying');
                }
            } catch (err) {
                console.error('Failed to fetch status:', err);
            }
            setLoading(false);
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 1000);
        return () => clearInterval(interval);
    }, []);

    // Fetch logs
    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/logs?limit=20`);
                if (res.ok) {
                    const data = await res.json();
                    setLogs(data.logs || []);
                }
            } catch (err) {
                console.error('Failed to fetch logs:', err);
            }
        };

        fetchLogs();
        const interval = setInterval(fetchLogs, 2000);
        return () => clearInterval(interval);
    }, []);

    // Auto scroll logs
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleStart = async () => {
        if (!confirm('⚠️ หุ่นยนต์จะเริ่มเคลื่อนที่อัตโนมัติ\n\nตรวจสอบให้แน่ใจว่า:\n1. พื้นที่รอบหุ่นยนต์ปลอดภัย\n2. มีคนดูแลอยู่ใกล้ๆ\n3. มีปุ่มหยุดฉุกเฉินพร้อมใช้งาน\n\nต้องการเริ่มหรือไม่?')) {
            return;
        }

        setMessage({ type: 'info', text: '🚀 กำลังเริ่ม Mission...' });

        try {
            const res = await fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'start' })
            });
            const data = await res.json();

            if (data.success) {
                setMessage({ type: 'success', text: '✅ Mission เริ่มแล้ว!' });
                setIsRunning(true);
            } else {
                setMessage({ type: 'error', text: `❌ ${data.message || 'ไม่สามารถเริ่ม Mission ได้'}` });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }
    };

    const handleStop = async () => {
        setMessage({ type: 'info', text: '🛑 กำลังหยุด...' });

        try {
            const res = await fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'stop' })
            });
            const data = await res.json();

            if (data.success) {
                setMessage({ type: 'success', text: '✅ Mission หยุดแล้ว' });
                setIsRunning(false);
            } else {
                setMessage({ type: 'error', text: '❌ หยุดไม่สำเร็จ' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }
    };

    // ส่งคำสั่งทดสอบแขนกล
    const sendArmCommand = async (cmd, label) => {
        setMessage({ type: 'info', text: `⏳ กำลังทำ ${label}...` });

        try {
            const res = await fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await res.json();

            if (data.success) {
                setMessage({ type: 'success', text: data.message || `✅ ${label} สำเร็จ` });
            } else {
                setMessage({ type: 'error', text: data.message || `❌ ${label} ล้มเหลว` });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }
    };

    const StatusBadge = ({ ok, label }) => (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${ok ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
            {ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            <span className="text-sm font-medium">{label}</span>
        </div>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500
                          flex items-center justify-center shadow-lg shadow-green-500/30">
                        <Zap className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">ทดสอบระบบอัตโนมัติ</h2>
                        <p className="text-sm text-gray-400">เริ่มและติดตามการทำงานอัตโนมัติ</p>
                    </div>
                </div>

                <button
                    onClick={onBack}
                    className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
                >
                    ← กลับ
                </button>
            </div>

            {/* Safety Warning */}
            <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl text-yellow-400">
                <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                <div>
                    <strong>คำเตือนความปลอดภัย:</strong> ระบบอัตโนมัติจะทำให้หุ่นยนต์เคลื่อนที่ได้เอง
                    กรุณาตรวจสอบพื้นที่และเตรียมหยุดฉุกเฉินไว้เสมอ
                </div>
            </div>

            {/* Status Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatusBadge ok={status?.esp32_connected !== false} label="ESP32" />
                <StatusBadge ok={status?.camera_connected !== false} label="Camera" />
                <StatusBadge ok={isRunning} label={isRunning ? 'กำลังทำงาน' : 'หยุดอยู่'} />
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-500/20 text-primary-400">
                    <Target className="w-4 h-4" />
                    <span className="text-sm font-medium">พ่นแล้ว: {status?.spray_count || 0}</span>
                </div>
            </div>

            {/* Control Buttons */}
            <div className="flex gap-4 justify-center">
                {!isRunning ? (
                    <button
                        onClick={handleStart}
                        className="flex items-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500
                       text-white font-bold text-lg shadow-lg shadow-green-500/30 hover:shadow-green-500/50
                       transition-all hover:scale-105"
                    >
                        <Play className="w-6 h-6" />
                        เริ่ม Mission
                    </button>
                ) : (
                    <button
                        onClick={handleStop}
                        className="flex items-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-red-500 to-rose-500
                       text-white font-bold text-lg shadow-lg shadow-red-500/30 hover:shadow-red-500/50
                       transition-all hover:scale-105 animate-pulse"
                    >
                        <Square className="w-6 h-6" />
                        หยุด Mission
                    </button>
                )}
            </div>

            {/* Arm Test Section */}
            <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
                <div className="flex items-center gap-2 mb-4">
                    <TestTube2 className="w-5 h-5 text-orange-400" />
                    <h3 className="font-semibold text-white">ทดสอบแขนกล</h3>
                    <span className="text-xs text-gray-400 ml-2">(ไม่ทำให้ล้อเคลื่อนที่)</span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {/* Full Test */}
                    <button
                        onClick={() => sendArmCommand('arm_test', 'ทดสอบแขนกลครบ')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 
                                   border border-orange-500/30 text-orange-400 hover:bg-orange-500/30 transition-all"
                    >
                        <TestTube2 className="w-6 h-6" />
                        <span className="text-sm font-medium">ทดสอบครบ</span>
                        <span className="text-xs text-gray-500">ยื่น→ลง→พ่น→ขึ้น→หด</span>
                    </button>

                    {/* Arm Extend */}
                    <button
                        onClick={() => sendArmCommand('arm_extend', 'ยืดแขน')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-700/50 
                                   border border-gray-600 text-cyan-400 hover:bg-gray-700 transition-all"
                    >
                        <MoveHorizontal className="w-6 h-6" />
                        <span className="text-sm">ยืดแขน</span>
                    </button>

                    {/* Arm Retract */}
                    <button
                        onClick={() => sendArmCommand('arm_retract', 'หดแขน')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-700/50 
                                   border border-gray-600 text-cyan-400 hover:bg-gray-700 transition-all"
                    >
                        <MoveHorizontal className="w-6 h-6 rotate-180" />
                        <span className="text-sm">หดแขน</span>
                    </button>

                    {/* Head Down */}
                    <button
                        onClick={() => sendArmCommand('head_down', 'หัวลง')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-700/50 
                                   border border-gray-600 text-purple-400 hover:bg-gray-700 transition-all"
                    >
                        <ArrowDown className="w-6 h-6" />
                        <span className="text-sm">หัวลง</span>
                    </button>

                    {/* Head Up */}
                    <button
                        onClick={() => sendArmCommand('head_up', 'หัวขึ้น')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-700/50 
                                   border border-gray-600 text-purple-400 hover:bg-gray-700 transition-all"
                    >
                        <ArrowUp className="w-6 h-6" />
                        <span className="text-sm">หัวขึ้น</span>
                    </button>

                    {/* Spray */}
                    <button
                        onClick={() => sendArmCommand('spray', 'พ่นน้ำ')}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-700/50 
                                   border border-gray-600 text-blue-400 hover:bg-gray-700 transition-all"
                    >
                        <Droplets className="w-6 h-6" />
                        <span className="text-sm">พ่นน้ำ</span>
                    </button>
                </div>
            </div>

            {/* Message */}
            {message && (
                <div className={`p-4 rounded-xl text-center ${message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                    message.type === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/30' :
                        'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                    }`}>
                    {message.text}
                </div>
            )}

            {/* Camera & Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Camera Feed */}
                <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 overflow-hidden">
                    <div className="p-4 border-b border-gray-700/50 flex items-center gap-2">
                        <Camera className="w-5 h-5 text-cyan-400" />
                        <h3 className="font-semibold text-white">กล้อง Live</h3>
                    </div>
                    <div className="aspect-video bg-gray-900">
                        <img
                            src={`${API_BASE}/api/camera`}
                            alt="Camera Feed"
                            className="w-full h-full object-contain"
                            onError={(e) => {
                                e.target.style.display = 'none';
                            }}
                        />
                    </div>
                </div>

                {/* Live Logs */}
                <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 overflow-hidden">
                    <div className="p-4 border-b border-gray-700/50 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-purple-400" />
                        <h3 className="font-semibold text-white">Log การทำงาน</h3>
                    </div>
                    <div className="h-64 overflow-y-auto p-4 space-y-2 font-mono text-sm">
                        {logs.length === 0 ? (
                            <p className="text-gray-500 text-center">ยังไม่มี log</p>
                        ) : (
                            logs.map((log, i) => (
                                <div key={i} className={`p-2 rounded ${log.event?.includes('ERROR') ? 'bg-red-500/10 text-red-400' :
                                    log.event?.includes('SPRAY') ? 'bg-green-500/10 text-green-400' :
                                        log.event?.includes('START') ? 'bg-blue-500/10 text-blue-400' :
                                            'bg-gray-700/50 text-gray-400'
                                    }`}>
                                    <span className="text-gray-500 text-xs">
                                        {new Date(log.timestamp).toLocaleTimeString('th-TH')}
                                    </span>
                                    <span className="ml-2">{log.event}</span>
                                    {log.details && <span className="text-gray-500 ml-2">- {log.details}</span>}
                                </div>
                            ))
                        )}
                        <div ref={logEndRef} />
                    </div>
                </div>
            </div>

            {/* Current State */}
            <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div>
                        <div className="text-3xl font-bold text-primary-400">{status?.weed_count || 0}</div>
                        <div className="text-gray-400 text-sm">หญ้าที่พบ</div>
                    </div>
                    <div>
                        <div className="text-3xl font-bold text-green-400">{status?.spray_count || 0}</div>
                        <div className="text-gray-400 text-sm">พ่นแล้ว</div>
                    </div>
                    <div>
                        <div className="text-3xl font-bold text-cyan-400">{(status?.distance_traveled || 0).toFixed(1)}</div>
                        <div className="text-gray-400 text-sm">ระยะทาง (m)</div>
                    </div>
                    <div>
                        <div className="text-2xl font-bold text-white">{status?.state || 'Unknown'}</div>
                        <div className="text-gray-400 text-sm">สถานะ</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
