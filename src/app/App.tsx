import { useState, useEffect } from "react";
import { StatusChip } from "@/app/components/StatusChip";
import { KpiCard } from "@/app/components/KpiCard";
import { DeviceGrid } from "@/app/components/DeviceGrid";
import { TimeSeriesChart } from "@/app/components/TimeSeriesChart";
import { AvailabilityTimeline } from "@/app/components/AvailabilityTimeline";
import { LogTable } from "@/app/components/LogTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";

// Mock data generator for initial state
function generateInitialData() {
  const now = Date.now();
  
  // Combined data for both PPS and Jitter
  const combinedData = Array.from({ length: 60 }, (_, i) => ({
    timestamp: new Date(now - (60 - i) * 1000).toLocaleTimeString(),
    pps: Math.floor(800 + Math.random() * 400),
    jitter: parseFloat((0.5 + Math.random() * 2).toFixed(2)),
  }));

  const availabilitySegments = [
    { start: 0, end: 2700, status: "up" as const },
    { start: 2700, end: 2850, status: "down" as const },
    { start: 2850, end: 3600, status: "up" as const },
  ];

  const devices = [
    { name: "VIC", connected: true },
    { name: "RDC", connected: true },
    { name: "ADC", connected: true },
    { name: "FCAM", connected: true },
    { name: "RCAM", connected: true },
    { name: "AUX", connected: true, warning: true },
    { name: "SCS", connected: true },
    { name: "DIP", connected: true },
    { name: "TCC", connected: false },
    { name: "TM", connected: true },
  ];

  const logs = Array.from({ length: 15 }, (_, i) => ({
    time: new Date(now - (15 - i) * 2000).toLocaleTimeString(),
    seq: 49195 + i,
    msg_code: `0x${(Math.floor(Math.random() * 255)).toString(16).padStart(2, "0").toUpperCase()}`,
    parse_ok: Math.random() > 0.05,
    checksum_ok: Math.random() > 0.03,
    mode: ["원격 주행 (REMOTE)", "수동", "대기"][Math.floor(Math.random() * 3)],
    authority: ["OCS(운용통제기)", "근거리조종기", "없음"][Math.floor(Math.random() * 3)],
    notes: i % 10 === 0 ? "네트워크 지터 감지 (12.5ms)" : "",
  }));

  const emergencyStatus = {
    "통신 두절": false,
    "장비고장(주행)": false,
    "장비고장(동력계)": false,
    "신호단절(주행)": true,
    "신호단절(자율)": false,
    "신호단절(항법)": false,
    "신호단절(동력계)": false,
    "신호단절(통신)": false,
    "수동정지(운용통제장치)": false,
    "수동정지(근거리조종기)": false,
  };

  return {
    connected: true,
    interface: "eno2",
    filter: "50000→61000",
    timeRange: "0.05s",
    lastPacketTime: new Date().toLocaleTimeString(),
    parseOkRate: 97.2,
    capturePps: 1024,
    filterPass: 99.9,
    parseSuccess: 100,
    checksumFail: 0.0,
    packetLoss: 0,
    availability5min: 99.98,
    availability1hour: 99.99,
    jitterP95: 2.1,
    jitterP99: 2.4,
    operationalMode: "원격 주행 (REMOTE)",
    operationalAuthority: "OCS(운용통제기)",
    drivingState: "전진/대기",
    combinedData,
    availabilitySegments,
    devices,
    logs,
    emergencyStatus,
    lastSeq: 49195 + 14,
    elapsedTime: 0,
  };
}

