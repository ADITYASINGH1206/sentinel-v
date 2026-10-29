import React, { useState } from 'react';
import {
  ListFilter,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Layers,
  Search,
  CheckCircle2,
} from 'lucide-react';
import { BandChip, DecisionBand } from '../components/BandChip';
import { REQUIRED_DISCLAIMER } from '../copy/forbidden';

interface QueueItem {
  id: string;
  created_at: string;
  band: DecisionBand;
  p_bal: number;
  duration_s: number;
  policy: string;
  reviewed: boolean;
}

const SAMPLE_QUEUE_ITEMS: QueueItem[] = [
  {
    id: 'an_queue_8841',
    created_at: '2026-10-29 07:15',
    band: 'needs_review',
    p_bal: 0.64,
    duration_s: 14.2,
    policy: 'pol_strict_v3',
    reviewed: false,
  },
  {
    id: 'an_queue_8842',
    created_at: '2026-10-29 07:22',
    band: 'needs_review',
    p_bal: 0.58,
    duration_s: 22.8,
    policy: 'pol_strict_v3',
    reviewed: false,
  },
  {
    id: 'an_queue_8843',
    created_at: '2026-10-29 07:30',
    band: 'likely_manipulated',
    p_bal: 0.88,
    duration_s: 9.5,
    policy: 'pol_strict_v3',
    reviewed: false,
  },
  {
    id: 'an_queue_8839',
    created_at: '2026-10-29 06:45',
    band: 'likely_authentic',
    p_bal: 0.12,
    duration_s: 31.0,
    policy: 'pol_strict_v3',
    reviewed: true,
  },
];

interface DashboardProps {
  onStartReview: (id?: string) => void;
  onViewCase: (id: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onStartReview, onViewCase }) => {
  const [filterBand, setFilterBand] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredItems = SAMPLE_QUEUE_ITEMS.filter((item) => {
    if (filterBand !== 'all' && item.band !== filterBand) return false;
    if (searchQuery && !item.id.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const pendingCount = SAMPLE_QUEUE_ITEMS.filter((i) => !i.reviewed).length;
  const reviewedCount = SAMPLE_QUEUE_ITEMS.filter((i) => i.reviewed).length;

  return (
    <div className="flex flex-col min-h-screen bg-bg text-text">
      {/* Header */}
      <header className="border-b border-border bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold tracking-wider text-accent text-lg">SENTINEL-V</span>
          <span className="text-muted text-sm">&bull;</span>
          <span className="text-sm font-medium text-text">Reviewer Console</span>
        </div>

        <button
          onClick={() => onStartReview()}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-xs font-semibold hover:opacity-90 shadow-sm transition-opacity"
        >
          <span>Start Review Queue ({pendingCount})</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">
        {/* Metric Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted">Pending Review</p>
              <p className="text-xl font-bold font-mono text-text">{pendingCount}</p>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted">Reviewed Today</p>
              <p className="text-xl font-bold font-mono text-text">{reviewedCount}</p>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted">Active Policy</p>
              <p className="text-sm font-semibold font-mono text-text">pol_strict_v3</p>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted">Avg Triage Speed</p>
              <p className="text-xl font-bold font-mono text-text">8.4s</p>
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <ListFilter className="w-4 h-4 text-muted" />
            <span className="text-xs text-muted font-medium">Filter:</span>
            <select
              value={filterBand}
              onChange={(e) => setFilterBand(e.target.value)}
              aria-label="Filter queue by decision band"
              className="text-xs p-1.5 bg-bg border border-border rounded text-text focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="all">All Decision Bands</option>
              <option value="needs_review">Needs Review</option>
              <option value="likely_manipulated">Likely Manipulated</option>
              <option value="likely_authentic">Likely Authentic</option>
            </select>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-muted absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search analysis ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs pl-8 pr-3 py-2 bg-bg border border-border rounded focus:outline-none focus:ring-1 focus:ring-accent text-text"
            />
          </div>
        </div>

        {/* Queue Table */}
        <div className="bg-surface border border-border rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/40 text-muted font-medium">
                <th className="py-3 px-4">Analysis ID</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Calibrated Band</th>
                <th className="py-3 px-4">Calibrated Score</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-text">{item.id}</td>
                  <td className="py-3 px-4 text-muted">{item.created_at}</td>
                  <td className="py-3 px-4">
                    <BandChip band={item.band} size="sm" />
                  </td>
                  <td className="py-3 px-4 font-mono font-bold text-text">{item.p_bal.toFixed(2)}</td>
                  <td className="py-3 px-4 text-muted">{item.duration_s}s</td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        item.reviewed
                          ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                          : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300'
                      }`}
                    >
                      {item.reviewed ? 'Reviewed' : 'Pending'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onViewCase(item.id)}
                        className="px-2.5 py-1 text-muted hover:text-text rounded border border-border hover:bg-bg transition-colors"
                      >
                        Details
                      </button>
                      {!item.reviewed && (
                        <button
                          onClick={() => onStartReview(item.id)}
                          className="px-2.5 py-1 bg-accent text-white rounded font-medium hover:opacity-90 transition-opacity"
                        >
                          Review
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mandatory Screening Disclaimer */}
        <div className="p-3 bg-surface border border-border rounded-lg text-xs text-muted italic text-center">
          {REQUIRED_DISCLAIMER}
        </div>
      </main>
    </div>
  );
};

