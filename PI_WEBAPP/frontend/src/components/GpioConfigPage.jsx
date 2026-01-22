/**
 * GpioConfigPage.jsx
 * หน้าตั้งค่า GPIO Configuration
 * 
 * สลับ pins ได้โดยไม่ต้อง upload code ใหม่
 */

import { useState, useEffect, useCallback } from 'react';
import {
    Cpu, Settings, RefreshCw, ChevronLeft,
    ArrowLeftRight, RotateCcw, AlertTriangle, CheckCircle2
} from 'lucide-react';

const API_BASE = '/api';

// GPIO Groups
const gpioGroups = [
    {
        id: 'motor_yz',
        name: 'Motor Y ↔ Motor Z',
        description: 'สลับ pins ระหว่าง Motor Y (ขึ้น/ลง) และ Motor Z (ยืด/หด)',
        color: 'blue',
    },
    {
        id: 'wheels',
        name: 'ล้อซ้าย ↔ ล้อขวา',
        description: 'สลับ pins ระหว่างล้อซ้ายและล้อขวา',
        color: 'green',
    },
];

export default function GpioConfigPage({ onBack }) {
    const [config, setConfig] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [swapping, setSwapping] = useState(null);
    const [message, setMessage] = useState(null);

    // Fetch GPIO config
    const fetchConfig = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE}/gpio`);
            const data = await response.json();
            if (data.success) {
                setConfig(data.config);
            } else {
                setMessage({ type: 'error', text: data.error });
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'ไม่สามารถโหลด config ได้' });
        }
        setIsLoading(false);
    }, []);

    // Swap pins
    const swapPins = async (groupId) => {
        setSwapping(groupId);
        setMessage(null);
        try {
            const response = await fetch(`${API_BASE}/gpio/swap/${groupId}`, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                setMessage({ type: 'success', text: data.message + ' - ' + data.note });
                await fetchConfig();
            } else {
                setMessage({ type: 'error', text: data.error });
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'เกิดข้อผิดพลาด' });
        }
        setSwapping(null);
    };

    // Reset config
    const resetConfig = async () => {
        if (!confirm('ต้องการ reset GPIO config เป็นค่าเริ่มต้น?')) return;

        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE}/gpio/reset`, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                setMessage({ type: 'success', text: data.message });
                await fetchConfig();
            } else {
                setMessage({ type: 'error', text: data.error });
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'เกิดข้อผิดพลาด' });
        }
        setIsLoading(false);
    };

    useEffect(() => {
        fetchConfig();
    }, [fetchConfig]);

    // Pin display component
    const PinBox = ({ label, pin1, pin2, pin1Label, pin2Label }) => (
        <div className="bg-gray-700/50 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-2">{label}</p>
            <div className="flex gap-2">
                <div className="flex-1 bg-gray-800 rounded px-2 py-1 text-center">
                    <span className="text-xs text-gray-500">{pin1Label}: </span>
                    <span className="text-sm font-mono text-white">GPIO {pin1}</span>
                </div>
                <div className="flex-1 bg-gray-800 rounded px-2 py-1 text-center">
                    <span className="text-xs text-gray-500">{pin2Label}: </span>
                    <span className="text-sm font-mono text-white">GPIO {pin2}</span>
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500
                          flex items-center justify-center shadow-lg shadow-orange-500/30">
                        <Cpu className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">GPIO Configuration</h2>
                        <p className="text-sm text-gray-400">ตั้งค่า pins โดยไม่ต้อง upload code</p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={fetchConfig}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 
                       hover:bg-gray-600 transition-colors flex items-center gap-2"
                    >
                        <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                        รีเฟรช
                    </button>
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

            {/* Message */}
            {message && (
                <div className={`p-4 rounded-xl border flex items-center gap-3 ${message.type === 'success'
                        ? 'bg-green-500/10 border-green-500/30 text-green-400'
                        : 'bg-red-500/10 border-red-500/30 text-red-400'
                    }`}>
                    {message.type === 'success' ? (
                        <CheckCircle2 className="w-5 h-5" />
                    ) : (
                        <AlertTriangle className="w-5 h-5" />
                    )}
                    {message.text}
                </div>
            )}

            {/* Loading */}
            {isLoading && !config && (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
            )}

            {/* Current Config Display */}
            {config && (
                <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 p-4">
                    <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                        <Settings className="w-5 h-5 text-gray-400" />
                        ค่า GPIO ปัจจุบัน
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <PinBox
                            label="Motor Y (ขึ้น/ลง)"
                            pin1={config.motor_y?.pin1}
                            pin2={config.motor_y?.pin2}
                            pin1Label="IN1"
                            pin2Label="IN2"
                        />
                        <PinBox
                            label="Motor Z (ยืด/หด)"
                            pin1={config.motor_z?.pin1}
                            pin2={config.motor_z?.pin2}
                            pin1Label="IN3"
                            pin2Label="IN4"
                        />
                        <PinBox
                            label="ล้อซ้าย"
                            pin1={config.wheel_l?.pin1}
                            pin2={config.wheel_l?.pin2}
                            pin1Label="IN1"
                            pin2Label="IN2"
                        />
                        <PinBox
                            label="ล้อขวา"
                            pin1={config.wheel_r?.pin1}
                            pin2={config.wheel_r?.pin2}
                            pin1Label="IN3"
                            pin2Label="IN4"
                        />
                    </div>
                </div>
            )}

            {/* Swap Buttons */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {gpioGroups.map((group) => (
                    <div
                        key={group.id}
                        className={`bg-${group.color}-500/10 border border-${group.color}-500/30 
                        rounded-xl p-4`}
                    >
                        <h3 className="font-medium text-white mb-2">{group.name}</h3>
                        <p className="text-sm text-gray-400 mb-4">{group.description}</p>

                        <button
                            onClick={() => swapPins(group.id)}
                            disabled={swapping === group.id}
                            className={`w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2
                         transition-all ${swapping === group.id ? 'opacity-50' : ''}
                         bg-${group.color}-500/20 text-${group.color}-400 
                         hover:bg-${group.color}-500 hover:text-white`}
                        >
                            {swapping === group.id ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    กำลังสลับ...
                                </>
                            ) : (
                                <>
                                    <ArrowLeftRight className="w-4 h-4" />
                                    สลับ Pins
                                </>
                            )}
                        </button>
                    </div>
                ))}
            </div>

            {/* Reset Button */}
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="font-medium text-white">Reset เป็นค่าเริ่มต้น</h3>
                        <p className="text-sm text-gray-400">กลับไปใช้ค่า default ทั้งหมด</p>
                    </div>
                    <button
                        onClick={resetConfig}
                        className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 
                       hover:bg-red-500 hover:text-white transition-all
                       flex items-center gap-2"
                    >
                        <RotateCcw className="w-4 h-4" />
                        Reset
                    </button>
                </div>
            </div>

            {/* Note */}
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-yellow-400">
                        <p className="font-medium mb-1">หมายเหตุ</p>
                        <ul className="list-disc list-inside text-yellow-400/80 space-y-1">
                            <li>หลังสลับ pins ต้อง <strong>restart ESP32</strong> เพื่อให้มีผล</li>
                            <li>ค่าที่ตั้งจะบันทึกใน EEPROM และคงอยู่หลัง reboot</li>
                            <li>ถ้าต่อสายผิด ให้กด "สลับ" แทนการต่อสายใหม่</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}
