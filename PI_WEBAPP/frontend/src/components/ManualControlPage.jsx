/**
 * ManualControlPage.jsx
 * หน้าควบคุมหุ่นยนต์แบบ Manual
 * - เดินหน้า/ถอยหลัง/เลี้ยว
 * - ควบคุมแขนกล Z (ยืด/หด)
 * - ควบคุมหัวพ่น Y (ขึ้น/ลง)
 * - พ่นยา
 */

import { useState, useCallback, useEffect } from 'react';
import { 
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight, 
  Square, Droplets, Minus, Plus,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  Gamepad2, AlertTriangle, RefreshCw
} from 'lucide-react';

// API
const API_BASE = import.meta.env.VITE_API_URL || '';

async function sendManualCommand(command, params = {}) {
  try {
    const response = await fetch(`${API_BASE}/api/manual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, params })
    });
    return await response.json();
  } catch (error) {
    console.error('Manual command error:', error);
    throw error;
  }
}

export default function ManualControlPage({ onBack }) {
  const [isMoving, setIsMoving] = useState(false);
  const [currentAction, setCurrentAction] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [sprayDuration, setSprayDuration] = useState(1.0);
  const [armDuration, setArmDuration] = useState(1.0);
  const [isConnected, setIsConnected] = useState(true);

  // ==================== Movement Commands ====================
  
  const handleMoveStart = async (direction) => {
    setIsMoving(true);
    setCurrentAction(direction);
    try {
      const result = await sendManualCommand(`MOVE_${direction}`);
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    }
  };

  const handleMoveStop = async () => {
    setIsMoving(false);
    setCurrentAction(null);
    try {
      const result = await sendManualCommand('MOVE_STOP');
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    }
  };

  // ==================== Arm Z Commands ====================

  const handleArmZ = async (action) => {
    setCurrentAction(`ARM_Z_${action}`);
    try {
      const cmd = action === 'OUT' ? `ACT:Z_OUT:${armDuration}` : `ACT:Z_IN:${armDuration}`;
      const result = await sendManualCommand(cmd);
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    } finally {
      setCurrentAction(null);
    }
  };

  // ==================== Arm Y Commands ====================

  const handleArmY = async (action) => {
    setCurrentAction(`ARM_Y_${action}`);
    try {
      const cmd = action === 'UP' ? 'ACT:Y_UP' : 'ACT:Y_DOWN';
      const result = await sendManualCommand(cmd);
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    } finally {
      setCurrentAction(null);
    }
  };

  // ==================== Spray Command ====================

  const handleSpray = async () => {
    setCurrentAction('SPRAY');
    try {
      const result = await sendManualCommand(`ACT:SPRAY:${sprayDuration}`);
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    } finally {
      setCurrentAction(null);
    }
  };

  // ==================== Emergency Stop ====================

  const handleEmergencyStop = async () => {
    setIsMoving(false);
    setCurrentAction(null);
    try {
      const result = await sendManualCommand('STOP_ALL');
      setLastResult(result);
    } catch (err) {
      setLastResult({ success: false, error: err.message });
    }
  };

  // ==================== Keyboard Controls ====================

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT') return;
      
      switch (e.key.toLowerCase()) {
        case 'w':
        case 'arrowup':
          if (!isMoving) handleMoveStart('FORWARD');
          break;
        case 's':
        case 'arrowdown':
          if (!isMoving) handleMoveStart('BACKWARD');
          break;
        case 'a':
        case 'arrowleft':
          if (!isMoving) handleMoveStart('LEFT');
          break;
        case 'd':
        case 'arrowright':
          if (!isMoving) handleMoveStart('RIGHT');
          break;
        case ' ':
          e.preventDefault();
          handleMoveStop();
          break;
        case 'escape':
          handleEmergencyStop();
          break;
      }
    };

    const handleKeyUp = (e) => {
      if (['w', 's', 'a', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(e.key.toLowerCase())) {
        handleMoveStop();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isMoving]);

  // ==================== Button Component ====================

  const ControlButton = ({ onClick, onMouseDown, onMouseUp, icon: Icon, label, active, danger, disabled, className = '' }) => (
    <button
      onClick={onClick}
      onMouseDown={onMouseDown}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      disabled={disabled}
      className={`
        p-4 rounded-xl font-medium transition-all duration-150
        flex flex-col items-center justify-center gap-2
        ${active 
          ? 'bg-primary-500 text-white scale-95 shadow-lg shadow-primary-500/30' 
          : danger
            ? 'bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white'
            : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600 hover:text-white'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
    >
      <Icon className="w-6 h-6" />
      {label && <span className="text-xs">{label}</span>}
    </button>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500
                          flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Gamepad2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Manual Control</h2>
            <p className="text-sm text-gray-400">ควบคุมหุ่นยนต์ด้วยตัวเอง</p>
          </div>
        </div>
        
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
        >
          ← กลับ
        </button>
      </div>

      {/* Keyboard Hint */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <p className="text-blue-400 text-sm">
          💡 <strong>ใช้คีย์บอร์ดควบคุมได้:</strong> W/A/S/D หรือ ลูกศร = เคลื่อนที่ | Space = หยุด | ESC = หยุดฉุกเฉิน
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Movement Controls */}
        <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            🚗 ควบคุมการเคลื่อนที่
          </h3>
          
          <div className="grid grid-cols-3 gap-3 max-w-[200px] mx-auto">
            {/* Row 1 */}
            <div></div>
            <ControlButton
              icon={ArrowUp}
              label="หน้า"
              active={currentAction === 'FORWARD'}
              onMouseDown={() => handleMoveStart('FORWARD')}
              onMouseUp={handleMoveStop}
            />
            <div></div>
            
            {/* Row 2 */}
            <ControlButton
              icon={ArrowLeft}
              label="ซ้าย"
              active={currentAction === 'LEFT'}
              onMouseDown={() => handleMoveStart('LEFT')}
              onMouseUp={handleMoveStop}
            />
            <ControlButton
              icon={Square}
              label="หยุด"
              active={!isMoving}
              onClick={handleMoveStop}
              className="bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500 hover:text-white"
            />
            <ControlButton
              icon={ArrowRight}
              label="ขวา"
              active={currentAction === 'RIGHT'}
              onMouseDown={() => handleMoveStart('RIGHT')}
              onMouseUp={handleMoveStop}
            />
            
            {/* Row 3 */}
            <div></div>
            <ControlButton
              icon={ArrowDown}
              label="ถอย"
              active={currentAction === 'BACKWARD'}
              onMouseDown={() => handleMoveStart('BACKWARD')}
              onMouseUp={handleMoveStop}
            />
            <div></div>
          </div>
        </div>

        {/* Arm Controls */}
        <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            🦾 ควบคุมแขนกล
          </h3>

          <div className="space-y-6">
            {/* Duration Setting */}
            <div className="flex items-center gap-4">
              <span className="text-gray-400 text-sm">เวลา:</span>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setArmDuration(Math.max(0.5, armDuration - 0.5))}
                  className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  <Minus className="w-4 h-4 text-gray-300" />
                </button>
                <span className="text-white font-mono w-16 text-center">{armDuration.toFixed(1)}s</span>
                <button 
                  onClick={() => setArmDuration(Math.min(5, armDuration + 0.5))}
                  className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  <Plus className="w-4 h-4 text-gray-300" />
                </button>
              </div>
            </div>

            {/* Arm Z Controls */}
            <div>
              <p className="text-gray-400 text-sm mb-2">แกน Z (ยืด/หด แนวนอน)</p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleArmZ('OUT')}
                  disabled={currentAction !== null}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all
                    ${currentAction === 'ARM_Z_OUT' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}
                    flex items-center justify-center gap-2
                  `}
                >
                  <ChevronRight className="w-5 h-5" />
                  ยืดออก
                </button>
                <button
                  onClick={() => handleArmZ('IN')}
                  disabled={currentAction !== null}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all
                    ${currentAction === 'ARM_Z_IN' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}
                    flex items-center justify-center gap-2
                  `}
                >
                  <ChevronLeft className="w-5 h-5" />
                  หดเข้า
                </button>
              </div>
            </div>

            {/* Arm Y Controls */}
            <div>
              <p className="text-gray-400 text-sm mb-2">แกน Y (หัวพ่น ขึ้น/ลง)</p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleArmY('UP')}
                  disabled={currentAction !== null}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all
                    ${currentAction === 'ARM_Y_UP' 
                      ? 'bg-cyan-500 text-white' 
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}
                    flex items-center justify-center gap-2
                  `}
                >
                  <ChevronUp className="w-5 h-5" />
                  ยกขึ้น
                </button>
                <button
                  onClick={() => handleArmY('DOWN')}
                  disabled={currentAction !== null}
                  className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all
                    ${currentAction === 'ARM_Y_DOWN' 
                      ? 'bg-cyan-500 text-white' 
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}
                    flex items-center justify-center gap-2
                  `}
                >
                  <ChevronDown className="w-5 h-5" />
                  วางลง
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Spray Control */}
        <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700/50 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            💦 ควบคุมการพ่นยา
          </h3>

          <div className="space-y-4">
            {/* Duration Setting */}
            <div className="flex items-center gap-4">
              <span className="text-gray-400 text-sm">เวลาพ่น:</span>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setSprayDuration(Math.max(0.5, sprayDuration - 0.5))}
                  className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  <Minus className="w-4 h-4 text-gray-300" />
                </button>
                <span className="text-white font-mono w-16 text-center">{sprayDuration.toFixed(1)}s</span>
                <button 
                  onClick={() => setSprayDuration(Math.min(10, sprayDuration + 0.5))}
                  className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                >
                  <Plus className="w-4 h-4 text-gray-300" />
                </button>
              </div>
            </div>

            {/* Spray Button */}
            <button
              onClick={handleSpray}
              disabled={currentAction !== null}
              className={`w-full py-4 rounded-xl font-bold text-lg transition-all
                ${currentAction === 'SPRAY'
                  ? 'bg-green-500 text-white scale-95'
                  : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600'}
                flex items-center justify-center gap-3 shadow-lg shadow-green-500/30
              `}
            >
              <Droplets className="w-6 h-6" />
              {currentAction === 'SPRAY' ? 'กำลังพ่น...' : 'พ่นยา'}
            </button>
          </div>
        </div>

        {/* Emergency Stop */}
        <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-red-500/30 p-6">
          <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            หยุดฉุกเฉิน
          </h3>

          <button
            onClick={handleEmergencyStop}
            className="w-full py-6 rounded-xl font-bold text-xl transition-all
              bg-gradient-to-r from-red-600 to-red-500 text-white 
              hover:from-red-700 hover:to-red-600
              flex items-center justify-center gap-3 shadow-lg shadow-red-500/30
              active:scale-95
            "
          >
            <Square className="w-8 h-8" />
            STOP ALL
          </button>
          <p className="text-gray-500 text-sm text-center mt-3">กด ESC หรือคลิกปุ่มนี้เพื่อหยุดทันที</p>
        </div>
      </div>

      {/* Status Display */}
      {lastResult && (
        <div className={`p-4 rounded-xl ${lastResult.success !== false ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          <p className="text-sm">
            {lastResult.success !== false 
              ? `✅ ${lastResult.message || 'คำสั่งสำเร็จ'}` 
              : `❌ ${lastResult.error || 'เกิดข้อผิดพลาด'}`
            }
          </p>
        </div>
      )}
    </div>
  );
}
