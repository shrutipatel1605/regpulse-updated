/**
 * 6-digit OTP input — one box per digit.
 *
 * - Auto-advances focus on input.
 * - Backspace moves to previous box.
 * - Paste fills all 6 digits.
 * - Auto-submits when last digit is entered.
 */

"use client";

import { useCallback, useRef } from "react";

interface OTPInputProps {
  value: string;
  onChange: (otp: string) => void;
  onComplete: (otp: string) => void;
  disabled?: boolean;
}

const OTP_LENGTH = 6;

export default function OTPInput({ value, onChange, onComplete, disabled = false }: OTPInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const digits = value.padEnd(OTP_LENGTH, "").slice(0, OTP_LENGTH).split("");

  const focusInput = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(index, OTP_LENGTH - 1));
    inputRefs.current[clamped]?.focus();
  }, []);

  const handleChange = useCallback(
    (index: number, inputValue: string) => {
      // Only accept digits
      const digit = inputValue.replace(/\D/g, "").slice(-1);
      if (!digit) return;

      const newDigits = [...digits];
      newDigits[index] = digit;
      const newOtp = newDigits.join("");
      onChange(newOtp);

      if (index < OTP_LENGTH - 1) {
        focusInput(index + 1);
      }

      // Auto-submit when all 6 digits filled
      if (newOtp.replace(/\s/g, "").length === OTP_LENGTH) {
        onComplete(newOtp);
      }
    },
    [digits, onChange, onComplete, focusInput],
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace") {
        e.preventDefault();
        const newDigits = [...digits];
        if (digits[index]) {
          // Clear current digit
          newDigits[index] = "";
          onChange(newDigits.join(""));
        } else if (index > 0) {
          // Move to previous and clear it
          newDigits[index - 1] = "";
          onChange(newDigits.join(""));
          focusInput(index - 1);
        }
      } else if (e.key === "ArrowLeft" && index > 0) {
        focusInput(index - 1);
      } else if (e.key === "ArrowRight" && index < OTP_LENGTH - 1) {
        focusInput(index + 1);
      }
    },
    [digits, onChange, focusInput],
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
      if (!pasted) return;

      onChange(pasted.padEnd(OTP_LENGTH, "").slice(0, OTP_LENGTH));

      // Focus last filled input
      const lastIndex = Math.min(pasted.length, OTP_LENGTH) - 1;
      focusInput(lastIndex);

      if (pasted.length >= OTP_LENGTH) {
        onComplete(pasted.slice(0, OTP_LENGTH));
      }
    },
    [onChange, onComplete, focusInput],
  );

  return (
    <div className="flex items-center justify-center gap-3">
      {Array.from({ length: OTP_LENGTH }).map((_, i) => (
        <input
          key={i}
          ref={(el) => {
            inputRefs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={1}
          value={digits[i]?.trim() || ""}
          disabled={disabled}
          className="h-14 w-12 rounded-lg border-2 border-gray-300 bg-white text-center text-2xl font-semibold
            text-navy-800 transition-colors
            focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-200
            disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
        />
      ))}
    </div>
  );
}
