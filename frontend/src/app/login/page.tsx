"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { login } from "@/lib/auth";
import { getErrorMessage } from "@/lib/errors";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(1, "Enter your password."),
});

type LoginForm = z.infer<typeof loginSchema>;

const DEMO_EMAIL = "utilityadmin@demo-water.dev";
const DEMO_PASSWORD = "ChangeMe123!";

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  function fillDemoCreds() {
    setValue("email", DEMO_EMAIL, { shouldValidate: true });
    setValue("password", DEMO_PASSWORD, { shouldValidate: true });
  }

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      router.push("/dashboard");
    } catch (error) {
      setServerError(getErrorMessage(error, "Invalid email or password."));
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">UtilityOS</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in to your utility account.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              {...register("email")}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
          </div>

          {serverError && <p className="text-sm text-red-600">{serverError}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Demo Login</p>
          <p className="mt-1 font-mono text-xs text-slate-700">{DEMO_EMAIL}</p>
          <p className="font-mono text-xs text-slate-700">{DEMO_PASSWORD}</p>
          <button
            type="button"
            onClick={fillDemoCreds}
            className="mt-2 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            Fill demo credentials
          </button>
          <p className="mt-2 text-xs text-slate-400">
            Full Utility Admin access to a shared public demo tenant -- data here can be
            changed by other visitors and isn&apos;t reset automatically. More accounts
            (CSR, Meter Reader, Consumer, ...) are listed in SEED_CREDENTIALS.md in the repo.
          </p>
        </div>
      </div>
    </main>
  );
}
