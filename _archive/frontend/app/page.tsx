"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface Role {
  run_id: string;
  run_name: string;
  role_label: string;
  created_at: number;
  state: string;
  message: string;
}

export default function Home() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      const res = await fetch("/api/runs");
      if (res.ok) {
        const data = await res.json();
        setRoles(data);
      }
      setLoading(false);
    } catch (error) {
      console.error("Error fetching roles:", error);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-black mb-4">
          Clear Match Talent
        </h1>
        <h2 className="text-2xl font-semibold text-blue-600 mb-3">
          Candidate List Builder
        </h2>
        <p className="text-lg text-black mb-8">
          Upload candidate data, filter, and build your perfect hiring list
        </p>
        <Link
          href="/role/new"
          className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-semibold rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 shadow-lg hover:shadow-xl transition-all"
        >
          ✨ Build New List
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <div className="bg-white shadow-lg overflow-hidden sm:rounded-lg border-2 border-gray-200">
          <div className="px-6 py-5 sm:px-8 bg-blue-50 border-b-2 border-gray-200">
            <h2 className="text-xl font-bold text-black">Recent Lists</h2>
            <p className="mt-1 text-sm text-black">
              View and manage your candidate lists
            </p>
          </div>
          {roles.length === 0 ? (
            <div className="px-4 py-12 text-center text-black">
              No lists yet. Create one to get started!
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {roles.map((role) => (
                <li key={role.run_id}>
                  <Link
                    href={`/role/${role.run_id}`}
                    className="block hover:bg-blue-50 px-6 py-5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-base font-semibold text-blue-600">
                          {role.role_label || role.run_name}
                        </p>
                        <p className="text-sm text-black mt-1">
                          Created: {new Date(role.created_at * 1000).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            role.state === "done"
                              ? "bg-green-100 text-green-800"
                              : role.state === "error"
                              ? "bg-red-100 text-red-800"
                              : role.state === "running"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {role.state}
                        </span>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
