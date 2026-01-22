/**
 * HealthCheckPage.jsx
 * หน้าตรวจสอบสุขภาพอุปกรณ์ทั้งหมด
 */

import { useState, useEffect, useCallback } from 'react';
import {
    Activity, Cpu, Camera, Cog, Droplets,
    Radio, CheckCircle2, AlertTriangle, XCircle,
    RefreshCw, ChevronLeft, Play, Wifi
} from 'lucide-react';

// API Base
const API_BASE = '/api';

// Device Icons
const deviceIcons = {
    esp32: Cpu,
    camera: Camera,
    motor_left: Cog,
    motor_right: Cog,
    motor_z: Cog,
    motor_y: Cog,
    pump: Droplets,
    ultrasonic_front: Radio,
    ultrasonic_y: Radio,
    ultrasonic_right: Radio,
};

// Device Labels
const deviceLabels = {
    esp32: 'ESP32 Controller',
    camera: 'กล้อง USB',
    motor_left: 'มอเตอร์ซ้าย',
    motor_right: 'มอเตอร์ขวา',
    motor_z: 'มอเตอร์ Z (ยืด/หด)',
    motor_y: 'มอเตอร์ Y (ขึ้น/ลง)',
    pump: 'ปั๊มพ่นยา',
    ultrasonic_front: 'Ultrasonic หน้า',
    ultrasonic_y: 'Ultrasonic แกน Y',
    ultrasonic_right: 'Ultrasonic ขวา',
};

// Testable devices
const testableDevices = ['motor_left', 'motor_right', 'motor_z', 'motor_y', 'pump'];

