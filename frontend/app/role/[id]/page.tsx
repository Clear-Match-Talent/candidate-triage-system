"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";

interface RunStatus {
  run_id: string;
  created_at: number;
  run_name: string;
  role_label: string;
  state: string;
  message: string;
  outputs?: {
    standardized?: string;
    evaluated?: string;
    proceed?: string;
    human_review?: string;
    dismiss?: string;
    duplicates?: string;
  };
}

export default function RoleDetail({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const router = useRouter();
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchRunStatus();
    
    // Poll every 2 seconds while running
    const interval = setInterval(() => {
      if (runStatus?.state === "running" || runStatus?.state === "queued") {
        fetchRunStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [resolvedParams.id, runStatus?.state]);

  const fetchRunStatus = async () => {
    try {
      const response = await fetch(`/api/runs/${resolvedParams.id}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          setError("Run not found");
        } else {
          setError("Failed to fetch run status");
        }
        setLoading(false);
        return;
      }

      const data = await response.json();
      setRunStatus(data);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching run status:", err);
      setError("An error occurred while fetching status");
      setLoading(false);
    }
  };

  const downloadFile = (kind: string) => {
    window.location.href = `/api/download/${resolvedParams.id}/${kind}`;
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-medium">Error</h3>
          <p className="text-red-600 mt-2">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!runStatus) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-yellow-800 font-medium">Run not found</h3>
          <button
            onClick={() => router.push("/")}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <a
          href="/"
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          ← Back to Home
        </a>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-900">
            {runStatus.role_label || runStatus.run_name}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Created: {new Date(runStatus.created_at * 1000).toLocaleString()}
          </p>
        </div>

        <div className="px-6 py-4">
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-lg font-medium text-gray-900">Status:</h2>
            <span
              className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full ${
                runStatus.state === "done"
                  ? "bg-green-100 text-green-800"
                  : runStatus.state === "error"
                  ? "bg-red-100 text-red-800"
                  : runStatus.state === "running"
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {runStatus.state.toUpperCase()}
            </span>
          </div>

          {runStatus.message && (
            <div className="mb-6">
              <p className="text-gray-700">{runStatus.message}</p>
            </div>
          )}

          {(runStatus.state === "running" || runStatus.state === "queued") && (
            <div className="mb-6">
              <div className="flex items-center gap-3">
                <svg
                  className="animate-spin h-5 w-5 text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <span className="text-gray-600">Processing... This may take a few minutes.</span>
              </div>
            </div>
          )}

          {runStatus.state === "done" && runStatus.outputs && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Download Results
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {runStatus.outputs.proceed && (
                  <button
                    onClick={() => downloadFile("proceed")}
                    className="flex items-center justify-between px-4 py-3 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <span className="font-medium text-green-900">✅ Proceed</span>
                    <svg
                      className="h-5 w-5 text-green-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>
                )}
                
                {runStatus.outputs.human_review && (
                  <button
                    onClick={() => downloadFile("human_review")}
                    className="flex items-center justify-between px-4 py-3 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100"
                  >
                    <span className="font-medium text-yellow-900">⚠️ Human Review</span>
                    <svg
                      className="h-5 w-5 text-yellow-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>
                )}
                
                {runStatus.outputs.dismiss && (
                  <button
                    onClick={() => downloadFile("dismiss")}
                    className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
                  >
                    <span className="font-medium text-red-900">❌ Dismiss</span>
                    <svg
                      className="h-5 w-5 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>
                )}
                
                {runStatus.outputs.evaluated && (
                  <button
                    onClick={() => downloadFile("evaluated")}
                    className="flex items-center justify-between px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100"
                  >
                    <span className="font-medium text-blue-900">📊 All Results</span>
                    <svg
                      className="h-5 w-5 text-blue-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
