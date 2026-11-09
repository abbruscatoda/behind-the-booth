"use client";

import { useEffect, useState } from "react";
import { createClient } from "../../lib/supabase/client";

export default function ConnectionTestPage() {
  const [message, setMessage] = useState("Connecting to Supabase...");

  useEffect(() => {
    async function testConnection() {
      try {
        const supabase = createClient();

        const { data, error } = await supabase
          .from("markets")
          .select("name")
          .eq("slug", "sample-raleigh-market")
          .single();

        if (error) throw error;

        setMessage(`Connected! Found: ${data.name}`);
      } catch (error) {
        setMessage(
          `Connection failed: ${
            error instanceof Error
              ? error.message
              : (error as { message?: string })?.message ??
                "Unknown error"
          }`
        );
      }
    }

    void testConnection();
  }, []);

  return (
    <main style={{ padding: "40px" }}>
      <h1>Supabase Connection Test</h1>
      <p>{message}</p>
    </main>
  );
}