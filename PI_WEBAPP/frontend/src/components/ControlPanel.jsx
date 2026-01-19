/**
 * ControlPanel Component
 * ปุ่มควบคุมหุ่นยนต์: Start, Stop, Download, Reset
 */

import {
    Play,
    Square,
    Download,
    RotateCcw,
    AlertTriangle,
    Loader2
} from 'lucide-react';
import { useState } from 'react';

export default function ControlPanel({
    onStart,
    onStop,
    onDownload,
    onReset,
    isRunning = false,
    isLoading = false
}) {
    const [confirmReset, setConfirmReset] = useState(false);
    const [downloadStatus, setDownloadStatus] = useState(null);

    // Handle start/stop
    const handleStartStop = async () => {
        if (isRunning) {
            await onStop?.();
        } else {
            await onStart?.();
        }
    };

    // Handle download
    const handleDownload = async () => {
        setDownloadStatus('downloading');
        try {
            await onDownload?.();
            setDownloadStatus('success');
            setTimeout(() => setDownloadStatus(null), 2000);
        } catch (error) {
            setDownloadStatus('error');
            setTimeout(() => setDownloadStatus(null), 2000);
        }
    };

    // Handle reset with confirmation
    const handleReset = async () => {
        if (!confirmReset) {
            setConfirmReset(true);
            setTimeout(() => setConfirmReset(false), 3000);
            return;
        }

        await onReset?.();
        setConfirmReset(false);
    };

    return (
        <div className="glass-dark p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                แผงควบคุม
            </h2>

            <div className="grid grid-cols-2 gap-4">
                {/* Start/Stop Button */}
                <button
                    onClick={handleStartStop}
                    disabled={isLoading}
                    className={`btn col-span-2 ${isRunning ? 'btn-danger' : 'btn-primary'}`}
                >
                    {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : isRunning ? (
                        <>
                            <Square className="w-5 h-5" />
                            หยุดฉุกเฉิน
                        </>
                    ) : (
                        <>
                            <Play className="w-5 h-5" />
                            เริ่ม Mission
                        </>
                    )}
                </button>

                {/* Download Button */}
                <button
                    onClick={handleDownload}
                    disabled={isLoading || downloadStatus === 'downloading'}
                    className="btn btn-secondary"
                >
                    {downloadStatus === 'downloading' ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : downloadStatus === 'success' ? (
                        '✓ ดาวน์โหลดแล้ว!'
                    ) : downloadStatus === 'error' ? (
                        '✗ ผิดพลาด'
                    ) : (
                        <>
                            <Download className="w-5 h-5" />
                            ดาวน์โหลด
                        </>
                    )}
                </button>

                {/* Reset Button */}
                <button
                    onClick={handleReset}
                    disabled={isLoading || isRunning}
                    className={`btn ${confirmReset
                        ? 'bg-red-600 hover:bg-red-700 text-white'
                        : 'btn-outline'}`}
                >
                    <RotateCcw className="w-5 h-5" />
                    {confirmReset ? 'ยืนยันรีเซ็ต?' : 'รีเซ็ตข้อมูล'}
                </button>
            </div>

            {/* Warning Messages */}
            {isRunning && (
                <div className="flex items-center gap-2 text-yellow-400 text-sm 
                        bg-yellow-500/10 rounded-lg p-3">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                    กำลังทำงาน...
                </div>
            )}

            {confirmReset && (
                <div className="text-red-400 text-sm bg-red-500/10 rounded-lg p-3">
                    ⚠️ การดำเนินการนี้จะลบข้อมูลทั้งหมด คลิกอีกครั้งเพื่อยืนยัน
                </div>
            )}
        </div>
    );
}
