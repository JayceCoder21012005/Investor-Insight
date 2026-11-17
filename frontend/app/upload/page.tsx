import { Suspense } from "react";
import { Spinner } from "@/components/kit";
import { UploadClient } from "./UploadClient";

export default function UploadPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <UploadClient />
    </Suspense>
  );
}
