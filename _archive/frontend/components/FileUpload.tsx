"use client";

import { useCallback } from "react";

interface FileUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

export default function FileUpload({ files, onFilesChange, disabled }: FileUploadProps) {
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (disabled) return;

      const droppedFiles = Array.from(e.dataTransfer.files).filter(
        (file) => file.name.endsWith(".csv")
      );
      
      if (droppedFiles.length > 0) {
        onFilesChange([...files, ...droppedFiles]);
      }
    },
    [files, onFilesChange, disabled]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (disabled) return;
      
      const selectedFiles = Array.from(e.target.files || []).filter(
        (file) => file.name.endsWith(".csv")
      );
      
      if (selectedFiles.length > 0) {
        onFilesChange([...files, ...selectedFiles]);
      }
    },
    [files, onFilesChange, disabled]
  );

  const removeFile = useCallback(
    (index: number) => {
      if (disabled) return;
      const newFiles = files.filter((_, i) => i !== index);
      onFilesChange(newFiles);
    },
    [files, onFilesChange, disabled]
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className={`border-2 border-dashed rounded-lg p-8 text-center ${
          disabled
            ? "border-gray-200 bg-gray-50 cursor-not-allowed"
            : "border-blue-300 bg-blue-50 hover:bg-blue-100 cursor-pointer"
        }`}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          accept=".csv"
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled}
        />
        <label
          htmlFor="file-upload"
          className={`${disabled ? "cursor-not-allowed" : "cursor-pointer"}`}
        >
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="mt-2 text-sm text-black">
            <span className="font-semibold text-blue-600">Click to upload</span>{" "}
            or drag and drop
          </p>
          <p className="mt-1 text-xs text-black opacity-70">CSV files only</p>
        </label>
      </div>

      {files.length > 0 && (
        <div className="bg-white border-2 border-gray-200 rounded-lg overflow-hidden shadow-sm">
          <div className="px-4 py-3 bg-blue-50 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-black">
              Uploaded Files ({files.length})
            </h3>
          </div>
          <ul className="divide-y divide-gray-200">
            {files.map((file, index) => (
              <li key={index} className="px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-black truncate">
                    {file.name}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <p className="text-xs text-black opacity-70">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  disabled={disabled}
                  className={`ml-4 text-red-600 hover:text-red-800 text-sm font-medium ${
                    disabled ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
