/**
 * SettingsPage.jsx
 * หน้าตั้งค่าแขนกลและระบบ - Advanced Version
 * รองรับ: Arm Config, Motion Control, Camera Calibration, Safety, PID Tuning
 */

import { useState, useEffect } from 'react';
import {
    Settings, Save, RotateCcw, AlertTriangle, Ruler, ArrowUpDown, ArrowLeftRight,
    Power, Camera, Zap, Shield, Sliders, Eye, Target, Gauge, ChevronDown, ChevronUp
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Collapsible Section Component
const Section = ({ title, icon: Icon, color, children, defaultOpen = true }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className="glass-dark rounded-xl overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
            >
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <Icon className={`w-5 h-5 ${color}`} />
                    {title}
                </h3>
                {isOpen ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
            </button>
            {isOpen && <div className="p-4 pt-0 border-t border-gray-700/50">{children}</div>}
        </div>
    );
};

// Input Field Component
const InputField = ({ label, description, value, onChange, step = 0.1, min, max, unit = '' }) => (
    <div>
        <label className="block text-sm text-gray-400 mb-1">{label}</label>
        <div className="flex items-center gap-2">
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 
                         rounded-lg text-white focus:border-primary-500 focus:outline-none"
                step={step}
                min={min}
                max={max}
            />
            {unit && <span className="text-gray-500 text-sm w-12">{unit}</span>}
        </div>
        {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
    </div>
);

// Slider Field Component
const SliderField = ({ label, value, onChange, min = 0, max = 100, unit = '%' }) => (
    <div>
        <div className="flex justify-between mb-1">
            <label className="text-sm text-gray-400">{label}</label>
            <span className="text-sm text-primary-400">{value}{unit}</span>
        </div>
        <input
            type="range"
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            min={min}
            max={max}
        />
    </div>
);

// Toggle Field Component
const ToggleField = ({ label, description, value, onChange }) => (
    <div className="flex items-center justify-between py-2">
        <div>
            <span className="text-white text-sm">{label}</span>
            {description && <p className="text-xs text-gray-500">{description}</p>}
        </div>
        <button
            onClick={() => onChange(!value)}
            className={`w-12 h-6 rounded-full transition-colors ${value ? 'bg-primary-500' : 'bg-gray-600'}`}
        >
            <div className={`w-5 h-5 bg-white rounded-full transition-transform ${value ? 'translate-x-6' : 'translate-x-0.5'}`} />
        </button>
    </div>
);

// Select Field Component
const SelectField = ({ label, value, onChange, options }) => (
    <div>
        <label className="block text-sm text-gray-400 mb-1">{label}</label>
        <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 
                     rounded-lg text-white focus:border-primary-500 focus:outline-none"
        >
            {options.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
        </select>
    </div>
);

export default function SettingsPage({ onBack }) {
    const [settings, setSettings] = useState({
        // === ARM CONFIGURATION ===
        arm_links: [15.5, 0, 0],  // ความยาวแต่ละข้อ [Z, Y, ...]
        joint_z_min: 0,
        joint_z_max: 15.5,
        joint_y_min: -90,
        joint_y_max: 90,

        // === SPEED & MOTION CONTROL ===
        max_speed_percent: 60,
        acceleration: 30,
        deceleration: 30,
        position_tolerance_cm: 0.5,
        angle_tolerance_deg: 2,
        retry_attempts: 3,

        // Legacy settings
        arm_speed_cm_per_sec: 2.21,
        arm_base_offset_cm: 9.0,
        max_arm_extend_cm: 15.5,
        arm_z_default_cm: 0.0,
        motor_y_speed_cm_per_sec: 5.0,
        motor_y_default_cm: 0.0,
        motor_y_max_cm: 20.0,

        // === CAMERA CALIBRATION ===
        camera_height_cm: 50.0,
        camera_angle_deg: 45.0,
        camera_fov_deg: 60.0,
        pixel_to_cm_ratio: 0.034,
        workspace_x_min: -30,
        workspace_x_max: 30,
        workspace_y_min: -30,
        workspace_y_max: 30,
        workspace_z_min: 0,
        workspace_z_max: 20,

        // === MOTION PLANNING ===
        motion_type: 'direct',
        approach_height_cm: 5.0,
        approach_speed_percent: 50,
        retreat_height_cm: 5.0,

        // === CONTROL MODES ===
        operation_mode: 'auto',
        control_method: 'inverse_kinematics',

        // === SAFETY SETTINGS ===
        emergency_stop_enabled: true,
        collision_detection_enabled: false,
        timeout_seconds: 30,

        // Error handling
        on_target_lost: 'stop',
        on_unreachable: 'alert',

        // === PID TUNING ===
        pid_kp: 2.0,
        pid_ki: 0.1,
        pid_kd: 0.05,
        moving_average_window: 5,
        kalman_filter_enabled: false,

        // === SPRAY SETTINGS ===
        default_spray_duration: 1.0,
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [rebooting, setRebooting] = useState(false);
    const [reconnecting, setReconnecting] = useState(false);
    const [message, setMessage] = useState(null);
    const [activeTab, setActiveTab] = useState('basic');

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/settings`);
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
            const response = await fetch(`${API_BASE}/api/settings`, {
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
        if (!confirm('รีเซ็ตค่าทั้งหมดเป็นค่าเริ่มต้น?')) return;

        setSettings({
            arm_links: [15.5, 0, 0],
            joint_z_min: 0,
            joint_z_max: 15.5,
            joint_y_min: -90,
            joint_y_max: 90,
            max_speed_percent: 60,
            acceleration: 30,
            deceleration: 30,
            position_tolerance_cm: 0.5,
            angle_tolerance_deg: 2,
            retry_attempts: 3,
            arm_speed_cm_per_sec: 2.21,
            arm_base_offset_cm: 9.0,
            max_arm_extend_cm: 15.5,
            arm_z_default_cm: 0.0,
            motor_y_speed_cm_per_sec: 5.0,
            motor_y_default_cm: 0.0,
            motor_y_max_cm: 20.0,
            camera_height_cm: 50.0,
            camera_angle_deg: 45.0,
            camera_fov_deg: 60.0,
            pixel_to_cm_ratio: 0.034,
            workspace_x_min: -30,
            workspace_x_max: 30,
            workspace_y_min: -30,
            workspace_y_max: 30,
            workspace_z_min: 0,
            workspace_z_max: 20,
            motion_type: 'direct',
            approach_height_cm: 5.0,
            approach_speed_percent: 50,
            retreat_height_cm: 5.0,
            operation_mode: 'auto',
            control_method: 'inverse_kinematics',
            emergency_stop_enabled: true,
            collision_detection_enabled: false,
            timeout_seconds: 30,
            on_target_lost: 'stop',
            on_unreachable: 'alert',
            pid_kp: 2.0,
            pid_ki: 0.1,
            pid_kd: 0.05,
            moving_average_window: 5,
            kalman_filter_enabled: false,
            default_spray_duration: 1.0,
        });
        setMessage({ type: 'info', text: '🔄 รีเซ็ตเป็นค่าเริ่มต้นแล้ว (ยังไม่ได้บันทึก)' });
    };

    const update = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const rebootBackend = async () => {
        if (!confirm('ต้องการรีบูต Backend ใช่ไหม?\n\nหลังรีบูตหน้าจะโหลดใหม่ภายใน 5 วินาที')) {
            return;
        }

        setRebooting(true);
        setMessage({ type: 'info', text: 'กำลังรีบูต Backend...' });

        try {
            await fetch(`${API_BASE}/api/reboot`, { method: 'POST' });
            setMessage({ type: 'success', text: '✅ กำลังรีบูต... รอ 5 วินาทีแล้วรีเฟรชหน้า' });
            setTimeout(() => window.location.reload(), 5000);
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
        <div className="space-y-4">
            {/* Header */}
            <div className="glass-dark p-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Settings className="w-6 h-6 text-primary-400" />
                        ตั้งค่าแขนกล
                    </h2>
                    {onBack && (
                        <button onClick={onBack} className="text-sm text-gray-400 hover:text-white">
                            ← กลับ
                        </button>
                    )}
                </div>

                {/* Tab Navigation */}
                <div className="flex gap-2 mt-4 overflow-x-auto">
                    {[
                        { id: 'basic', label: '📏 พื้นฐาน', icon: Ruler },
                        { id: 'motion', label: '⚡ การเคลื่อนที่', icon: Zap },
                        { id: 'camera', label: '📷 กล้อง', icon: Camera },
                        { id: 'safety', label: '🛡️ ความปลอดภัย', icon: Shield },
                        { id: 'advanced', label: '🔧 ขั้นสูง', icon: Sliders },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm transition-colors ${activeTab === tab.id
                                    ? 'bg-primary-500 text-white'
                                    : 'bg-gray-800 text-gray-400 hover:text-white'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Warning */}
            <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl text-yellow-400 text-sm">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <span><strong>สำคัญ:</strong> วัดค่าจริงก่อนใส่ การตั้งค่าผิดอาจทำให้แขนกลเสียหาย</span>
            </div>

            {/* === BASIC TAB === */}
            {activeTab === 'basic' && (
                <div className="space-y-4">
                    {/* Arm Z Settings */}
                    <Section title="แขน Z (ยืด/หด)" icon={ArrowLeftRight} color="text-blue-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <InputField
                                label="ความยาวแขนสูงสุด"
                                description="ระยะยืดสูงสุดที่แขนเคลื่อนที่ได้"
                                value={settings.max_arm_extend_cm}
                                onChange={(v) => update('max_arm_extend_cm', v)}
                                min={1} max={100} unit="cm"
                            />
                            <InputField
                                label="Offset จากกล้อง"
                                description="ระยะระหว่างกล้องกับฐานแขน"
                                value={settings.arm_base_offset_cm}
                                onChange={(v) => update('arm_base_offset_cm', v)}
                                min={0} max={50} unit="cm"
                            />
                            <InputField
                                label="ความเร็วแขน Z"
                                description="จากการวัด: 15.5cm ใน 7 วินาที = 2.21 cm/s"
                                value={settings.arm_speed_cm_per_sec}
                                onChange={(v) => update('arm_speed_cm_per_sec', v)}
                                step={0.01} min={0.1} max={20} unit="cm/s"
                            />
                            <InputField
                                label="ตำแหน่ง Home Z"
                                description="ตำแหน่งเริ่มต้นของแขน"
                                value={settings.arm_z_default_cm}
                                onChange={(v) => update('arm_z_default_cm', v)}
                                min={0} max={50} unit="cm"
                            />
                        </div>
                    </Section>

                    {/* Arm Y Settings */}
                    <Section title="แขน Y (ขึ้น/ลง)" icon={ArrowUpDown} color="text-cyan-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <InputField
                                label="ระยะเคลื่อนที่สูงสุด Y"
                                description="ระยะจากบนสุดถึงล่างสุด"
                                value={settings.motor_y_max_cm}
                                onChange={(v) => update('motor_y_max_cm', v)}
                                min={1} max={50} unit="cm"
                            />
                            <InputField
                                label="ความเร็วแขน Y"
                                value={settings.motor_y_speed_cm_per_sec}
                                onChange={(v) => update('motor_y_speed_cm_per_sec', v)}
                                min={1} max={30} unit="cm/s"
                            />
                            <InputField
                                label="มุมต่ำสุด Y"
                                value={settings.joint_y_min}
                                onChange={(v) => update('joint_y_min', v)}
                                min={-180} max={0} unit="°"
                            />
                            <InputField
                                label="มุมสูงสุด Y"
                                value={settings.joint_y_max}
                                onChange={(v) => update('joint_y_max', v)}
                                min={0} max={180} unit="°"
                            />
                        </div>
                    </Section>

                    {/* Spray Settings */}
                    <Section title="การพ่นยา" icon={Target} color="text-green-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <InputField
                                label="เวลาพ่นเริ่มต้น"
                                description="ระยะเวลาพ่นต่อหนึ่งเป้าหมาย"
                                value={settings.default_spray_duration}
                                onChange={(v) => update('default_spray_duration', v)}
                                step={0.1} min={0.1} max={10} unit="s"
                            />
                        </div>
                    </Section>
                </div>
            )}

            {/* === MOTION TAB === */}
            {activeTab === 'motion' && (
                <div className="space-y-4">
                    <Section title="ความเร็วและความเร่ง" icon={Gauge} color="text-orange-400">
                        <div className="space-y-4 mt-4">
                            <SliderField
                                label="ความเร็วสูงสุด"
                                value={settings.max_speed_percent}
                                onChange={(v) => update('max_speed_percent', v)}
                            />
                            <SliderField
                                label="ความเร่ง (Acceleration)"
                                value={settings.acceleration}
                                onChange={(v) => update('acceleration', v)}
                            />
                            <SliderField
                                label="ความชะลอ (Deceleration)"
                                value={settings.deceleration}
                                onChange={(v) => update('deceleration', v)}
                            />
                        </div>
                    </Section>

                    <Section title="ความแม่นยำ" icon={Target} color="text-purple-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <InputField
                                label="Position Tolerance"
                                description="ยอมรับความคลาดเคลื่อนตำแหน่ง"
                                value={settings.position_tolerance_cm}
                                onChange={(v) => update('position_tolerance_cm', v)}
                                step={0.1} min={0.1} max={5} unit="cm"
                            />
                            <InputField
                                label="Angle Tolerance"
                                description="ยอมรับความคลาดเคลื่อนมุม"
                                value={settings.angle_tolerance_deg}
                                onChange={(v) => update('angle_tolerance_deg', v)}
                                min={1} max={10} unit="°"
                            />
                            <InputField
                                label="Retry Attempts"
                                description="จำนวนครั้งที่ลองใหม่ถ้าไม่ถึงเป้า"
                                value={settings.retry_attempts}
                                onChange={(v) => update('retry_attempts', v)}
                                step={1} min={0} max={10} unit="ครั้ง"
                            />
                        </div>
                    </Section>

                    <Section title="Motion Planning" icon={Zap} color="text-yellow-400" defaultOpen={false}>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <SelectField
                                label="ประเภทการเคลื่อนที่"
                                value={settings.motion_type}
                                onChange={(v) => update('motion_type', v)}
                                options={[
                                    { value: 'direct', label: 'Direct (ตรงไปเป้าหมาย)' },
                                    { value: 'linear', label: 'Linear (เป็นเส้นตรง)' },
                                    { value: 'arc', label: 'Arc (เป็นโค้ง)' },
                                    { value: 'safe', label: 'Safe Path (หลีกสิ่งกีดขวาง)' },
                                ]}
                            />
                            <InputField
                                label="ความสูงก่อนพ่น"
                                description="ความสูงที่แขนลดลงมาก่อนพ่น"
                                value={settings.approach_height_cm}
                                onChange={(v) => update('approach_height_cm', v)}
                                min={0} max={20} unit="cm"
                            />
                            <SliderField
                                label="ความเร็วขณะเข้าใกล้"
                                value={settings.approach_speed_percent}
                                onChange={(v) => update('approach_speed_percent', v)}
                            />
                            <InputField
                                label="ความสูงหลังพ่น"
                                description="ความสูงที่แขนยกขึ้นหลังพ่น"
                                value={settings.retreat_height_cm}
                                onChange={(v) => update('retreat_height_cm', v)}
                                min={0} max={20} unit="cm"
                            />
                        </div>
                    </Section>
                </div>
            )}

            {/* === CAMERA TAB === */}
            {activeTab === 'camera' && (
                <div className="space-y-4">
                    <Section title="Camera Setup" icon={Camera} color="text-blue-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <InputField
                                label="ความสูงกล้อง"
                                description="ความสูงจากพื้นงาน"
                                value={settings.camera_height_cm}
                                onChange={(v) => update('camera_height_cm', v)}
                                min={10} max={200} unit="cm"
                            />
                            <InputField
                                label="มุมกล้อง"
                                description="0° = มองตรง, 90° = มองลง"
                                value={settings.camera_angle_deg}
                                onChange={(v) => update('camera_angle_deg', v)}
                                min={0} max={90} unit="°"
                            />
                            <InputField
                                label="Field of View"
                                description="มุมมองกล้อง"
                                value={settings.camera_fov_deg}
                                onChange={(v) => update('camera_fov_deg', v)}
                                min={30} max={120} unit="°"
                            />
                            <InputField
                                label="Pixel to CM Ratio"
                                description="อัตราส่วนแปลง (1 pixel = กี่ cm)"
                                value={settings.pixel_to_cm_ratio}
                                onChange={(v) => update('pixel_to_cm_ratio', v)}
                                step={0.001} min={0.001} max={1} unit="cm/px"
                            />
                        </div>
                    </Section>

                    <Section title="Workspace Bounds" icon={Eye} color="text-cyan-400" defaultOpen={false}>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
                            <InputField label="X Min" value={settings.workspace_x_min} onChange={(v) => update('workspace_x_min', v)} min={-100} max={0} unit="cm" />
                            <InputField label="X Max" value={settings.workspace_x_max} onChange={(v) => update('workspace_x_max', v)} min={0} max={100} unit="cm" />
                            <InputField label="Y Min" value={settings.workspace_y_min} onChange={(v) => update('workspace_y_min', v)} min={-100} max={0} unit="cm" />
                            <InputField label="Y Max" value={settings.workspace_y_max} onChange={(v) => update('workspace_y_max', v)} min={0} max={100} unit="cm" />
                            <InputField label="Z Min" value={settings.workspace_z_min} onChange={(v) => update('workspace_z_min', v)} min={0} max={50} unit="cm" />
                            <InputField label="Z Max" value={settings.workspace_z_max} onChange={(v) => update('workspace_z_max', v)} min={0} max={100} unit="cm" />
                        </div>
                    </Section>
                </div>
            )}

            {/* === SAFETY TAB === */}
            {activeTab === 'safety' && (
                <div className="space-y-4">
                    <Section title="Safety Limits" icon={Shield} color="text-red-400">
                        <div className="space-y-4 mt-4">
                            <ToggleField
                                label="Emergency Stop"
                                description="เปิดใช้งานปุ่มหยุดฉุกเฉิน"
                                value={settings.emergency_stop_enabled}
                                onChange={(v) => update('emergency_stop_enabled', v)}
                            />
                            <ToggleField
                                label="Collision Detection"
                                description="ตรวจจับการชน (ต้องมี sensor)"
                                value={settings.collision_detection_enabled}
                                onChange={(v) => update('collision_detection_enabled', v)}
                            />
                            <InputField
                                label="Timeout"
                                description="เวลาสูงสุดต่อการเคลื่อนที่"
                                value={settings.timeout_seconds}
                                onChange={(v) => update('timeout_seconds', v)}
                                step={1} min={5} max={120} unit="s"
                            />
                        </div>
                    </Section>

                    <Section title="Error Handling" icon={AlertTriangle} color="text-yellow-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <SelectField
                                label="เมื่อหาเป้าหมายไม่เจอ"
                                value={settings.on_target_lost}
                                onChange={(v) => update('on_target_lost', v)}
                                options={[
                                    { value: 'stop', label: 'หยุดทันที' },
                                    { value: 'last_position', label: 'ไปตำแหน่งล่าสุด' },
                                    { value: 'home', label: 'กลับ Home' },
                                ]}
                            />
                            <SelectField
                                label="เมื่อเป้าหมายไกลเกินไป"
                                value={settings.on_unreachable}
                                onChange={(v) => update('on_unreachable', v)}
                                options={[
                                    { value: 'nearest', label: 'ไปจุดใกล้สุดที่ถึงได้' },
                                    { value: 'skip', label: 'ข้ามไปเป้าถัดไป' },
                                    { value: 'alert', label: 'แจ้งเตือนผู้ใช้' },
                                ]}
                            />
                        </div>
                    </Section>

                    {/* System Controls */}
                    <Section title="ระบบ" icon={Power} color="text-red-400">
                        <div className="flex gap-4 flex-wrap mt-4">
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
                                        const res = await fetch(`${API_BASE}/api/camera/reconnect`, { method: 'POST' });
                                        const data = await res.json();
                                        if (data.success) {
                                            setMessage({ type: 'success', text: '✅ เชื่อมต่อกล้องสำเร็จ!' });
                                        } else {
                                            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อกล้องได้' });
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
                    </Section>
                </div>
            )}

            {/* === ADVANCED TAB === */}
            {activeTab === 'advanced' && (
                <div className="space-y-4">
                    <Section title="Control Method" icon={Sliders} color="text-purple-400">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                            <SelectField
                                label="โหมดการทำงาน"
                                value={settings.operation_mode}
                                onChange={(v) => update('operation_mode', v)}
                                options={[
                                    { value: 'auto', label: 'Auto - ตรวจจับอัตโนมัติ' },
                                    { value: 'manual', label: 'Manual - ควบคุมด้วยมือ' },
                                    { value: 'teaching', label: 'Teaching - บันทึกตำแหน่ง' },
                                    { value: 'repeat', label: 'Repeat - ทำซ้ำตามบันทึก' },
                                ]}
                            />
                            <SelectField
                                label="วิธีควบคุม"
                                value={settings.control_method}
                                onChange={(v) => update('control_method', v)}
                                options={[
                                    { value: 'visual_servoing', label: 'Visual Servoing (Feedback จากกล้อง)' },
                                    { value: 'inverse_kinematics', label: 'Inverse Kinematics (คำนวณล่วงหน้า)' },
                                    { value: 'hybrid', label: 'Hybrid (ผสมทั้งสอง)' },
                                ]}
                            />
                        </div>
                    </Section>

                    <Section title="PID Tuning" icon={Sliders} color="text-orange-400">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                            <InputField
                                label="Kp (Proportional)"
                                description="ค่าตอบสนองหลัก"
                                value={settings.pid_kp}
                                onChange={(v) => update('pid_kp', v)}
                                step={0.1} min={0} max={10}
                            />
                            <InputField
                                label="Ki (Integral)"
                                description="แก้ error สะสม"
                                value={settings.pid_ki}
                                onChange={(v) => update('pid_ki', v)}
                                step={0.01} min={0} max={5}
                            />
                            <InputField
                                label="Kd (Derivative)"
                                description="ลดการแกว่ง"
                                value={settings.pid_kd}
                                onChange={(v) => update('pid_kd', v)}
                                step={0.01} min={0} max={5}
                            />
                        </div>
                    </Section>

                    <Section title="Filters" icon={Eye} color="text-cyan-400" defaultOpen={false}>
                        <div className="space-y-4 mt-4">
                            <InputField
                                label="Moving Average Window"
                                description="จำนวน frame สำหรับกรอง noise"
                                value={settings.moving_average_window}
                                onChange={(v) => update('moving_average_window', v)}
                                step={1} min={1} max={20} unit="frames"
                            />
                            <ToggleField
                                label="Kalman Filter"
                                description="ใช้ Kalman Filter สำหรับ smooth tracking"
                                value={settings.kalman_filter_enabled}
                                onChange={(v) => update('kalman_filter_enabled', v)}
                            />
                        </div>
                    </Section>
                </div>
            )}

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
                    className="flex-1 px-6 py-3 bg-gradient-to-r from-primary-500 to-emerald-500 
                             text-white font-semibold rounded-xl shadow-lg shadow-primary-500/30
                             hover:shadow-primary-500/50 transition-all flex items-center justify-center gap-2
                             disabled:opacity-50"
                >
                    <Save className="w-5 h-5" />
                    {saving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า'}
                </button>

                <button
                    onClick={resetDefaults}
                    className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-gray-300 
                             rounded-xl transition-colors flex items-center gap-2"
                >
                    <RotateCcw className="w-5 h-5" />
                    รีเซ็ต
                </button>
            </div>
        </div>
    );
}
