/**
 * CameraFeed Component
 * แสดง Live Camera Feed พร้อม Coordinate Graph Overlay
 */

import { Video, RefreshCw, Grid } from 'lucide-react';
import { useState, useMemo } from 'react';

export default function CameraFeed({ isConnected = true }) {
    const [key, setKey] = useState(0);
    const [showGrid, setShowGrid] = useState(true);

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
                    {/* Grid toggle */}
                    <button
                        onClick={() => setShowGrid(!showGrid)}
                        className={`p-1.5 rounded-lg transition-colors ${showGrid ? 'bg-primary-500/30 text-primary-400' : 'hover:bg-gray-700 text-gray-400'}`}
                        title="แสดง/ซ่อน กราฟพิกัด"
                    >
                        <Grid className="w-4 h-4" />
                    </button>

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

            {/* Camera view with coordinate overlay */}
            <div className="relative aspect-video bg-gray-900 rounded-xl overflow-hidden">
                <img
                    key={key}
                    src={`${cameraUrl}?refresh=${key}`}
                    alt="Camera Feed"
                    className="w-full h-full object-cover"
                />

                {/* Coordinate Graph Overlay */}
                {showGrid && (
                    <svg
                        className="absolute inset-0 w-full h-full pointer-events-none"
                        viewBox="0 0 640 480"
                        preserveAspectRatio="none"
                    >
                        {/* Grid lines (every 80px) */}
                        <defs>
                            <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
                                <path d="M 80 0 L 0 0 0 80" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                            </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#grid)" />

                        {/* X-axis (at bottom, y=480) */}
                        <line x1="0" y1="478" x2="640" y2="478" stroke="#3b82f6" strokeWidth="2" />

                        {/* Y-axis (at center, x=320) */}
                        <line x1="320" y1="0" x2="320" y2="480" stroke="#3b82f6" strokeWidth="2" />

                        {/* Origin point (0,0) at bottom center */}
                        <circle cx="320" cy="478" r="6" fill="#ef4444" stroke="white" strokeWidth="2" />

                        {/* X-axis labels */}
                        <text x="20" y="468" fill="#3b82f6" fontSize="14" fontWeight="bold">X-</text>
                        <text x="600" y="468" fill="#3b82f6" fontSize="14" fontWeight="bold">X+</text>

                        {/* Y-axis label */}
                        <text x="330" y="20" fill="#22c55e" fontSize="14" fontWeight="bold">Y+</text>

                        {/* Origin label */}
                        <text x="270" y="465" fill="#ef4444" fontSize="12" fontWeight="bold">(0,0)</text>

                        {/* Direction labels */}
                        <text x="580" y="450" fill="#fbbf24" fontSize="10">Forward →</text>
                        <text x="10" y="450" fill="#fbbf24" fontSize="10">← Backward</text>

                        {/* Center crosshair */}
                        <circle cx="320" cy="240" r="4" fill="none" stroke="#22c55e" strokeWidth="2" />
                        <line x1="310" y1="240" x2="330" y2="240" stroke="#22c55e" strokeWidth="1" />
                        <line x1="320" y1="230" x2="320" y2="250" stroke="#22c55e" strokeWidth="1" />

                        {/* Pixel markers on X-axis */}
                        <text x="75" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">-240</text>
                        <text x="155" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">-160</text>
                        <text x="235" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">-80</text>
                        <text x="395" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">+80</text>
                        <text x="475" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">+160</text>
                        <text x="555" y="475" fill="rgba(255,255,255,0.5)" fontSize="9">+240</text>

                        {/* Pixel markers on Y-axis */}
                        <text x="325" y="400" fill="rgba(255,255,255,0.5)" fontSize="9">80</text>
                        <text x="325" y="320" fill="rgba(255,255,255,0.5)" fontSize="9">160</text>
                        <text x="325" y="240" fill="rgba(255,255,255,0.5)" fontSize="9">240</text>
                        <text x="325" y="160" fill="rgba(255,255,255,0.5)" fontSize="9">320</text>
                        <text x="325" y="80" fill="rgba(255,255,255,0.5)" fontSize="9">400</text>
                    </svg>
                )}

                {/* Overlay info */}
                <div className="absolute bottom-2 left-2 right-2 flex justify-between text-xs text-white/70">
                    <span className="bg-black/50 px-2 py-1 rounded">640 x 480</span>
                    <span className="bg-black/50 px-2 py-1 rounded flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
                        บันทึก
                    </span>
                </div>
            </div>

            {/* Coordinate info */}
            {showGrid && (
                <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-xs text-gray-400">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                            <div className="w-3 h-0.5 bg-blue-500"></div>
                            X-axis: ซ้าย(-) ← 0 → ขวา(+)
                        </span>
                        <span className="flex items-center gap-1">
                            <div className="w-0.5 h-3 bg-green-500"></div>
                            Y-axis: 0 → บน(+)
                        </span>
                        <span className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                            Origin (0,0) = 320px
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}
