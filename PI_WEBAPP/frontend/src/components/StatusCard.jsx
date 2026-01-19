/**
 * StatusCard Component
 * แสดงสถิติแบบ Card พร้อม Icon และ Animation
 */

import {
    Leaf,
    Sprout,
    Compass,
    Droplets,
    Battery,
    Activity
} from 'lucide-react';

// Icon mapping
const iconMap = {
    weed: Leaf,
    chili: Sprout,
    distance: Compass,
    spray: Droplets,
    battery: Battery,
    state: Activity,
};

// Color mapping based on type
const colorMap = {
    weed: 'text-red-400 bg-red-500/20',
    chili: 'text-green-400 bg-green-500/20',
    distance: 'text-blue-400 bg-blue-500/20',
    spray: 'text-cyan-400 bg-cyan-500/20',
    battery: 'text-yellow-400 bg-yellow-500/20',
    state: 'text-purple-400 bg-purple-500/20',
};

export default function StatusCard({
    title,
    value,
    unit = '',
    type = 'default',
    animate = false
}) {
    const Icon = iconMap[type] || Activity;
    const colorClass = colorMap[type] || 'text-gray-400 bg-gray-500/20';

    return (
        <div className="stat-card group">
            {/* Icon */}
            <div className={`w-12 h-12 rounded-xl ${colorClass} 
                       flex items-center justify-center
                       group-hover:scale-110 transition-transform duration-300`}>
                <Icon className={`w-6 h-6 ${animate ? 'animate-pulse' : ''}`} />
            </div>

            {/* Title */}
            <p className="text-sm text-gray-400 mt-2">{title}</p>

            {/* Value */}
            <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-white">
                    {typeof value === 'number' ? value.toLocaleString() : value}
                </span>
                {unit && (
                    <span className="text-sm text-gray-500">{unit}</span>
                )}
            </div>
        </div>
    );
}
