/**
 * Shared layout for auth pages (register, login, verify).
 * Centered card with RegPulse branding.
 */

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-navy-50 to-gray-100 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-navy-800">RegPulse</h1>
          <p className="mt-1 text-sm text-gray-500">RBI Regulatory Intelligence</p>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-lg">{children}</div>
      </div>
    </div>
  );
}
