"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import FileUpload from "@/components/FileUpload";

export default function NewRole() {
  const router = useRouter();
  const [roleName, setRoleName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!roleName.trim()) {
      setError("Please enter a role name");
      return;
    }
    
    if (files.length === 0) {
      setError("Please upload at least one CSV file");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("run_name", roleName);
      formData.append("role_label", roleName);
      
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch("/api/run", {
        method: "POST",
        body: formData,
      });

      if (response.redirected) {
        // Extract run_id from redirect URL
        const redirectUrl = response.url;
        const runId = redirectUrl.split("/").pop();
        router.push(`/role/${runId}`);
      } else if (response.ok) {
        // Try to parse response for run_id
        const data = await response.json();
        if (data.run_id) {
          router.push(`/role/${data.run_id}`);
        }
      } else {
        setError("Failed to create role. Please try again.");
        setUploading(false);
      }
    } catch (err) {
      console.error("Upload error:", err);
      setError("An error occurred while uploading. Please try again.");
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <a
          href="/"
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          ← Back to Home
        </a>
      </div>

      <div className="bg-white shadow-lg rounded-lg p-8">
        <h1 className="text-3xl font-bold text-black mb-2">
          Build Your Candidate List
        </h1>
        <p className="text-black mb-8">Upload candidate data and let our system handle the rest</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="roleName"
              className="block text-sm font-semibold text-black mb-2"
            >
              Role Name
            </label>
            <input
              type="text"
              id="roleName"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              placeholder="e.g., Mandrel - Founding Engineer"
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 text-black text-base"
              disabled={uploading}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-black mb-2">
              Upload Candidate Files
            </label>
            <p className="text-sm text-black mb-3">
              Drag and drop your CSV files here, or click to browse
            </p>
            <FileUpload
              files={files}
              onFilesChange={setFiles}
              disabled={uploading}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={uploading || !roleName.trim() || files.length === 0}
              className="flex-1 bg-blue-600 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
            >
              {uploading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                  Processing...
                </span>
              ) : (
                "Process & Standardize"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
