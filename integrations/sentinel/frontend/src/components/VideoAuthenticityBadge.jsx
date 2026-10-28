import React from 'react';

/**
 * Video Authenticity Badge matching SENTINEL Tailwind styling.
 */
export default function VideoAuthenticityBadge({ status, score, reportUrl }) {
    if (!status) return null;

    let badgeClass = "bg-gray-100 text-gray-800 border-gray-300";
    let label = "Screening Pending";

    if (status === "allowed" || status === "likely_authentic") {
        badgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
        label = "Likely Authentic";
    } else if (status === "review" || status === "needs_review") {
        badgeClass = "bg-amber-50 text-amber-700 border-amber-200";
        label = "Needs Review";
    } else if (status === "held" || status === "likely_manipulated") {
        badgeClass = "bg-rose-50 text-rose-700 border-rose-200";
        label = "Likely Manipulated";
    }

    return (
        <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border ${badgeClass}`}>
            <span>{label}</span>
            {score !== undefined && score !== null && (
                <span className="font-mono opacity-80">({(score * 100).toFixed(0)}%)</span>
            )}
            {reportUrl && (
                <a 
                    href={reportUrl} 
                    target="_blank" 
                    rel="noreferrer"
                    className="underline hover:opacity-80 ml-1"
                >
                    Evidence
                </a>
            )}
        </div>
    );
}

