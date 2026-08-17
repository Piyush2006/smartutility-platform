"use client";

import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter, useSearchParams } from "next/navigation";
import { setPassword } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";

interface SetPasswordForm {
  password: string;
  confirm: string;
}

function SetPasswordFormInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SetPasswordForm>();

  async function onSubmit(values: SetPasswordForm) {
    if (!token) return;
    setServerError(null);
    try {
      await setPassword(token, values.password);
      router.push("/dashboard");
    } catch (error) {
      setServerError(getErrorMessage(error, "This invite link is invalid or has expired."));
    }
  }

  if (!token) {
    return (
      <p className="text-sm text-red-600">
        This link is missing its invite token. Ask whoever invited you to send a new one.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-slate-700">
          New Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register("password", { required: "Enter a password.", minLength: { value: 8, message: "At least 8 characters." } })}
          className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
      </div>

      <div>
        <label htmlFor="confirm" className="block text-sm font-medium text-slate-700">
          Confirm Password
        </label>
        <input
          id="confirm"
          type="password"
          autoComplete="new-password"
          {...register("confirm", { required: "Confirm your password.", validate: (v) => v === watch("password") || "Passwords don't match." })}
          className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        {errors.confirm && <p className="mt-1 text-xs text-red-600">{errors.confirm.message}</p>}
      </div>

      {serverError && <p className="text-sm text-red-600">{serverError}</p>}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
      >
        {isSubmitting ? "Setting password..." : "Set Password & Sign In"}
      </button>
    </form>
  );
}

export default function SetPasswordPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Welcome to UtilityOS</h1>
        <p className="mt-1 text-sm text-slate-500">Set a password to activate your account.</p>
        <Suspense fallback={<p className="mt-6 text-sm text-slate-400">Loading…</p>}>
          <SetPasswordFormInner />
        </Suspense>
      </div>
    </main>
  );
}
