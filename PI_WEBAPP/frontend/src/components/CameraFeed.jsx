/**
 * CameraFeed Component
 * แสดง Live Camera Feed - Simple Version
 */

import { Video, RefreshCw } from 'lucide-react';
import { useState, useMemo } from 'react';

export default function CameraFeed({ isConnected = true }) {
    const [key, setKey] = useState(0);

    // Build camera URL using the same hostname but backend port
    const cameraUrl = useMemo(() => {
        const hostname = window.location.hostname;
        return `http://${hostname}:8000/api/camera/stream`;
    }, []);

    const handleRefresh = () => {
        setKey(prev => prev + 1);
    };

    return (
        <div className="glass-dark p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    <Video className="w-5 h-5 text-primary-400" />
                    กล้องถ่ายทอดสด
                </h2>

                <div className="flex items-center gap-2">
                    {/* Status indicator */}
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                        สด
                    </div>

                    {/* Refresh button */}
                    <button
                        onClick={handleRefresh}
                        className="p-1.5 rounded-lg hover:bg-gray-700 transition-colors"
                    >
                        <RefreshCw className="w-4 h-4 text-gray-400" />
                    </button>
                </div>
            </div>

            {/* Camera view - Simple img tag */}
            <div className="relative aspect-video bg-gray-900 rounded-xl overflow-hidden">
                <img
                    key={key}
                    src={`${cameraUrl}?refresh=${key}`}
                    alt="Camera Feed"
                    className="w-full h-full object-cover"
                />

                {/* Overlay info */}
                <div className="absolute bottom-2 left-2 right-2 flex justify-between text-xs text-white/70">
                    <span className="bg-black/50 px-2 py-1 rounded">480 x 360</span>
                    <span className="bg-black/50 px-2 py-1 rounded flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                        บันทึก
                    </span>
                </div>
            </div>
        </div>
    );
}
