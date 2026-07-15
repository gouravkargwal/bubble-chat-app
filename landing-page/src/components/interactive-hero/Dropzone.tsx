"use client";

import React, { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { UploadIcon } from "./icons";
import { slideUp, EASE_OUT } from "./types";

interface DropzoneProps {
  onImageSelected: (file: File) => void;
}

export function Dropzone({ onImageSelected }: DropzoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(file);
      setTimeout(() => onImageSelected(file), 800);
    },
    [onImageSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <motion.div
      variants={slideUp}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex flex-col items-center w-full"
    >
      {/* Heading */}
      <div className="text-center max-w-3xl">
        <h1 className="font-heading text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-nothing-white leading-[1.05]">
          Turn every <span className="text-neon-red">left on read</span> into a
          reply that{" "}
          <span className="text-nothing-white/70">actually lands</span>.
        </h1>
        <p className="mt-5 text-base sm:text-lg text-nothing-text-secondary leading-relaxed max-w-2xl mx-auto">
          Upload a chat screenshot. Pick a direction. Let AI craft replies that
          match <em>your</em> voice &mdash; no more awkward silences, no more
          second-guessing.
        </p>
      </div>

      {/* Live demo preview (blurred teaser) */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5, ease: EASE_OUT }}
        className="mt-10 w-full max-w-md"
      >
        <div className="relative overflow-hidden rounded-xl border border-nothing-border bg-nothing-surface p-4">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase tracking-widest text-nothing-text-tertiary">
              Example Output &bull; Playful Tease
            </span>
            <motion.span
              className="text-[10px] font-mono text-neon-red tracking-wider"
              animate={{ opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              LIVE DEMO
            </motion.span>
          </div>
          <p
            className="text-sm text-nothing-white blur-sm select-none"
            aria-hidden="true"
          >
            Haha you&rsquo;re literally impossible to resist, you know that? 😏
          </p>
          <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-nothing-black/10 backdrop-blur-[1px]">
            <span className="text-[10px] font-mono text-nothing-text-secondary tracking-wider bg-nothing-black/60 px-3 py-1.5 rounded-full border border-nothing-border">
              YOUR REPLIES WILL LOOK LIKE THIS
            </span>
          </div>
        </div>
      </motion.div>

      {/* Dropzone */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9, duration: 0.5, ease: EASE_OUT }}
        className="mt-8 w-full max-w-md"
      >
        <p className="text-center text-xs font-mono text-nothing-text-secondary tracking-wider mb-3">
          TRY IT YOURSELF &rarr;
        </p>
        <button
          onClick={() => inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          className={`relative w-full cursor-pointer rounded-2xl border-2 border-dashed p-10 sm:p-14 transition-all duration-300 ${
            dragOver
              ? "border-neon-red bg-neon-red/5"
              : preview
              ? "border-nothing-border bg-nothing-surface"
              : "border-nothing-border hover:border-nothing-text-secondary hover:bg-nothing-white/[0.02]"
          }`}
          aria-label={
            preview
              ? "Screenshot preview uploaded, click to upload a different screenshot"
              : "Upload your chat screenshot"
          }
        >
          {preview ? (
            <div className="flex flex-col items-center gap-3">
              <div className="relative h-48 w-full max-w-xs">
                <Image
                  src={preview}
                  alt="Uploaded chat screenshot preview"
                  fill
                  className="rounded-lg object-contain"
                  unoptimized
                />
              </div>
              <span className="text-xs font-mono text-nothing-success/80">
                &#x2714; IMAGE_LOCKED
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full border border-nothing-border p-4">
                <UploadIcon
                  className="h-8 w-8 text-nothing-text-secondary"
                  aria-hidden="true"
                />
              </div>
              <div className="text-center">
                <p className="text-sm font-bold text-nothing-white">
                  {dragOver
                    ? "DROP IT LIKE IT'S HOT 🔥"
                    : "Upload your chat screenshot"}
                </p>
                <p className="mt-1.5 text-xs font-mono text-nothing-text-tertiary leading-relaxed">
                  We&rsquo;ll analyze the conversation and generate replies
                  tailored to your situation.
                </p>
                <p className="mt-2 text-[10px] font-mono text-nothing-text-tertiary tracking-wider">
                  PNG, JPG, WEBP &bull; MAX 10MB
                </p>
              </div>
            </div>
          )}
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleInputChange}
            aria-hidden="true"
          />
        </button>
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.3, duration: 0.5 }}
        className="mt-6 text-[10px] font-mono text-nothing-text-tertiary tracking-wider text-center"
      >
        Built by real people for real conversations &mdash; trusted by early
        adopters
      </motion.p>
    </motion.div>
  );
}
