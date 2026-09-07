"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { SearchInput } from "@/components/ui/SearchInput";
import { Spinner } from "@/components/ui/Spinner";

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  plan: string;
  credit_balance: number;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

function useUsers(search: string, page: number) {
  return useQuery({
    queryKey: ["admin", "users", search, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (search) params.search = search;
      const { data } = await api.get("/admin/users", { params });
      return data as { data: AdminUser[]; total: number };
    },
  });
}

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading } = useUsers(search, 1);
  const qc = useQueryClient();

  const toggle = useMutation({
    mutationFn: async ({ id, field, value }: { id: string; field: string; value: boolean }) => {
      await api.patch(`/admin/users/${id}`, { [field]: value });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <div className="p-6">
      <h1 className="mb-4 text-xl font-bold text-gray-900">Users ({data?.total ?? 0})</h1>
      <SearchInput value={search} onChange={setSearch} placeholder="Search by email or name..." className="mb-4 max-w-md" />

      {isLoading && <Spinner size="sm" />}

      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Plan</th>
                <th className="px-3 py-2">Credits</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((u) => (
                <tr key={u.id} className="border-t border-gray-100">
                  <td className="px-3 py-2 text-gray-900">{u.email}</td>
                  <td className="px-3 py-2">{u.full_name}</td>
                  <td className="px-3 py-2 capitalize">{u.plan}</td>
                  <td className="px-3 py-2">{u.credit_balance}</td>
                  <td className="px-3 py-2">
                    {u.is_active ? (
                      <Badge variant="active">Active</Badge>
                    ) : (
                      <Badge variant="superseded">Inactive</Badge>
                    )}
                    {u.is_admin && <Badge variant="high" className="ml-1">Admin</Badge>}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => toggle.mutate({ id: u.id, field: "is_active", value: !u.is_active })}
                      className="text-xs text-navy-600 hover:underline"
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
