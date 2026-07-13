"use client";

import React, { type ReactNode, useEffect, useRef, useState } from "react";

// ── Scroll-triggered reveal wrapper (CSS-only) ──
// Lightweight: uses IntersectionObserver + CSS transitions instead of framer-motion.

interface AnimatedSectionProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
  distance?: number;
  duration?: number;
  once?: boolean;
}

function getTransform(
  direction: "up" | "down" | "left" | "right" | "none",
  distance: number
): string {
  switch (direction) {
    case "up":
      return `translateY(${distance}px)`;
    case "down":
      return `translateY(${-distance}px)`;
    case "left":
      return `translateX(${distance}px)`;
    case "right":
      return `translateX(${-distance}px)`;
    case "none":
      return "none";
  }
}

export function AnimatedSection({
  children,
  className = "",
  delay = 0,
  direction = "up",
  distance = 60,
  duration = 0.7,
  once = true,
}: AnimatedSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setIsVisible(false);
        }
      },
      { rootMargin: "-80px", threshold: 0 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [once]);

  const transform = getTransform(direction, distance);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "none" : transform,
        transition: `opacity ${duration}s cubic-bezier(0.16, 1, 0.3, 1), transform ${duration}s cubic-bezier(0.16, 1, 0.3, 1)`,
        transitionDelay: `${delay}s`,
      }}
    >
      {children}
    </div>
  );
}

// ── Staggered children container ──
// Renders children as-is for maximum reliability.
// Each child receives its stagger delay as a CSS custom property.
// Falls back to immediate render when the container is visible.

interface StaggerContainerProps {
  children: ReactNode;
  className?: string;
  staggerDelay?: number;
  once?: boolean;
}

export function StaggerContainer({
  children,
  className = "",
  staggerDelay = 0.1,
  once = true,
}: StaggerContainerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setIsVisible(false);
        }
      },
      { rootMargin: "-60px", threshold: 0 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [once]);

  const childrenArray = React.Children.toArray(children);

  return (
    <div ref={ref} className={className}>
      {childrenArray.map((child, index) => (
        <div
          key={index}
          style={{
            opacity: isVisible ? 1 : 0,
            transform: isVisible ? "translateY(0)" : "translateY(40px)",
            transition: `opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)`,
            transitionDelay: isVisible ? `${index * staggerDelay}s` : "0s",
          }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}

interface StaggerItemProps {
  children: ReactNode;
  className?: string;
  direction?: "up" | "down" | "left" | "right" | "none";
  distance?: number;
}

/**
 * StaggerItem is a thin wrapper that does NOT set its own opacity.
 * Visibility is managed entirely by the parent StaggerContainer.
 */
export function StaggerItem({ children, className = "" }: StaggerItemProps) {
  return <div className={className}>{children}</div>;
}

// ── Scale-on-hover wrapper ──
// Uses CSS hover via group utilities for performance.

interface ScaleHoverProps {
  children: ReactNode;
  scale?: number;
  className?: string;
}

export function ScaleHover({
  children,
  scale = 1.02,
  className = "",
}: ScaleHoverProps) {
  return (
    <div
      className={className}
      style={{ transition: "transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.transform = `scale(${scale})`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(1)";
      }}
    >
      {children}
    </div>
  );
}

// ── ParallaxLayer (keeps framer-motion import) ──
import { motion, useScroll, useTransform } from "framer-motion";

interface ParallaxLayerProps {
  children: ReactNode;
  speed?: number;
  className?: string;
}

export function ParallaxLayer({
  children,
  speed = 0.3,
  className = "",
}: ParallaxLayerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [speed * 100, speed * -100]);

  return (
    <div ref={ref} className={className}>
      <motion.div style={{ y }}>{children}</motion.div>
    </div>
  );
}
