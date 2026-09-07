"use client";

import { useState, useRef, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import toast from "react-hot-toast";

interface ManualUpload {
  id: string;
  admin_id: string;
  filename: string;
  file_size_bytes: number;
  status: string;
  document_id: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

const DOC_TYPES = [
  "CIRCULAR",
  "MASTER_DIRECTION",
  "NOTIFICATION",
  "PRESS_RELEASE",
  "GUIDELINE",
  "OTHER",
] as const;

function useUploads() {
  return useQuery({
    queryKey: ["admin", "uploads"],
    queryFn: async () => {
      const { data } = await api.get("/admin/uploads", {
        params: { page: 1, page_size: 50 },
      });
      return data as { data: ManualUpload[]; total: number };
    },
    refetchInterval: (query) => {
      const uploads = query.state.data?.data ?? [];
      const hasPending = uploads.some(
        (u) => u.status === "PENDING" || u.status === "PROCESSING"
      );
      return hasPending ? 5000 : false;
    },
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusVariant(status: string) {
  switch (status) {
    case "COMPLETED":
      return "active" as const;
    case "FAILED":
      return "high" as const;
    case "PROCESSING":
      return "medium" as const;
    default:
      return "low" as const;
  }
}

export default function UploadsPage() {
  const { data, isLoading } = useUploads();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState<string>("CIRCULAR");
  const [dragOver, setDragOver] = useState(false);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("doc_type", docType);
      const { data } = await api.post("/admin/uploads/pdf", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || "PDF queued");
        setTitle("");
        if (fileRef.current) fileRef.current.value = "";
      } else {
        toast.error(data.message || "Upload failed");
      }
      qc.invalidateQueries({ queryKey: ["admin", "uploads"] });
    },
    onError: () => {
      toast.error("Upload failed");
    },
  });

  const handleFile = useCallback(
    (file: File) => {
      if (file.type !== "application/pdf") {
        toast.error("Only PDF files are accepted");
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        toast.error("File too large (max 20MB)");
        return;
      }
      upload.mutate(file);
    },
    [upload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  if (isLoading) {
    return (
      <div className="flex justify-center p-20">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900 dark:text-gray-100">
        PDF Upload
      </h1>

      {/* Upload form */}
      <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
              Title (optional — extracted from PDF if blank)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Master Direction on KYC"
              className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
              Document Type
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            >
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
            dragOver
              ? "border-navy-500 bg-navy-50 dark:bg-navy-900/20"
              : "border-gray-300 hover:border-gray-400 dark:border-gray-600"
          }`}
          onClick={() => fileRef.current?.click()}
        >
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {upload.isPending
              ? "Uploading..."
              : "Drop a PDF here or click to select"}
          </p>
          <p className="mt-1 text-xs text-gray-400">Max 20 MB</p>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      </div>

      {/* Upload history */}
      <h2 className="mb-3 text-lg font-semibold text-gray-800 dark:text-gray-200">
        Recent Uploads
      </h2>
      <div className="space-y-3">
        {data?.data.length === 0 && (
          <p className="text-sm text-gray-500">No uploads yet.</p>
        )}
        {data?.data.map((u) => (
          <div
            key={u.id}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Badge variant={statusVariant(u.status)}>{u.status}</Badge>
                <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                  {u.filename}
                </span>
                <span className="text-xs text-gray-500">
                  {formatBytes(u.file_size_bytes)}
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {new Date(u.created_at).toLocaleString("en-IN")}
              </span>
            </div>
            {u.document_id && (
              <p className="mt-2 text-xs text-green-700 dark:text-green-400">
                Circular created:{" "}
                <a
                  href={`/library/${u.document_id}`}
                  className="underline hover:text-green-600"
                >
                  {u.document_id.slice(0, 8)}...
                </a>
              </p>
            )}
            {u.error_message && (
              <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                {u.error_message}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
