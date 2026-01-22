/**
 * StateIndicator Component
 * แสดงสถานะปัจจุบันของหุ่นยนต์ (Idle, Moving, Spraying, Stopped)
 */

import {
    CircleDot,
    Navigation,
    Droplets,
    CircleStop,
    AlertTriangle
} from 'lucide-react';

// State configuration
const stateConfig = {
    Idle: {
        icon: CircleDot,
        color: 'text-gray-400',
        bgColor: 'bg-gray-500/20',
        ringColor: 'ring-gray-500/50',
        label: 'สแตนด์บาย',
        description: 'รอคำสั่ง'
    },
    Moving: {
        icon: Navigation,
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20',
        ringColor: 'ring-blue-500/50',
        label: 'กำลังเคลื่อนที่',
        description: 'กำลังค้นหาวัชพืช...'
    },
    Spraying: {
        icon: Droplets,
        color: 'text-cyan-400',
        bgColor: 'bg-cyan-500/20',
        ringColor: 'ring-cyan-500/50',
        label: 'กำลังพ่นยา',
        description: 'พ่นยากำจัดหญ้า'
    },
    Stopped: {
        icon: CircleStop,
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        ringColor: 'ring-red-500/50',
        label: 'หยุดแล้ว',
        description: 'หยุด Mission'
    },
    Error: {
        icon: AlertTriangle,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-500/20',
        ringColor: 'ring-yellow-500/50',
        label: 'ผิดพลาด',
        description: 'ตรวจสอบสถานะระบบ'
    }
};

export default function StateIndicator({ state = 'Idle' }) {
    const config = stateConfig[state] || stateConfig.Idle;
    const Icon = config.icon;
    const isActive = state === 'Moving' || state === 'Spraying';

    return (
        <div className={`glass-dark p-6 ${isActive ? 'ring-2 ' + config.ringColor : ''}`}>
            <div className="flex items-center gap-4">
                {/* Animated icon */}
                <div className={`relative w-16 h-16 rounded-2xl ${config.bgColor}
                        flex items-center justify-center`}>
                    <Icon className={`w-8 h-8 ${config.color} 
                           ${isActive ? 'animate-pulse' : ''}`} />

                    {/* Pulse ring for active states */}
                    {isActive && (
                        <div className={`absolute inset-0 rounded-2xl ${config.bgColor} 
                            animate-ping opacity-50`} />
                    )}
                </div>

                {/* Text */}
                <div>
                    <h3 className={`text-2xl font-bold ${config.color}`}>
                        {config.label}
                    </h3>
                    <p className="text-sm text-gray-500">
                        {config.description}
                    </p>
                </div>
            </div>

            {/* Progress bar for active states */}
            {isActive && (
                <div className="mt-4 h-1 bg-gray-700 rounded-full overflow-hidden">
                    <div
                        className={`h-full ${config.bgColor.replace('/20', '')} 
                       animate-pulse rounded-full`}
                        style={{
                            width: '100%',
                            animation: 'progress 2s ease-in-out infinite'
                        }}
                    />
                </div>
            )}

            <style>{`
        @keyframes progress {
          0%, 100% { transform: translateX(-100%); }
          50% { transform: translateX(100%); }
        }
      `}</style>
        </div>
    );
}
