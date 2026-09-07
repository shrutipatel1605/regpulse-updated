"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";

interface PromptVersion {
  id: string;
  version_tag: string;
  prompt_text: string;
  is_active: boolean;
  created_at: string;
}

function usePrompts() {
  return useQuery({
    queryKey: ["admin", "prompts"],
    queryFn: async () => {
      const { data } = await api.get("/admin/prompts");
      return data as { data: PromptVersion[] };
    },
  });
}

export default function PromptsPage() {
  const { data, isLoading } = usePrompts();
  const qc = useQueryClient();
  const [tag, setTag] = useState("");
  const [text, setText] = useState("");

  const create = useMutation({
    mutationFn: async () => {
      await api.post("/admin/prompts", { version_tag: tag, prompt_text: text });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "prompts"] });
      setTag("");
      setText("");
    },
  });

  const activate = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/admin/prompts/${id}/activate`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "prompts"] }),
  });

  if (isLoading) return <div className="flex justify-center p-20"><Spinner size="lg" /></div>;

  return (
    <div className="p-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">Prompt Versions</h1>

      {/* Create form */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Create New Version</h2>
        <input
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          placeholder="Version tag (e.g. v2.1)"
          className="mb-2 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Prompt text..."
          rows={4}
          className="mb-2 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => create.mutate()}
          disabled={!tag || !text || create.isPending}
          className="rounded bg-navy-700 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Create & Activate
        </button>
      </div>

      {/* List */}
      <div className="space-y-3">
        {data?.data.map((p) => (
          <div key={p.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{p.version_tag}</span>
                {p.is_active && <Badge variant="active">Active</Badge>}
              </div>
              {!p.is_active && (
                <button
                  onClick={() => activate.mutate(p.id)}
                  className="rounded border border-gray-300 px-3 py-1 text-xs"
                >
                  Activate
                </button>
              )}
            </div>
            <p className="mt-2 text-xs text-gray-500 line-clamp-3">{p.prompt_text}</p>
            <p className="mt-1 text-xs text-gray-400">
              {new Date(p.created_at).toLocaleDateString("en-IN")}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
