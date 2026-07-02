import React from "react";

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 48, className = "" }: LogoProps) {
  return (
    <div
      className={`inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 108 108"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* White circle background */}
        <circle cx="54" cy="54" r="28" fill="white" />
        {/* Geometric 'C' cutout */}
        <path
          d="M63.73,45.51 A12,12 0 1,0 63.73,62.49 L61.31,60.07 A8.6,8.6 0 1,1 61.31,47.93 Z"
          fill="black"
          fillRule="evenodd"
        />
      </svg>
    </div>
  );
}

export function LogoMark({ size = 16, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={`inline-flex items-center justify-center rounded-full bg-nothing-white ${className}`}
      style={{ width: size, height: size }}
    >
      <div
        className="rounded-full"
        style={{
          width: size * 0.55,
          height: size * 0.55,
          backgroundColor: "#000000",
          clipPath: "polygon(52% 0%, 100% 50%, 52% 100%, 30% 64%, 30% 36%)",
        }}
      />
    </div>
  );
}

export function StatusDot({ active = true, className = "" }) {
  return (
    <span
      className={`inline-block rounded-full ${
        active ? "bg-neon-red animate-blink" : "bg-nothing-text-tertiary"
      } ${className}`}
      style={{ width: 8, height: 8 }}
    />
  );
}
