/**
 * SettingsPage.jsx
 * หน้าตั้งค่าแขนกลและระบบ
 */

import { useState, useEffect } from 'react';
import { Settings, Save, RotateCcw, AlertTriangle, Ruler, ArrowUpDown, ArrowLeftRight, Power, Camera } from 'lucide-react';

export default function SettingsPage({ onBack }) {
    const [settings, setSettings] = useState({
        max_arm_extend_cm: 50.0,      // ความยาวแขน Z สูงสุด
        arm_base_offset_cm: 5.0,      // ระยะ offset ของแขน
        arm_speed_cm_per_sec: 10.0,   // ความเร็วแขน
        servo_y_angle_down: 90,       // มุม servo ลง
        servo_y_angle_up: 0,          // มุม servo ขึ้น
        default_spray_duration: 1.0,  // เวลาพ่นเริ่มต้น
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [rebooting, setRebooting] = useState(false);
    const [reconnecting, setReconnecting] = useState(false);
    const [message, setMessage] = useState(null);

    // โหลดค่าจาก backend
    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const data = await response.json();
                setSettings(prev => ({ ...prev, ...data }));
            }
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
        setLoading(false);
    };

    const saveSettings = async () => {
        setSaving(true);
        setMessage(null);

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                setMessage({ type: 'success', text: '✅ บันทึกการตั้งค่าสำเร็จ!' });
            } else {
                setMessage({ type: 'error', text: '❌ บันทึกไม่สำเร็จ' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }

        setSaving(false);
    };

    const resetDefaults = () => {
        setSettings({
            max_arm_extend_cm: 50.0,
            arm_base_offset_cm: 5.0,
            arm_speed_cm_per_sec: 10.0,
            servo_y_angle_down: 90,
            servo_y_angle_up: 0,
            default_spray_duration: 1.0,
        });
        setMessage({ type: 'info', text: '🔄 รีเซ็ตเป็นค่าเริ่มต้นแล้ว (ยังไม่ได้บันทึก)' });
    };

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
    };

    const rebootBackend = async () => {
        if (!confirm('ต้องการรีบูต Backend ใช่ไหม?\n\nหลังรีบูตหน้าจะโหลดใหม่ภายใน 5 วินาที')) {
            return;
        }

        setRebooting(true);
        setMessage({ type: 'info', text: 'กำลังรีบูต Backend...' });

        try {
            await fetch('/api/reboot', { method: 'POST' });
            setMessage({ type: 'success', text: '✅ กำลังรีบูต... รอ 5 วินาทีแล้วรีเฟรชหน้า' });

            // Reload page after 5 seconds
            setTimeout(() => {
                window.location.reload();
            }, 5000);
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถรีบูตได้' });
            setRebooting(false);
        }
    };

    if (loading) {
        return (
            <div className="glass-dark p-6 text-center text-gray-400">
                กำลังโหลดการตั้งค่า...
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="glass-dark p-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Settings className="w-6 h-6 text-primary-400" />
                        ตั้งค่าแขนกล
                    </h2>

                    {onBack && (
                        <button
                            onClick={onBack}
                            className="text-sm text-gray-400 hover:text-white"
                        >
                            ← กลับ
                        </button>
                    )}
                </div>

                <p className="text-gray-400 text-sm mt-2">
                    กำหนดขอบเขตการเคลื่อนที่ของแขนกลเพื่อป้องกันความเสียหาย
                </p>
            </div>

            {/* Warning */}
            <div className="flex items-center gap-2 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl text-yellow-400 text-sm">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <span>
                    <strong>สำคัญ:</strong> วัดความยาวแขนกลจริงก่อนใส่ค่า การตั้งค่าผิดอาจทำให้แขนกลเสียหาย
                </span>
            </div>

            {/* Arm Z Settings */}
            <div className="glass-dark p-6">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <ArrowLeftRight className="w-5 h-5 text-blue-400" />
                    แขน Z (ยืด/หด - แนวนอน)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            ความยาวสูงสุด (cm)
                        </label>
                        <input
                            type="number"
                            value={settings.max_arm_extend_cm}
                            onChange={(e) => handleChange('max_arm_extend_cm', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="0.1"
                            min="1"
                            max="100"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ระยะยืดสูงสุดจากตำแหน่งเริ่มต้น
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            Offset จากกล้อง (cm)
                        </label>
                        <input
                            type="number"
                            value={settings.arm_base_offset_cm}
                            onChange={(e) => handleChange('arm_base_offset_cm', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="0.1"
                            min="0"
                            max="50"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ระยะระหว่างกล้องกับฐานแขน
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            ความเร็วแขน (cm/s)
                        </label>
                        <input
                            type="number"
                            value={settings.arm_speed_cm_per_sec}
                            onChange={(e) => handleChange('arm_speed_cm_per_sec', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="0.5"
                            min="1"
                            max="50"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ใช้สำหรับคำนวณเวลายืด/หด
                        </p>
                    </div>
                </div>
            </div>

            {/* Arm Y Settings */}
            <div className="glass-dark p-6">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <ArrowUpDown className="w-5 h-5 text-cyan-400" />
                    แขน Y (ขึ้น/ลง - แนวตั้ง)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            มุม Servo ตำแหน่งบน (องศา)
                        </label>
                        <input
                            type="number"
                            value={settings.servo_y_angle_up}
                            onChange={(e) => handleChange('servo_y_angle_up', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="1"
                            min="0"
                            max="180"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ตำแหน่งพักของหัวฉีด
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            มุม Servo ตำแหน่งล่าง (องศา)
                        </label>
                        <input
                            type="number"
                            value={settings.servo_y_angle_down}
                            onChange={(e) => handleChange('servo_y_angle_down', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="1"
                            min="0"
                            max="180"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ตำแหน่งพ่นยา
                        </p>
                    </div>
                </div>
            </div>

            {/* Spray Settings */}
            <div className="glass-dark p-6">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <Ruler className="w-5 h-5 text-green-400" />
                    การพ่นยา
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">
                            เวลาพ่นเริ่มต้น (วินาที)
                        </label>
                        <input
                            type="number"
                            value={settings.default_spray_duration}
                            onChange={(e) => handleChange('default_spray_duration', e.target.value)}
                            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
                            step="0.1"
                            min="0.1"
                            max="10"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            ระยะเวลาพ่นต่อหนึ่งต้น
                        </p>
                    </div>
                </div>
            </div>

            {/* System Section */}
            <div className="glass-dark p-6">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                    <Power className="w-5 h-5 text-red-400" />
                    ระบบ
                </h3>

                <div className="flex gap-4 flex-wrap">
                    <button
                        onClick={rebootBackend}
                        disabled={rebooting}
                        className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 
                                 rounded-lg text-red-400 transition-colors flex items-center gap-2
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RotateCcw className={`w-4 h-4 ${rebooting ? 'animate-spin' : ''}`} />
                        {rebooting ? 'กำลังรีบูต...' : 'รีบูต Backend'}
                    </button>

                    <button
                        onClick={async () => {
                            setReconnecting(true);
                            setMessage({ type: 'info', text: 'กำลังเชื่อมต่อกล้องใหม่...' });
                            try {
                                const res = await fetch('/api/camera/reconnect', { method: 'POST' });
                                const data = await res.json();
                                if (data.success) {
                                    setMessage({ type: 'success', text: '✅ เชื่อมต่อกล้องสำเร็จ!' });
                                } else {
                                    setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อกล้องได้ - ลองถอด/เสียบสาย USB หรือรีบูต' });
                                }
                            } catch (err) {
                                setMessage({ type: 'error', text: '❌ เชื่อมต่อ server ไม่ได้' });
                            }
                            setReconnecting(false);
                        }}
                        disabled={reconnecting}
                        className="px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 
                                 rounded-lg text-blue-400 transition-colors flex items-center gap-2
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Camera className={`w-4 h-4 ${reconnecting ? 'animate-pulse' : ''}`} />
                        {reconnecting ? 'กำลังเชื่อมต่อ...' : 'เชื่อมต่อกล้องใหม่'}
                    </button>
                </div>

                <p className="text-xs text-gray-500 mt-2">
                    รีบูต server หรือเชื่อมต่อกล้องใหม่เมื่อมีปัญหา
                </p>
            </div>

            {/* Message */}
            {message && (
                <div className={`p-4 rounded-xl text-sm ${message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                    message.type === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/30' :
                        'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                    }`}>
                    {message.text}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-4">
                <button
                    onClick={saveSettings}
                    disabled={saving}
                    className="btn btn-primary flex-1"
                >
                    <Save className="w-5 h-5" />
                    {saving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า'}
                </button>

                <button
                    onClick={resetDefaults}
                    className="btn btn-outline"
                >
                    <RotateCcw className="w-5 h-5" />
                    รีเซ็ต
                </button>
            </div>
        </div>
    );
}
