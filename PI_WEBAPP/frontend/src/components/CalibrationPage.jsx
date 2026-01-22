/**
 * CalibrationPage.jsx
 * หน้า Calibration พร้อมระบบ Wizard ช่วย calibrate กล้องและแขนกล
 */

import { useState, useEffect, useRef } from 'react';
import {
    Focus, Camera, Ruler, CheckCircle, AlertTriangle, RefreshCw,
    ChevronLeft, ChevronRight, Play, Target, Move, ArrowRight, Crosshair
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Step indicator component
const StepIndicator = ({ steps, currentStep, onStepClick }) => (
    <div className="flex items-center justify-center gap-2 mb-6">
        {steps.map((step, index) => (
            <div key={index} className="flex items-center">
                <button
                    onClick={() => onStepClick && onStepClick(index)}
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all
                        ${index === currentStep
                            ? 'bg-primary-500 text-white scale-110 shadow-lg shadow-primary-500/50'
                            : index < currentStep
                                ? 'bg-green-500 text-white'
                                : 'bg-gray-700 text-gray-400'}`}
                >
                    {index < currentStep ? '✓' : index + 1}
                </button>
                {index < steps.length - 1 && (
                    <div className={`w-12 h-1 mx-1 rounded ${index < currentStep ? 'bg-green-500' : 'bg-gray-700'}`} />
                )}
            </div>
        ))}
    </div>
);

// Calibration step components
const Step1CameraSetup = ({ settings, onUpdate, onCapture, capturedImage }) => (
    <div className="space-y-4">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Camera className="w-6 h-6 text-blue-400" />
            ขั้นตอนที่ 1: ตั้งค่ากล้อง
        </h3>
        <p className="text-gray-400">
            ป้อนข้อมูลตำแหน่งและมุมกล้องของคุณ
        </p>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">ความสูงกล้อง (cm)</label>
                <input
                    type="number"
                    value={settings.camera_height_cm}
                    onChange={(e) => onUpdate('camera_height_cm', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="10" max="200"
                />
                <p className="text-xs text-gray-500 mt-1">วัดจากพื้นงานถึงกล้อง</p>
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">มุมกล้อง (องศา)</label>
                <input
                    type="number"
                    value={settings.camera_angle_deg}
                    onChange={(e) => onUpdate('camera_angle_deg', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="0" max="90"
                />
                <p className="text-xs text-gray-500 mt-1">0° = มองตรง, 90° = มองลง</p>
            </div>
        </div>

        {/* Camera preview */}
        <div className="mt-4">
            <div className="aspect-video bg-gray-900 rounded-xl overflow-hidden relative">
                {capturedImage ? (
                    <img src={capturedImage} alt="Captured" className="w-full h-full object-contain" />
                ) : (
                    <img
                        src={`${API_BASE}/api/camera/stream`}
                        alt="Camera Live"
                        className="w-full h-full object-contain"
                        onError={(e) => {
                            // Fallback to snapshot if stream fails
                            e.target.src = `${API_BASE}/api/camera/snapshot?t=${Date.now()}`;
                        }}
                    />
                )}

                {/* Crosshair overlay */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <Crosshair className="w-20 h-20 text-primary-500/50" />
                </div>
            </div>
            <button
                onClick={onCapture}
                className="mt-2 w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center justify-center gap-2"
            >
                <Camera className="w-5 h-5" />
                ถ่ายภาพทดสอบ
            </button>
        </div>
    </div>
);

const Step2MeasureDistance = ({ settings, onUpdate, onMeasure, measuring }) => (
    <div className="space-y-4">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Ruler className="w-6 h-6 text-yellow-400" />
            ขั้นตอนที่ 2: วัดระยะ Pixel-to-CM
        </h3>
        <p className="text-gray-400">
            วางวัตถุที่ทราบขนาดไว้หน้ากล้อง แล้วป้อนข้อมูล
        </p>

        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-yellow-300 text-sm">
            <strong>📏 วิธีวัด:</strong>
            <ol className="list-decimal ml-4 mt-2 space-y-1">
                <li>วางไม้บรรทัดหรือกระดาษ A4 (กว้าง 21 cm) หน้ากล้อง</li>
                <li>หมายเลขพิกเซลในภาพ (หรือใช้ Detection)</li>
                <li>ป้อนขนาดจริง (cm) และขนาดพิกเซลที่วัดได้</li>
            </ol>
        </div>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">ขนาดจริง (cm)</label>
                <input
                    type="number"
                    value={settings.known_size_cm || 21}
                    onChange={(e) => onUpdate('known_size_cm', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="1" max="100"
                />
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">ขนาดในภาพ (pixels)</label>
                <input
                    type="number"
                    value={settings.known_size_px || 600}
                    onChange={(e) => onUpdate('known_size_px', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="1" max="2000"
                />
            </div>
        </div>

        <button
            onClick={onMeasure}
            disabled={measuring}
            className="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-600 text-black font-bold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
        >
            {measuring ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Target className="w-5 h-5" />}
            {measuring ? 'กำลังคำนวณ...' : 'คำนวณอัตราส่วน Pixel-to-CM'}
        </button>

        {settings.pixel_to_cm_ratio > 0 && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-green-400">
                <strong>✅ ผลลัพธ์:</strong>
                <p className="mt-1">1 pixel = <strong>{settings.pixel_to_cm_ratio.toFixed(4)}</strong> cm</p>
            </div>
        )}
    </div>
);

const Step3ArmCalibration = ({ settings, onUpdate, onTestArm, testing }) => (
    <div className="space-y-4">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Move className="w-6 h-6 text-cyan-400" />
            ขั้นตอนที่ 3: Calibrate แขนกล
        </h3>
        <p className="text-gray-400">
            ป้อนข้อมูลความยาวและความเร็วของแขนกล
        </p>

        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4 text-cyan-300 text-sm">
            <strong>🔧 วิธีวัด:</strong>
            <ol className="list-decimal ml-4 mt-2 space-y-1">
                <li>กดยืดแขนจนสุด แล้ววัดความยาวที่ยืดได้ (cm)</li>
                <li>จับเวลาว่าใช้เวลากี่วินาที</li>
                <li>คำนวณความเร็ว: ความยาว ÷ เวลา = cm/s</li>
            </ol>
        </div>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">ความยาวแขนสูงสุด (cm)</label>
                <input
                    type="number"
                    value={settings.max_arm_extend_cm}
                    onChange={(e) => onUpdate('max_arm_extend_cm', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="1" max="100" step="0.1"
                />
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">เวลายืดเต็มที่ (วินาที)</label>
                <input
                    type="number"
                    value={settings.arm_extend_time || 7}
                    onChange={(e) => onUpdate('arm_extend_time', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="0.5" max="30" step="0.1"
                />
            </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">ระยะกล้องถึงฐานแขน (cm)</label>
                <input
                    type="number"
                    value={settings.arm_base_offset_cm}
                    onChange={(e) => onUpdate('arm_base_offset_cm', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
                    min="0" max="50" step="0.1"
                />
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">ความเร็วคำนวณ (cm/s)</label>
                <input
                    type="number"
                    value={settings.arm_speed_cm_per_sec}
                    readOnly
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-green-400 font-mono"
                />
            </div>
        </div>

        <button
            onClick={onTestArm}
            disabled={testing}
            className="w-full px-4 py-3 bg-cyan-500 hover:bg-cyan-600 text-black font-bold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
        >
            {testing ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
            {testing ? 'กำลังทดสอบ...' : 'ทดสอบแขนกล'}
        </button>
    </div>
);

const Step4YAxisCalibration = ({ settings, onUpdate, onTestY, testing }) => (
    <div className="space-y-4">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <ArrowRight className="w-6 h-6 text-purple-400" />
            ขั้นตอนที่ 4: ตั้งค่าหัวพ่น Y-axis
        </h3>
        <p className="text-gray-400">
            ตั้งค่าเวลายก/ลง หัวพ่นยา (วินาที)
        </p>

        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 text-purple-300 text-sm">
            <strong>💡 วิธีใช้:</strong> ตั้งค่าเวลาที่ต้องการให้หัวพ่นยกขึ้น/ลง แล้วกดทดสอบ
        </div>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">⬆️ เวลายกขึ้น (วินาที)</label>
                <input
                    type="number"
                    value={settings.y_up_duration || 3}
                    onChange={(e) => onUpdate('y_up_duration', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center text-lg font-mono focus:border-primary-500 focus:outline-none"
                    min="0.5" max="30" step="0.5"
                />
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">⬇️ เวลาลง (วินาที)</label>
                <input
                    type="number"
                    value={settings.y_down_duration || 3}
                    onChange={(e) => onUpdate('y_down_duration', parseFloat(e.target.value) || 0)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center text-lg font-mono focus:border-primary-500 focus:outline-none"
                    min="0.5" max="30" step="0.5"
                />
            </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
            <button
                onClick={() => onTestY('up')}
                disabled={testing}
                className="py-4 px-4 rounded-xl font-bold text-lg bg-gradient-to-r from-purple-500 to-violet-500 hover:from-purple-600 hover:to-violet-600 text-white flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg"
            >
                ⬆️ ยกขึ้น {settings.y_up_duration || 3}s
            </button>
            <button
                onClick={() => onTestY('down')}
                disabled={testing}
                className="py-4 px-4 rounded-xl font-bold text-lg bg-gradient-to-r from-purple-500 to-violet-500 hover:from-purple-600 hover:to-violet-600 text-white flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg"
            >
                ⬇️ ลง {settings.y_down_duration || 3}s
            </button>
        </div>
    </div>
);

const Step5Review = ({ settings, onSave, saving }) => (
    <div className="space-y-4">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <CheckCircle className="w-6 h-6 text-green-400" />
            ขั้นตอนที่ 4: ตรวจสอบและบันทึก
        </h3>
        <p className="text-gray-400">
            ตรวจสอบค่าที่ calibrate แล้วบันทึก
        </p>

        <div className="bg-gray-800 rounded-xl p-4 space-y-3">
            <h4 className="text-white font-semibold border-b border-gray-700 pb-2">📷 Camera Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
                <span className="text-gray-400">ความสูงกล้อง:</span>
                <span className="text-white font-mono">{settings.camera_height_cm} cm</span>
                <span className="text-gray-400">มุมกล้อง:</span>
                <span className="text-white font-mono">{settings.camera_angle_deg}°</span>
                <span className="text-gray-400">Pixel-to-CM:</span>
                <span className="text-white font-mono">{settings.pixel_to_cm_ratio?.toFixed(4) || 'N/A'} cm/px</span>
            </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-4 space-y-3">
            <h4 className="text-white font-semibold border-b border-gray-700 pb-2">🤖 Arm Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
                <span className="text-gray-400">ความยาวแขน:</span>
                <span className="text-white font-mono">{settings.max_arm_extend_cm} cm</span>
                <span className="text-gray-400">ความเร็วแขน:</span>
                <span className="text-white font-mono">{settings.arm_speed_cm_per_sec} cm/s</span>
                <span className="text-gray-400">Offset กล้อง:</span>
                <span className="text-white font-mono">{settings.arm_base_offset_cm} cm</span>
            </div>
        </div>

        <button
            onClick={onSave}
            disabled={saving}
            className="w-full px-4 py-4 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 
                     text-white font-bold text-lg rounded-xl flex items-center justify-center gap-2 
                     shadow-lg shadow-green-500/30 disabled:opacity-50"
        >
            {saving ? <RefreshCw className="w-6 h-6 animate-spin" /> : <CheckCircle className="w-6 h-6" />}
            {saving ? 'กำลังบันทึก...' : '💾 บันทึก Calibration'}
        </button>
    </div>
);

export default function CalibrationPage({ onBack }) {
    const [currentStep, setCurrentStep] = useState(0);
    const [settings, setSettings] = useState({
        camera_height_cm: 50,
        camera_angle_deg: 45,
        pixel_to_cm_ratio: 0.05,
        known_size_cm: 21,
        known_size_px: 420,
        max_arm_extend_cm: 16.3,
        arm_extend_time: 7.5,
        arm_base_offset_cm: 8.5,
        arm_speed_cm_per_sec: 2.17,
        y_up_duration: 3,
        y_down_duration: 3,
    });
    const [capturedImage, setCapturedImage] = useState(null);
    const [measuring, setMeasuring] = useState(false);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    const steps = ['กล้อง', 'Pixel-CM', 'แขน Z', 'หัวพ่น Y', 'บันทึก'];

    // Load existing settings
    useEffect(() => {
        loadSettings();
    }, []);

    // Auto-calculate arm speed when inputs change
    useEffect(() => {
        if (settings.max_arm_extend_cm > 0 && settings.arm_extend_time > 0) {
            const speed = settings.max_arm_extend_cm / settings.arm_extend_time;
            setSettings(prev => ({ ...prev, arm_speed_cm_per_sec: parseFloat(speed.toFixed(2)) }));
        }
    }, [settings.max_arm_extend_cm, settings.arm_extend_time]);

    const loadSettings = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/settings`);
            if (res.ok) {
                const data = await res.json();
                setSettings(prev => ({ ...prev, ...data }));
            }
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
    };

    const updateSetting = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const captureImage = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/camera/snapshot`);
            if (res.ok) {
                const blob = await res.blob();
                setCapturedImage(URL.createObjectURL(blob));
                setMessage({ type: 'success', text: '✅ ถ่ายภาพสำเร็จ!' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ถ่ายภาพไม่สำเร็จ' });
        }
    };

    const measurePixelToCm = () => {
        setMeasuring(true);
        setTimeout(() => {
            const ratio = settings.known_size_cm / settings.known_size_px;
            setSettings(prev => ({ ...prev, pixel_to_cm_ratio: ratio }));
            setMeasuring(false);
            setMessage({ type: 'success', text: `✅ คำนวณสำเร็จ: 1px = ${ratio.toFixed(4)}cm` });
        }, 1000);
    };

    const testArm = async () => {
        setTesting(true);
        setMessage({ type: 'info', text: '🔄 กำลังทดสอบแขนกล...' });

        try {
            const res = await fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'arm_test' })
            });
            const data = await res.json();

            if (data.success) {
                setMessage({ type: 'success', text: '✅ ทดสอบแขนกลสำเร็จ!' });
            } else {
                setMessage({ type: 'error', text: `❌ ${data.message}` });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อได้' });
        }

        setTesting(false);
    };

    const testYAxis = async (direction) => {
        setTesting(true);
        const duration = direction === 'up'
            ? (settings.y_up_duration || 3)
            : (settings.y_down_duration || 3);
        const dirText = direction === 'up' ? 'ยกขึ้น' : 'วางลง';
        setMessage({ type: 'info', text: `🔄 กำลังทดสอบหัวพ่น ${dirText} ${duration} วินาที...` });

        try {
            const cmd = direction === 'up' ? `Y_UP:${duration}` : `Y_DOWN:${duration}`;
            const res = await fetch(`${API_BASE}/api/manual`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd, params: {} })
            });
            const data = await res.json();

            if (data.success) {
                setMessage({ type: 'success', text: `✅ ทดสอบหัวพ่น ${dirText} ${duration} วินาที สำเร็จ!` });
            } else {
                setMessage({ type: 'error', text: `❌ ${data.message}` });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อได้' });
        }

        setTesting(false);
    };

    const saveCalibration = async () => {
        setSaving(true);

        try {
            const res = await fetch(`${API_BASE}/api/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            if (res.ok) {
                setMessage({ type: 'success', text: '✅ บันทึก Calibration สำเร็จ!' });
            } else {
                setMessage({ type: 'error', text: '❌ บันทึกไม่สำเร็จ' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }

        setSaving(false);
    };

    const nextStep = () => setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
    const prevStep = () => setCurrentStep(prev => Math.max(prev - 1, 0));

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="glass-dark p-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Focus className="w-6 h-6 text-primary-400" />
                        🎯 Calibration Wizard
                    </h2>
                    {onBack && (
                        <button onClick={onBack} className="text-sm text-gray-400 hover:text-white">
                            ← กลับ
                        </button>
                    )}
                </div>
                <p className="text-gray-400 text-sm mt-1">
                    ช่วยตั้งค่า Camera และ Arm ให้ทำงานได้แม่นยำ
                </p>
            </div>

            {/* Step Indicator */}
            <StepIndicator steps={steps} currentStep={currentStep} onStepClick={setCurrentStep} />

            {/* Step Content */}
            <div className="glass-dark p-6">
                {currentStep === 0 && (
                    <Step1CameraSetup
                        settings={settings}
                        onUpdate={updateSetting}
                        onCapture={captureImage}
                        capturedImage={capturedImage}
                    />
                )}
                {currentStep === 1 && (
                    <Step2MeasureDistance
                        settings={settings}
                        onUpdate={updateSetting}
                        onMeasure={measurePixelToCm}
                        measuring={measuring}
                    />
                )}
                {currentStep === 2 && (
                    <Step3ArmCalibration
                        settings={settings}
                        onUpdate={updateSetting}
                        onTestArm={testArm}
                        testing={testing}
                    />
                )}
                {currentStep === 3 && (
                    <Step4YAxisCalibration
                        settings={settings}
                        onUpdate={updateSetting}
                        onTestY={testYAxis}
                        testing={testing}
                    />
                )}
                {currentStep === 4 && (
                    <Step5Review
                        settings={settings}
                        onSave={saveCalibration}
                        saving={saving}
                    />
                )}
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

            {/* Navigation Buttons */}
            <div className="flex gap-4">
                {currentStep > 0 && (
                    <button
                        onClick={prevStep}
                        className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl flex items-center justify-center gap-2"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        ย้อนกลับ
                    </button>
                )}

                {/* Quick Save Button - แสดงในทุกขั้นตอน */}
                <button
                    onClick={saveCalibration}
                    disabled={saving}
                    className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 
                             text-white font-bold rounded-xl flex items-center justify-center gap-2 
                             shadow-lg shadow-green-500/30 disabled:opacity-50"
                >
                    {saving ? <RefreshCw className="w-5 h-5 animate-spin" /> : <CheckCircle className="w-5 h-5" />}
                    {saving ? 'กำลังบันทึก...' : '💾 Save'}
                </button>

                {currentStep < steps.length - 1 && (
                    <button
                        onClick={nextStep}
                        className="flex-1 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-xl flex items-center justify-center gap-2"
                    >
                        ถัดไป
                        <ChevronRight className="w-5 h-5" />
                    </button>
                )}
            </div>
        </div>
    );
}
