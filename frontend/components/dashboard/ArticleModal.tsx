"use client";

import { X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Badge, Button } from "@/components/kit";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import type { Article } from "@/lib/api";
import { LEVEL_LABEL } from "@/lib/labels";

/** An article opened as a comic page. Escape, the overlay and "Đóng" all close it (Radix Dialog handles focus). */
export function ArticleModal({ article, onClose }: { article: Article; onClose: () => void }) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="comic-panel max-h-[88vh] gap-0 overflow-hidden rounded-2xl bg-card p-0 shadow-[7px_7px_0_0_var(--ink)] ring-0 sm:max-w-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b-[2.5px] border-border bg-secondary px-6 py-4 text-secondary-foreground">
          <div className="space-y-2">
            <Badge tilt>{LEVEL_LABEL[article.level] ?? article.level}</Badge>
            <DialogTitle className="comic-title text-3xl">{article.title}</DialogTitle>
            <DialogDescription className="sr-only">Bài đọc kiến thức</DialogDescription>
          </div>
          <Button variant="secondary" size="default" onClick={onClose}>
            <X aria-hidden /> Đóng
          </Button>
        </div>
        <div className="article max-h-[65vh] space-y-3 overflow-y-auto px-6 py-5 text-[0.95rem] leading-relaxed">
          <ReactMarkdown>{article.body}</ReactMarkdown>
        </div>
      </DialogContent>
    </Dialog>
  );
}
