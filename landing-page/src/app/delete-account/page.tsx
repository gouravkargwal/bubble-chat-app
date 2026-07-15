"use client";

import { useEffect } from "react";

export default function DeleteAccountPage() {
  useEffect(() => {
    window.location.href =
      "mailto:support@cookdai.site?subject=Account%20Deletion%20Request&body=Please%20delete%20my%20account%20and%20all%20associated%20data.%0A%0AMy%20account%20email%3A%20%0AReason%20for%20deletion%3A";
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#101124] text-white">
      <div className="text-center">
        <p className="text-lg">Redirecting to email client...</p>
        <p className="text-sm text-gray-400 mt-2">
          If you are not redirected, email{" "}
          <a
            href="mailto:support@cookdai.site?subject=Account%20Deletion%20Request&body=Please%20delete%20my%20account%20and%20all%20associated%20data.%0A%0AMy%20account%20email%3A%20%0AReason%20for%20deletion%3A"
            className="text-[#FF003C] underline"
          >
            support@cookdai.site
          </a>
        </p>
      </div>
    </main>
  );
}
