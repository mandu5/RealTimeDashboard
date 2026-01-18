import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/app/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Pause, Play, Trash2, ArrowDown } from "lucide-react";
import { useState, useEffect, useRef } from "react";

interface LogEntry {
  time: string;
  seq: number;
  msg_code: string;
  parse_ok: boolean;
  checksum_ok: boolean;
  mode: string;
  authority: string;
  notes: string;
}

interface LogTableProps {
  logs: LogEntry[];
  maxRows?: number;
  isPaused: boolean;
  onPauseToggle: () => void;
  onClear: () => void;
}

export function LogTable({ logs, maxRows = 50, isPaused, onPauseToggle, onClear }: LogTableProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const displayLogs = logs.slice(0, maxRows);

  useEffect(() => {
    if (autoScroll && scrollRef.current && !isPaused) {
      scrollRef.current.scrollTop = 0; // Scroll to top for newest entries
    }
  }, [logs, autoScroll, isPaused]);

  return (
    <Card className="shadow-sm border-slate-200">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <div className="w-1 h-4 bg-purple-600 rounded-full"></div>
            로그/이벤트 테이블 (최근 {displayLogs.length}개)
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoScroll(!autoScroll)}
              className={`text-xs h-8 border-slate-200 ${autoScroll ? 'bg-blue-50 border-blue-300 text-blue-700' : 'hover:bg-slate-50'}`}
            >
              <ArrowDown className={`w-3.5 h-3.5 mr-1.5 ${autoScroll ? 'animate-bounce' : ''}`} />
              Auto-scroll
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onPauseToggle}
              className={`text-xs h-8 border-slate-200 ${isPaused ? 'bg-amber-50 border-amber-300 text-amber-700' : 'hover:bg-slate-50'}`}
            >
              {isPaused ? <Play className="w-3.5 h-3.5 mr-1.5" /> : <Pause className="w-3.5 h-3.5 mr-1.5" />}
              {isPaused ? 'Resume' : 'Pause'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onClear}
              className="text-xs h-8 border-slate-200 hover:bg-red-50 hover:border-red-300 hover:text-red-700"
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Clear
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div ref={scrollRef} className="max-h-96 overflow-y-auto border border-slate-200 rounded-lg bg-white">
          <Table>
            <TableHeader className="sticky top-0 bg-gradient-to-r from-slate-50 to-slate-100 z-10 border-b border-slate-200">
              <TableRow>
                <TableHead className="w-[120px] font-semibold text-slate-700">Time</TableHead>
                <TableHead className="w-[80px] font-semibold text-slate-700">Seq</TableHead>
                <TableHead className="w-[100px] font-semibold text-slate-700">Msg Code</TableHead>
                <TableHead className="w-[80px] font-semibold text-slate-700">Parse OK</TableHead>
                <TableHead className="w-[100px] font-semibold text-slate-700">Checksum OK</TableHead>
                <TableHead className="w-[100px] font-semibold text-slate-700">Mode</TableHead>
                <TableHead className="w-[120px] font-semibold text-slate-700">Authority</TableHead>
                <TableHead className="font-semibold text-slate-700">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayLogs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-slate-400 py-12">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                        <span className="text-2xl">📋</span>
                      </div>
                      <span className="text-sm font-medium">No logs available</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                displayLogs.map((log, idx) => (
                  <TableRow 
                    key={`${log.seq}-${log.time}`}
                    className={`transition-all duration-300 ${
                      idx === 0 && !isPaused 
                        ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-l-2 border-l-blue-500' 
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <TableCell className="text-xs font-mono text-slate-600">{log.time}</TableCell>
                    <TableCell className="text-xs font-bold text-slate-800">{log.seq}</TableCell>
                    <TableCell className="text-xs font-mono bg-slate-100 text-slate-700">{log.msg_code}</TableCell>
                    <TableCell>
                      <Badge 
                        variant={log.parse_ok ? "default" : "destructive"} 
                        className={`text-xs font-bold ${
                          log.parse_ok 
                            ? 'bg-emerald-100 text-emerald-700 border border-emerald-300' 
                            : 'bg-red-100 text-red-700 border border-red-300'
                        }`}
                      >
                        {log.parse_ok ? "✓" : "✗"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={log.checksum_ok ? "default" : "destructive"} 
                        className={`text-xs font-bold ${
                          log.checksum_ok 
                            ? 'bg-emerald-100 text-emerald-700 border border-emerald-300' 
                            : 'bg-red-100 text-red-700 border border-red-300'
                        }`}
                      >
                        {log.checksum_ok ? "✓" : "✗"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs font-medium text-slate-700">{log.mode}</TableCell>
                    <TableCell className="text-xs font-medium text-slate-700">{log.authority}</TableCell>
                    <TableCell className="text-xs">
                      {log.notes && (
                        <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-300">
                          {log.notes}
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}