export default function App() {
  const [data, setData] = useState(generateInitialData());
  const [isPaused, setIsPaused] = useState(false);

  // Simulate polling every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPaused) return;
      
      setData((prevData) => {
        const now = Date.now();
        
        // Update combined chart data
        const newDataPoint = {
          timestamp: new Date(now).toLocaleTimeString(),
          pps: Math.floor(800 + Math.random() * 400),
          jitter: parseFloat((0.5 + Math.random() * 2).toFixed(2)),
        };
        const newCombinedData = [...prevData.combinedData.slice(1), newDataPoint];

        // Add new log entry
        const newSeq = prevData.lastSeq + 1;
        const newLog = {
          time: new Date(now).toLocaleTimeString(),
          seq: newSeq,
          msg_code: `0x${(Math.floor(Math.random() * 255)).toString(16).padStart(2, "0").toUpperCase()}`,
          parse_ok: Math.random() > 0.05,
          checksum_ok: Math.random() > 0.03,
          mode: ["원격 주행 (REMOTE)", "수동", "대기"][Math.floor(Math.random() * 3)],
          authority: ["OCS(운용통제기)", "근거리조종기", "없음"][Math.floor(Math.random() * 3)],
          notes: Math.random() > 0.9 ? "네트워크 지터 감지 (12.5ms)" : "",
        };

        const newLogs = [newLog, ...prevData.logs].slice(0, 200);

        // Update KPIs occasionally
        const shouldUpdateKpis = Math.random() > 0.7;
        
        // Update availability timeline (1 hour = 3600 seconds)
        const newElapsedTime = prevData.elapsedTime + 2;
        const timeWindow = 3600; // 1 hour window
        
        const isConnected = Math.random() > 0.02; // 98% uptime
        
        let newSegments = [...prevData.availabilitySegments];
        const lastSegment = newSegments[newSegments.length - 1];
        
        if (lastSegment) {
          if ((isConnected && lastSegment.status === "up") || (!isConnected && lastSegment.status === "down")) {
            lastSegment.end = Math.min(newElapsedTime, timeWindow);
          } else {
            newSegments.push({
              start: lastSegment.end,
              end: Math.min(newElapsedTime, timeWindow),
              status: isConnected ? "up" : "down",
            });
          }
          
          if (newElapsedTime > timeWindow) {
            const offset = newElapsedTime - timeWindow;
            newSegments = newSegments
              .map(seg => ({
                ...seg,
                start: Math.max(0, seg.start - offset),
                end: Math.max(0, seg.end - offset),
              }))
              .filter(seg => seg.end > 0);
          }
        }
        
        return {
          ...prevData,
          lastPacketTime: new Date().toLocaleTimeString(),
          capturePps: shouldUpdateKpis ? Math.floor(1000 + Math.random() * 100) : prevData.capturePps,
          parseOkRate: shouldUpdateKpis ? parseFloat((96 + Math.random() * 3).toFixed(1)) : prevData.parseOkRate,
          filterPass: shouldUpdateKpis ? parseFloat((99 + Math.random()).toFixed(1)) : prevData.filterPass,
          parseSuccess: shouldUpdateKpis ? parseFloat((99 + Math.random()).toFixed(1)) : prevData.parseSuccess,
          checksumFail: shouldUpdateKpis ? parseFloat((Math.random() * 0.5).toFixed(1)) : prevData.checksumFail,
          packetLoss: shouldUpdateKpis ? Math.floor(Math.random() * 2) : prevData.packetLoss,
          jitterP95: parseFloat((1.5 + Math.random()).toFixed(1)),
          jitterP99: parseFloat((2 + Math.random() * 0.8).toFixed(1)),
          combinedData: newCombinedData,
          logs: newLogs,
          lastSeq: newSeq,
          elapsedTime: newElapsedTime,
          availabilitySegments: newSegments,
        };
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [isPaused]);

  const handlePauseToggle = () => {
    setIsPaused(!isPaused);
  };

  const handleClearLogs = () => {
    setData((prevData) => ({
      ...prevData,
      logs: [],
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      {/* Header Bar */}
      <div className="bg-white border border-slate-200 rounded-xl px-6 py-4 mb-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-1 h-8 bg-blue-600 rounded-full"></div>
            <h1 className="text-xl font-bold text-slate-800">VIC↔OCS 실시간 모니터링</h1>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip
              label="연결상태"
              value={data.connected ? "연결됨" : "연결끊김"}
              variant={data.connected ? "success" : "destructive"}
            />
            <StatusChip label="인터페이스" value={data.interface} />
            <StatusChip label="필터" value={data.filter} />
            <StatusChip label="시간범위" value={data.timeRange} />
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-8 gap-4 mb-6">
        <KpiCard 
          title="수신 pps" 
          value={data.capturePps} 
          unit="pps" 
          showProgress 
          progressColor="blue"
          progressValue={70}
        />
        <KpiCard 
          title="필터 통과율" 
          value={data.filterPass} 
          unit="%" 
          showProgress 
          progressColor="green"
          progressValue={data.filterPass}
        />
        <KpiCard 
          title="파싱 성공률" 
          value={data.parseSuccess} 
          unit="%" 
          showProgress 
          progressColor="green"
          progressValue={data.parseSuccess}
        />
        <KpiCard 
          title="체크섬 오류율" 
          value={data.checksumFail} 
          unit="" 
        />
        <KpiCard 
          title="추정 패킷 손실" 
          value={data.packetLoss} 
          unit="pkts" 
        />
        <KpiCard 
          title="가용성 (5분)" 
          value={data.availability5min} 
          unit="%" 
          showProgress 
          progressColor="green"
          progressValue={data.availability5min}
        />
        <KpiCard 
          title="가용성 (1시간)" 
          value={data.availability1hour} 
          unit="%" 
          showProgress 
          progressColor="green"
          progressValue={data.availability1hour}
        />
        <KpiCard 
          title="지터 (P95/P99)" 
          value={`${data.jitterP95} / ${data.jitterP99}`} 
          unit="ms" 
        />
      </div>

      {/* Main Content - 2 Columns */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Left Column */}
        <div className="flex flex-col gap-6">
          {/* 현재 운용 상태 */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <div className="w-1 h-4 bg-blue-600 rounded-full"></div>
                현재 운용 상태
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg p-4 border border-emerald-200">
                <div className="text-xs font-medium text-emerald-700 mb-2">운용모드</div>
                <div className="text-base font-bold text-emerald-900">{data.operationalMode}</div>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
                <div className="text-xs font-medium text-blue-700 mb-2">운용권한</div>
                <div className="text-base font-bold text-blue-900">{data.operationalAuthority}</div>
              </div>
              <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg p-4 border border-slate-200">
                <div className="text-xs font-medium text-slate-700 mb-2">주행상태</div>
                <div className="text-base font-bold text-slate-900">{data.drivingState}</div>
              </div>
            </CardContent>
          </Card>

          {/* 비상정지/이상 원인 */}
          <Card className="shadow-sm border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <div className="w-1 h-4 bg-amber-600 rounded-full"></div>
                비상정지/이상 원인
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1.5">
                {Object.entries(data.emergencyStatus).map(([key, value]) => (
                  <div 
                    key={key} 
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                      value 
                        ? "bg-red-50 border border-red-200" 
                        : "bg-slate-50 border border-transparent hover:border-slate-200"
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      value ? "bg-red-500 animate-pulse shadow-lg shadow-red-500/50" : "bg-slate-300"
                    }`}></div>
                    <span className={`text-xs font-medium ${
                      value ? "text-red-700" : "text-slate-600"
                    }`}>
                      {key}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">
          {/* 장치 연결 상태 */}
          <Card className="shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">장치 연결 상태</CardTitle>
                <span className="text-xs text-gray-500">전체: 9/10 개, 정상: 1s</span>
              </div>
            </CardHeader>
            <CardContent>
              <DeviceGrid devices={data.devices} />
            </CardContent>
          </Card>

          {/* 통신 품질 차트 */}
          <TimeSeriesChart 
            title="통신 품질 차트" 
            data={data.combinedData}
            showPps={true}
            showJitter={true}
            p95={data.jitterP95}
            p99={data.jitterP99}
          />
          
          {/* 가용성 타임라인 */}
          <AvailabilityTimeline segments={data.availabilitySegments} duration={3600} />
        </div>
      </div>

      {/* Bottom Full Width - Log Table */}
      <LogTable 
        logs={data.logs} 
        maxRows={200}
        isPaused={isPaused}
        onPauseToggle={handlePauseToggle}
        onClear={handleClearLogs}
      />
    </div>
  );
}