export default function HealthCheckPage({ onBack }) {
    const [healthData, setHealthData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [testingDevice, setTestingDevice] = useState(null);
    const [lastCheck, setLastCheck] = useState(null);

    // Fetch health status
    const fetchHealth = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE}/health`);
            const data = await response.json();
            setHealthData(data);
            setLastCheck(new Date());
        } catch (err) {
            console.error('Failed to fetch health:', err);
        }
        setIsLoading(false);
    }, []);

    // Test device
    const testDevice = async (device) => {
        setTestingDevice(device);
        try {
            const response = await fetch(`${API_BASE}/health/test/${device}`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                // Refresh health after test
                await fetchHealth();
            } else {
                alert(`ทดสอบล้มเหลว: ${data.error}`);
            }
        } catch (err) {
            alert(`เกิดข้อผิดพลาด: ${err.message}`);
        }
        setTestingDevice(null);
    };

    // Load on mount
    useEffect(() => {
        fetchHealth();
    }, [fetchHealth]);

    // Status color and icon
    const getStatusStyle = (status) => {
        switch (status) {
            case 'ok':
                return {
                    bg: 'bg-green-500/20',
                    border: 'border-green-500/50',
                    text: 'text-green-400',
                    icon: CheckCircle2,
                };
            case 'warning':
                return {
                    bg: 'bg-yellow-500/20',
                    border: 'border-yellow-500/50',
                    text: 'text-yellow-400',
                    icon: AlertTriangle,
                };
            case 'error':
            default:
                return {
                    bg: 'bg-red-500/20',
                    border: 'border-red-500/50',
                    text: 'text-red-400',
                    icon: XCircle,
                };
        }
    };

    // Device Card Component
    const DeviceCard = ({ deviceKey, deviceData }) => {
        const style = getStatusStyle(deviceData.status);
        const StatusIcon = style.icon;
        const DeviceIcon = deviceIcons[deviceKey] || Cog;
        const isTestable = testableDevices.includes(deviceKey);
        const isTesting = testingDevice === deviceKey;

        return (
            <div className={`${style.bg} ${style.border} border rounded-xl p-4 transition-all hover:scale-[1.02]`}>
                <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg ${style.bg} flex items-center justify-center`}>
                            <DeviceIcon className={`w-5 h-5 ${style.text}`} />
                        </div>
                        <div>
                            <h3 className="font-medium text-white text-sm">
                                {deviceLabels[deviceKey] || deviceKey}
                            </h3>
                            <p className={`text-xs ${style.text}`}>
                                {deviceData.message}
                            </p>
                        </div>
                    </div>
                    <StatusIcon className={`w-5 h-5 ${style.text}`} />
                </div>

                {/* Details */}
                {deviceData.details && (
                    <div className="text-xs text-gray-400 mb-2">
                        {deviceData.details.suggestion && (
                            <p className="text-yellow-400">💡 {deviceData.details.suggestion}</p>
                        )}
                        {deviceData.details.latency_ms && (
                            <p>⏱️ Latency: {deviceData.details.latency_ms}ms</p>
                        )}
                    </div>
                )}

                {/* Test Button */}
                {isTestable && (
                    <button
                        onClick={() => testDevice(deviceKey)}
                        disabled={isTesting || deviceData.status === 'error'}
                        className={`w-full mt-2 py-2 rounded-lg text-xs font-medium transition-all
              flex items-center justify-center gap-2
              ${deviceData.status === 'error'
                                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                                : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white'
                            }
              ${isTesting ? 'opacity-50' : ''}
            `}
                    >
                        {isTesting ? (
                            <>
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                กำลังทดสอบ...
                            </>
                        ) : (
                            <>
                                <Play className="w-3 h-3" />
                                ทดสอบ
                            </>
                        )}
                    </button>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500
                          flex items-center justify-center shadow-lg shadow-purple-500/30">
                        <Activity className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Health Check</h2>
                        <p className="text-sm text-gray-400">ตรวจสอบสถานะอุปกรณ์</p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {/* Refresh Button */}
                    <button
                        onClick={fetchHealth}
                        disabled={isLoading}
                        className={`px-4 py-2 rounded-lg bg-gray-700 text-gray-300 
                       hover:bg-gray-600 transition-colors flex items-center gap-2
                       ${isLoading ? 'opacity-50' : ''}`}
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                        ตรวจสอบใหม่
                    </button>

                    {/* Back Button */}
                    <button
                        onClick={onBack}
                        className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 
                       hover:bg-gray-600 transition-colors flex items-center gap-2"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        กลับ
                    </button>
                </div>
            </div>

            {/* Summary */}
            {healthData && (
                <div className={`p-4 rounded-xl border ${healthData.all_ok
                        ? 'bg-green-500/10 border-green-500/30'
                        : healthData.summary.error > 0
                            ? 'bg-red-500/10 border-red-500/30'
                            : 'bg-yellow-500/10 border-yellow-500/30'
                    }`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {healthData.all_ok ? (
                                <CheckCircle2 className="w-6 h-6 text-green-400" />
                            ) : healthData.summary.error > 0 ? (
                                <XCircle className="w-6 h-6 text-red-400" />
                            ) : (
                                <AlertTriangle className="w-6 h-6 text-yellow-400" />
                            )}
                            <div>
                                <p className={`font-medium ${healthData.all_ok ? 'text-green-400' :
                                        healthData.summary.error > 0 ? 'text-red-400' : 'text-yellow-400'
                                    }`}>
                                    {healthData.all_ok
                                        ? '✅ อุปกรณ์ทั้งหมดพร้อมใช้งาน'
                                        : healthData.summary.error > 0
                                            ? `❌ มี ${healthData.summary.error} อุปกรณ์ที่มีปัญหา`
                                            : `⚠️ มี ${healthData.summary.warning} อุปกรณ์ที่ต้องตรวจสอบ`
                                    }
                                </p>
                                <p className="text-xs text-gray-400">
                                    ✅ {healthData.summary.ok} |
                                    ⚠️ {healthData.summary.warning} |
                                    ❌ {healthData.summary.error}
                                </p>
                            </div>
                        </div>
                        {lastCheck && (
                            <p className="text-xs text-gray-500">
                                ตรวจสอบล่าสุด: {lastCheck.toLocaleTimeString('th-TH')}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Loading State */}
            {isLoading && !healthData && (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            )}

            {/* Device Grid */}
            {healthData && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(healthData.devices).map(([key, data]) => (
                        <DeviceCard key={key} deviceKey={key} deviceData={data} />
                    ))}
                </div>
            )}

            {/* Help Section */}
            <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-4">
                <h3 className="font-medium text-white mb-2 flex items-center gap-2">
                    <Wifi className="w-4 h-4 text-blue-400" />
                    คำแนะนำการแก้ไข
                </h3>
                <ul className="text-sm text-gray-400 space-y-1">
                    <li>• <strong className="text-red-400">ESP32 ไม่เชื่อมต่อ</strong>: ตรวจสอบสาย USB และ port /dev/ttyUSB0</li>
                    <li>• <strong className="text-red-400">กล้องไม่พบ</strong>: ตรวจสอบการเชื่อมต่อ USB กล้อง</li>
                    <li>• <strong className="text-yellow-400">Ultrasonic = 0</strong>: ตรวจสอบการต่อสาย TRIG/ECHO</li>
                    <li>• <strong className="text-yellow-400">Motor ทำงานพร้อมกัน</strong>: ตรวจสอบการต่อ IN1-IN4 ให้ถูกต้อง</li>
                </ul>
            </div>
        </div>
    );
}
