/**
 * LogViewer Component
 * แสดง Log Entries แบบ Real-time
 */

import { ScrollText, Leaf, Sprout, AlertCircle, Play, Square } from 'lucide-react';
import { useEffect, useRef } from 'react';

// Icon และ Color ตาม event type
const eventConfig = {
    WEED_DETECTED: {
        icon: Leaf,
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        label: 'พ่นแล้ว'
    },
    CHILI_AVOIDED: {
        icon: Sprout,
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        label: 'หลีกเลี่ยง'
    },
    WEED_SPRAYED: {
        icon: Leaf,
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        label: 'พ่นแล้ว'
    },
    MISSION_START: {
        icon: Play,
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20',
        label: 'เริ่ม'
    },
    EMERGENCY_STOP: {
        icon: Square,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-500/20',
        label: 'หยุด'
    },
    default: {
        icon: AlertCircle,
        color: 'text-gray-400',
        bgColor: 'bg-gray-500/20',
        label: 'เหตุการณ์'
    }
};

function LogEntry({ log }) {
    const config = eventConfig[log.event] || eventConfig.default;
    const Icon = config.icon;

    // Format timestamp
    const formatTime = (timestamp) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('th-TH', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return timestamp;
        }
    };

    return (
        <div className="flex items-start gap-3 p-3 rounded-lg 
                    bg-gray-800/50 hover:bg-gray-800 transition-colors">
            {/* Icon */}
            <div className={`w-8 h-8 rounded-lg ${config.bgColor} 
                       flex items-center justify-center flex-shrink-0`}>
                <Icon className={`w-4 h-4 ${config.color}`} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${config.color}`}>
                        {config.label}
                    </span>
                    <span className="text-xs text-gray-500">
                        {formatTime(log.timestamp)}
                    </span>
                </div>

                {log.details && (
                    <p className="text-sm text-gray-400 truncate mt-0.5">
                        {log.details}
                    </p>
                )}

                {(log.x !== null || log.y !== null) && (
                    <p className="text-xs text-gray-500 mt-1">
                        ตำแหน่ง: ({log.x?.toFixed(0)}, {log.y?.toFixed(0)})
                    </p>
                )}
            </div>
        </div>
    );
}

export default function LogViewer({ logs = [], maxHeight = '400px' }) {
    const scrollRef = useRef(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="glass-dark p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    <ScrollText className="w-5 h-5 text-primary-400" />
                    ประวัติการทำงาน
                </h2>
                <span className="text-sm text-gray-500">
                    {logs.length} รายการ
                </span>
            </div>

            {/* Log list */}
            <div
                ref={scrollRef}
                className="space-y-2 overflow-y-auto pr-2"
                style={{ maxHeight }}
            >
                {logs.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <ScrollText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>ยังไม่มีกิจกรรม</p>
                        <p className="text-sm">เริ่ม Mission เพื่อดูประวัติ</p>
                    </div>
                ) : (
                    [...logs].reverse().map((log, index) => (
                        <LogEntry key={index} log={log} />
                    ))
                )}
            </div>
        </div>
    );
}
