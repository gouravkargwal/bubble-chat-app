import React from "react";
import Image from "next/image";

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
      <Image
        src="/logo.svg"
        alt="Cookd"
        width={size}
        height={size}
        className="pointer-events-none select-none"
        priority
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
