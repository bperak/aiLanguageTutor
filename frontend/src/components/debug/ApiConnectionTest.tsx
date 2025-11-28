"use client";

import { useState } from "react";

export default function ApiConnectionTest() {
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const testConnection = async () => {
    setLoading(true);
    setResult("");
    
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const testUrl = `${apiBase}/health`;
    
    try {
      console.log("Testing connection to:", testUrl);
      const response = await fetch(testUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setResult(`✅ Connection successful! Response: ${JSON.stringify(data, null, 2)}`);
      } else {
        setResult(`❌ Connection failed with status: ${response.status}`);
      }
    } catch (error: any) {
      setResult(`❌ Connection error: ${error.message}`);
      console.error("Connection test error:", error);
    } finally {
      setLoading(false);
    }
  };

  const testLexicalEndpoint = async () => {
    setLoading(true);
    setResult("");
    
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const testUrl = `${apiBase}/api/v1/lexical/graph?center=水&depth=1&searchField=kanji`;
    
    try {
      console.log("Testing lexical endpoint:", testUrl);
      const response = await fetch(testUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setResult(`✅ Lexical endpoint successful! Nodes: ${data.nodes?.length || 0}, Links: ${data.links?.length || 0}`);
      } else {
        const errorText = await response.text();
        setResult(`❌ Lexical endpoint failed with status: ${response.status} - ${errorText}`);
      }
    } catch (error: any) {
      setResult(`❌ Lexical endpoint error: ${error.message}`);
      console.error("Lexical endpoint test error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg bg-gray-50">
      <h3 className="text-lg font-semibold mb-4">API Connection Test</h3>
      
      <div className="space-y-2 mb-4">
        <p><strong>API Base URL:</strong> {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}</p>
        <p><strong>Environment:</strong> {process.env.NODE_ENV}</p>
      </div>
      
      <div className="space-x-2 mb-4">
        <button
          onClick={testConnection}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          Test Health Endpoint
        </button>
        
        <button
          onClick={testLexicalEndpoint}
          disabled={loading}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          Test Lexical Endpoint
        </button>
      </div>
      
      {loading && <p>Testing connection...</p>}
      
      {result && (
        <div className="mt-4 p-3 bg-white border rounded">
          <pre className="whitespace-pre-wrap text-sm">{result}</pre>
        </div>
      )}
    </div>
  );
}
