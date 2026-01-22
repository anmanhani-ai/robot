/**
 * ModelSelectorPage.jsx
 * หน้าเลือกและจัดการ YOLO Model + Target Classes
 */

import { useState, useEffect } from 'react';
import {
    Brain, RefreshCw, Check, AlertTriangle, ChevronRight, Info, Target, Crosshair
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function ModelSelectorPage({ onBack }) {
    const [models, setModels] = useState([]);
    const [currentModel, setCurrentModel] = useState(null);
    const [modelInfo, setModelInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [changing, setChanging] = useState(false);
    const [message, setMessage] = useState(null);

    // Target classes state
    const [targetClasses, setTargetClasses] = useState([]);
    const [availableClasses, setAvailableClasses] = useState([]);

    // Fetch models and targets
    useEffect(() => {
        fetchModels();
        fetchModelInfo();
        fetchTargets();
    }, []);

    const fetchModels = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/models`);
            if (res.ok) {
                const data = await res.json();
                setModels(data.models || []);
                setCurrentModel(data.current);
            }
        } catch (err) {
            console.error('Failed to fetch models:', err);
        }
        setLoading(false);
    };

    const fetchModelInfo = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/models/info`);
            if (res.ok) {
                const data = await res.json();
                setModelInfo(data);
            }
        } catch (err) {
            console.error('Failed to fetch model info:', err);
        }
    };

    const fetchTargets = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/targets`);
            if (res.ok) {
                const data = await res.json();
                setTargetClasses(data.targets || []);
                setAvailableClasses(data.available_classes || []);
            }
        } catch (err) {
            console.error('Failed to fetch targets:', err);
        }
    };

    const handleSelectModel = async (modelName) => {
        if (modelName === currentModel) return;

        setChanging(true);
        setMessage({ type: 'info', text: `⏳ กำลังโหลด ${modelName}...` });

        try {
            const res = await fetch(`${API_BASE}/api/models/${modelName}`, {
                method: 'POST'
            });
            const data = await res.json();

            if (data.success) {
                setCurrentModel(modelName);
                setMessage({ type: 'success', text: `✅ ${data.message}` });
                fetchModelInfo();
                fetchTargets(); // Refresh available classes
            } else {
                setMessage({ type: 'error', text: `❌ ${data.detail || 'โหลดโมเดลไม่สำเร็จ'}` });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถเชื่อมต่อ server' });
        }

        setChanging(false);
    };

    const toggleTargetClass = async (className) => {
        const isCurrentlyTarget = targetClasses.includes(className.toLowerCase());

        try {
            const endpoint = isCurrentlyTarget
                ? `${API_BASE}/api/targets/remove/${className}`
                : `${API_BASE}/api/targets/add/${className}`;

            const res = await fetch(endpoint, { method: 'POST' });
            const data = await res.json();

            if (data.success) {
                setTargetClasses(data.targets);
                setMessage({
                    type: 'success',
                    text: isCurrentlyTarget
                        ? `➖ ยกเลิก ${className} จาก target`
                        : `➕ เพิ่ม ${className} เป็น target`
                });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '❌ ไม่สามารถอัปเดต target' });
        }
    };

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
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500
                          flex items-center justify-center shadow-lg shadow-purple-500/30">
                        <Brain className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">เลือก AI Model</h2>
                        <p className="text-sm text-gray-400">เลือกโมเดลและ class ที่ต้องการพ่น</p>
                    </div>
                </div>

                <button
                    onClick={onBack}
                    className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
                >
                    ← กลับ
                </button>
            </div>

            {/* Target Class Selection */}
            <div className="bg-gradient-to-r from-red-500/10 to-orange-500/10 backdrop-blur rounded-2xl border border-red-500/30 p-6">
                <div className="flex items-center gap-2 mb-4">
                    <Crosshair className="w-5 h-5 text-red-400" />
                    <h3 className="font-semibold text-white">เลือก Class ที่จะพ่นยา</h3>
                </div>

                <p className="text-sm text-gray-400 mb-4">
                    คลิกเพื่อ เปิด/ปิด class ที่ต้องการให้หุ่นยนต์พ่นยา (กรอบสีแดง = พ่น, กรอบสีเขียว = ไม่พ่น)
                </p>

                {availableClasses.length === 0 ? (
                    <div className="text-center text-gray-500 py-4">
                        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-yellow-500" />
                        <p>ยังไม่มี class (โหลดโมเดลก่อน)</p>
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-3">
                        {availableClasses.map((className) => {
                            const isTarget = targetClasses.includes(className.toLowerCase());
                            return (
                                <button
                                    key={className}
                                    onClick={() => toggleTargetClass(className)}
                                    className={`px-4 py-2 rounded-xl font-medium transition-all transform hover:scale-105 ${isTarget
                                            ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <Target className={`w-4 h-4 ${isTarget ? 'text-white' : 'text-gray-500'}`} />
                                        <span>{className}</span>
                                        {isTarget && <span className="text-xs">🎯</span>}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                )}

                <div className="mt-4 pt-4 border-t border-red-500/20">
                    <div className="text-sm text-gray-400">
                        <strong className="text-white">Target ปัจจุบัน:</strong>{' '}
                        {targetClasses.length > 0
                            ? targetClasses.map(t => <span key={t} className="text-red-400 mx-1">{t}</span>)
                            : <span className="text-yellow-400">ไม่มี (หุ่นยนต์จะไม่พ่นอะไร)</span>
                        }
                    </div>
                </div>
            </div>

            {/* Current Model Info */}
            {modelInfo && modelInfo.loaded && (
                <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <Info className="w-5 h-5 text-blue-400" />
                        <h3 className="font-semibold text-white">โมเดลที่ใช้งานอยู่</h3>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        <div>
                            <div className="text-lg font-bold text-primary-400">{modelInfo.model_name || '-'}</div>
                            <div className="text-xs text-gray-500">ชื่อโมเดล</div>
                        </div>
                        <div>
                            <div className="text-lg font-bold text-cyan-400">{modelInfo.num_classes || '-'}</div>
                            <div className="text-xs text-gray-500">Classes</div>
                        </div>
                        <div>
                            <div className="text-lg font-bold text-green-400">{modelInfo.using_gpu ? 'GPU' : 'CPU'}</div>
                            <div className="text-xs text-gray-500">Device</div>
                        </div>
                        <div>
                            <div className="text-sm font-mono text-gray-400 truncate">{currentModel || '-'}</div>
                            <div className="text-xs text-gray-500">ไฟล์</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Models List */}
            <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 overflow-hidden">
                <div className="p-4 border-b border-gray-700/50">
                    <h3 className="font-semibold text-white">โมเดลที่มี ({models.length})</h3>
                </div>

                {models.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
                        <p>ไม่พบไฟล์โมเดล (.pt) ใน folder</p>
                        <p className="text-sm mt-2">กรุณาวางไฟล์โมเดลใน raspberry_pi/models/</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700/50">
                        {models.map((model) => {
                            const isCurrent = model === currentModel;
                            return (
                                <button
                                    key={model}
                                    onClick={() => handleSelectModel(model)}
                                    disabled={changing || isCurrent}
                                    className={`w-full px-6 py-4 flex items-center justify-between transition-colors
                              ${isCurrent
                                            ? 'bg-primary-500/10 cursor-default'
                                            : 'hover:bg-gray-700/50'
                                        }
                              disabled:opacity-50`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isCurrent ? 'bg-primary-500' : 'bg-gray-700'
                                            }`}>
                                            <Brain className="w-5 h-5 text-white" />
                                        </div>
                                        <div className="text-left">
                                            <div className={`font-medium ${isCurrent ? 'text-primary-400' : 'text-white'}`}>
                                                {model}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {isCurrent ? '✓ กำลังใช้งาน' : 'คลิกเพื่อเลือก'}
                                            </div>
                                        </div>
                                    </div>

                                    {isCurrent ? (
                                        <Check className="w-5 h-5 text-primary-400" />
                                    ) : (
                                        <ChevronRight className="w-5 h-5 text-gray-500" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                )}
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

            {/* Help */}
            <div className="bg-gray-800/30 rounded-xl p-4 text-sm text-gray-400">
                <strong className="text-white">💡 วิธีใช้:</strong>
                <ul className="list-disc ml-4 mt-2 space-y-1">
                    <li><span className="text-red-400">กรอบสีแดง</span> = class ที่จะพ่นยา (target)</li>
                    <li><span className="text-green-400">กรอบสีเขียว</span> = class ที่จะไม่พ่น (safe)</li>
                    <li>คลิกที่ปุ่ม class เพื่อสลับ target/safe</li>
                </ul>
            </div>
        </div>
    );
}
