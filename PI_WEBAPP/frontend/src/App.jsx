/**
 * AgriBot Dashboard - Main App
 * Real-time control dashboard for agricultural weeding robot
 */

import { useState, useEffect, useCallback } from 'react';
import { Tractor, Wifi, WifiOff, Settings, Gamepad2, Activity, Cpu, Zap, Brain, Focus } from 'lucide-react';

// Components
import StatusCard from './components/StatusCard';
import ControlPanel from './components/ControlPanel';
import LogViewer from './components/LogViewer';
import CameraFeed from './components/CameraFeed';
import StateIndicator from './components/StateIndicator';
import SettingsPage from './components/SettingsPage';
import ManualControlPage from './components/ManualControlPage';
import HealthCheckPage from './components/HealthCheckPage';
import GpioConfigPage from './components/GpioConfigPage';
import AutoTestPage from './components/AutoTestPage';
import ModelSelectorPage from './components/ModelSelectorPage';
import CalibrationPage from './components/CalibrationPage';
import StepIndicator from './components/StepIndicator';

// API
import { getStatus, sendCommand, getLogs, downloadReport, resetReport, CAMERA_STREAM_URL } from './services/api';

// Import CSS
import './index.css';


export default function App() {
  // State
  const [status, setStatus] = useState({
    weed_count: 0,
    chili_count: 0,
    distance_traveled: 0,
    state: 'Idle',
    spray_count: 0,
    battery: 100,
    current_step: 0,
    step_description: '',
  });
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState('dashboard'); // 'dashboard' | 'settings' | 'manual' | 'health' | 'auto'

  // ==================== Data Fetching ====================

  /**
   * Fetch status from backend (polling every 1 second)
   */
  const fetchStatus = useCallback(async () => {
    try {
      const data = await getStatus();
      setStatus(data);
      setIsConnected(true);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch status:', err);
      setIsConnected(false);
      setError('Connection lost');
    }
  }, []);

  /**
   * Fetch logs from backend
   */
  const fetchLogs = useCallback(async () => {
    try {
      const data = await getLogs(100);
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, []);

  // Polling effect
  useEffect(() => {
    // Initial fetch
    fetchStatus();
    fetchLogs();

    // Setup polling interval (1 second)
    const statusInterval = setInterval(fetchStatus, 1000);
    const logsInterval = setInterval(fetchLogs, 2000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(logsInterval);
    };
  }, [fetchStatus, fetchLogs]);

  // ==================== Command Handlers ====================

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await sendCommand('start');
      await fetchStatus();
    } catch (err) {
      setError('Failed to start mission');
    }
    setIsLoading(false);
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      await sendCommand('stop');
      await fetchStatus();
    } catch (err) {
      setError('Failed to stop mission');
    }
    setIsLoading(false);
  };

  const handleDownload = async () => {
    try {
      await downloadReport();
    } catch (err) {
      throw err; // Let ControlPanel handle this
    }
  };

  const handleReset = async () => {
    setIsLoading(true);
    try {
      await resetReport();
      setLogs([]);
      await fetchStatus();
    } catch (err) {
      setError('Failed to reset');
    }
    setIsLoading(false);
  };

  // ==================== Render ====================

  const isRunning = status.state === 'Moving' || status.state === 'Spraying';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Background Pattern */}
      <div className="fixed inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2322c55e' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }} />

      {/* Main Content */}
      <div className="relative z-10 container mx-auto px-4 py-6 max-w-7xl">

        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700
                           flex items-center justify-center shadow-lg shadow-primary-500/30">
              <Tractor className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">AgriBot</h1>
              <p className="text-sm text-gray-400">ระบบควบคุมหุ่นยนต์กำจัดวัชพืช</p>
            </div>
          </div>

          {/* Connection Status */}
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full
                          ${isConnected
              ? 'bg-green-500/20 text-green-400'
              : 'bg-red-500/20 text-red-400'}`}>
            {isConnected ? (
              <Wifi className="w-4 h-4" />
            ) : (
              <WifiOff className="w-4 h-4" />
            )}
            <span className="text-sm font-medium">
              {isConnected ? 'เชื่อมต่อแล้ว' : 'ไม่ได้เชื่อมต่อ'}
            </span>
          </div>

          {/* Header Buttons */}
          <div className="flex items-center gap-2">
            {/* Health Check Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'health' ? 'dashboard' : 'health')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'health'
                ? 'bg-purple-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="ตรวจสอบอุปกรณ์"
            >
              <Activity className="w-5 h-5" />
              <span className="hidden sm:inline text-sm">Health</span>
            </button>

            {/* GPIO Config Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'gpio' ? 'dashboard' : 'gpio')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'gpio'
                ? 'bg-orange-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="ตั้งค่า GPIO"
            >
              <Cpu className="w-5 h-5" />
            </button>

            {/* Model Selector Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'model' ? 'dashboard' : 'model')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'model'
                ? 'bg-pink-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="เลือก AI Model"
            >
              <Brain className="w-5 h-5" />
              <span className="hidden sm:inline text-sm">Model</span>
            </button>

            {/* Calibration Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'calibration' ? 'dashboard' : 'calibration')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'calibration'
                ? 'bg-yellow-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="Calibration Wizard"
            >
              <Focus className="w-5 h-5" />
              <span className="hidden sm:inline text-sm">Calibrate</span>
            </button>

            {/* Auto Test Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'auto' ? 'dashboard' : 'auto')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'auto'
                ? 'bg-green-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="ทดสอบอัตโนมัติ"
            >
              <Zap className="w-5 h-5" />
              <span className="hidden sm:inline text-sm">Auto</span>
            </button>

            {/* Manual Control Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'manual' ? 'dashboard' : 'manual')}
              className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${currentPage === 'manual'
                ? 'bg-blue-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="ควบคุมด้วยตนเอง"
            >
              <Gamepad2 className="w-5 h-5" />
              <span className="hidden sm:inline text-sm">Manual</span>
            </button>

            {/* Settings Button */}
            <button
              onClick={() => setCurrentPage(currentPage === 'settings' ? 'dashboard' : 'settings')}
              className={`p-2 rounded-lg transition-colors ${currentPage === 'settings'
                ? 'bg-primary-500 text-white'
                : 'hover:bg-gray-700 text-gray-400'
                }`}
              title="ตั้งค่า"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 
                         rounded-xl text-red-400 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Conditional Page Render */}
        {currentPage === 'settings' ? (
          <SettingsPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'manual' ? (
          <ManualControlPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'health' ? (
          <HealthCheckPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'gpio' ? (
          <GpioConfigPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'model' ? (
          <ModelSelectorPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'auto' ? (
          <AutoTestPage onBack={() => setCurrentPage('dashboard')} />
        ) : currentPage === 'calibration' ? (
          <CalibrationPage onBack={() => setCurrentPage('dashboard')} />
        ) : (
          /* Main Grid - Dashboard */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Left Column: Stats + Camera */}
            <div className="lg:col-span-2 space-y-6">

              {/* State Indicator */}
              <StateIndicator state={status.state} />

              {/* Step Indicator - แสดง step ปัจจุบัน */}
              {(status.current_step > 0 || status.step_description) && (
                <StepIndicator
                  currentStep={status.current_step}
                  stepDescription={status.step_description}
                />
              )}

              {/* Robot Speech Bubble */}
              <div className="bg-gradient-to-r from-primary-500/10 to-blue-500/10 
                              border border-primary-500/30 rounded-2xl p-4 
                              flex items-center gap-4 relative overflow-hidden">
                {/* Robot Avatar */}
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary-400 to-primary-600
                                flex items-center justify-center text-3xl shadow-lg shadow-primary-500/30
                                flex-shrink-0">
                  {status.robot_emoji || '🤖'}
                </div>

                {/* Speech Bubble */}
                <div className="flex-1 min-w-0">
                  <div className="relative bg-gray-800/80 rounded-xl px-4 py-3 text-white
                                  before:content-[''] before:absolute before:left-[-8px] before:top-1/2
                                  before:border-8 before:border-transparent before:border-r-gray-800/80
                                  before:-translate-y-1/2">
                    <p className="text-base font-medium truncate">
                      {status.robot_message || 'สวัสดีครับ! พร้อมทำงานแล้ว 🌱'}
                    </p>
                  </div>
                </div>

                {/* Animated Pulse when running */}
                {isRunning && (
                  <div className="absolute top-2 right-2">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-primary-500"></span>
                    </span>
                  </div>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatusCard
                  title="หญ้าที่พ่นแล้ว"
                  value={status.weed_count}
                  type="weed"
                  animate={isRunning}
                />
                <StatusCard
                  title="พริกที่หลีกเลี่ยง"
                  value={status.chili_count}
                  type="chili"
                />
                <StatusCard
                  title="ระยะทาง"
                  value={status.distance_traveled.toFixed(1)}
                  unit="ม."
                  type="distance"
                />
                <StatusCard
                  title="แบตเตอรี่"
                  value={status.battery}
                  unit="%"
                  type="battery"
                />
              </div>

              {/* Camera Feed */}
              <CameraFeed
                streamUrl="/api/camera/stream"
                isConnected={true}
              />
            </div>

            {/* Right Column: Controls + Logs */}
            <div className="space-y-6">

              {/* Control Panel */}
              <ControlPanel
                onStart={handleStart}
                onStop={handleStop}
                onDownload={handleDownload}
                onReset={handleReset}
                isRunning={isRunning}
                isLoading={isLoading}
              />

              {/* Activity Log */}
              <LogViewer logs={logs} maxHeight="350px" />
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-8 text-center text-gray-600 text-sm">
          <p>AgriBot Dashboard v1.0 • Raspberry Pi 5</p>
        </footer>
      </div>
    </div>
  );
}
