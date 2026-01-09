import { Suspense } from "react";
import { DialoguePlaygroundClient } from "./playground-client";
export default function DialoguePlaygroundPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl mx-auto p-6 text-sm text-muted-foreground">
          Loading…
        </div>
      }
    >
      <DialoguePlaygroundClient />
    </Suspense>
  );
}
