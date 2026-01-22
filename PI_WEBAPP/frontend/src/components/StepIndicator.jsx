/**
 * StepIndicator - แสดงขั้นตอนการทำงานปัจจุบัน
 * ใช้สำหรับ debug และตรวจสอบระหว่างทดสอบบนอุปกรณ์จริง
 */

import { Check, Circle, PlayCircle, Pause } from 'lucide-react';

const STEPS = [
    { id: 0, name: 'Idle', icon: '⏸️' },
    { id: 1, name: 'Searching', icon: '🔍' },
    { id: 2, name: 'Detected', icon: '🎯' },
    { id: 3, name: 'Aligning', icon: '📐' },
    { id: 4, name: 'Calculate Z', icon: '📏' },
    { id: 5, name: 'Offset', icon: '➡️' },
    { id: 6, name: 'Spraying', icon: '💦' },
    { id: 7, name: 'Reset', icon: '🔄' },
    { id: 8, name: 'Continue', icon: '✅' },
];

export default function StepIndicator({ currentStep = 0, stepDescription = '' }) {
    return (
        <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <PlayCircle className="w-5 h-5 text-primary-400" />
                    ขั้นตอนการทำงาน
                </h3>
                <span className="px-3 py-1 bg-primary-500/20 text-primary-400 rounded-full text-sm font-medium">
                    Step {currentStep}/8
                </span>
            </div>

            {/* Step Pills */}
            <div className="flex flex-wrap gap-2 mb-4">
                {STEPS.map((step) => {
                    const isActive = step.id === currentStep;
                    const isPast = step.id < currentStep;

                    return (
                        <div
                            key={step.id}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${isActive
                                    ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30 scale-110'
                                    : isPast
                                        ? 'bg-green-500/20 text-green-400'
                                        : 'bg-gray-700/50 text-gray-500'
                                }`}
                        >
                            <span>{step.icon}</span>
                            <span className="hidden sm:inline">{step.name}</span>
                            <span className="sm:hidden">{step.id}</span>
                        </div>
                    );
                })}
            </div>

            {/* Current Step Description */}
            {stepDescription && (
                <div className="bg-gray-900/50 rounded-xl p-3 border border-gray-700/50">
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center text-lg flex-shrink-0">
                            {STEPS.find(s => s.id === currentStep)?.icon || '🤖'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-primary-400 font-medium text-sm">
                                {STEPS.find(s => s.id === currentStep)?.name || 'Unknown'}
                            </p>
                            <p className="text-white text-base mt-1 break-words">
                                {stepDescription}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Progress Bar */}
            <div className="mt-4 h-2 bg-gray-700/50 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-300"
                    style={{ width: `${(currentStep / 8) * 100}%` }}
                />
            </div>
        </div>
    );
}
