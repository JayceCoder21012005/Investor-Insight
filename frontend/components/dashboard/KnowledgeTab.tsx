"use client";

import { BookOpen } from "lucide-react";
import { useState } from "react";
import { type Accent, ACCENT_CHIP, Badge } from "@/components/kit";
import type { Article } from "@/lib/api";
import { LEVEL_LABEL } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { ArticleModal } from "./ArticleModal";

const ACCENTS: Accent[] = ["sky", "gold", "pink"];

export function KnowledgeTab({ articles }: { articles: Article[] }) {
  const [open, setOpen] = useState<Article | null>(null);
  return (
    <div className="space-y-6">
      <p className="text-sm font-medium text-muted-foreground">Ba bài đọc phù hợp với các tín hiệu và mức kinh nghiệm của bạn.</p>
      <div className="grid gap-6 md:grid-cols-3">
        {articles.map((a, i) => (
          <button
            key={a.id}
            onClick={() => setOpen(a)}
            className={cn("comic-press comic-press-accent group flex flex-col overflow-hidden rounded-xl bg-card text-left", `accent-${ACCENTS[i % 3]}`)}
          >
            <div className="flex items-center justify-between px-4 pt-4">
              <span className={cn("flex size-12 items-center justify-center rounded-xl border-[2.5px] border-border transition-transform group-hover:-rotate-6", ACCENT_CHIP[ACCENTS[i % 3]])}>
                <BookOpen className="size-6" aria-hidden />
              </span>
              <span className="halftone size-12 rounded-full text-primary/25" aria-hidden />
            </div>
            <div className="flex flex-1 flex-col gap-2 p-4">
              <Badge>{LEVEL_LABEL[a.level] ?? a.level}</Badge>
              <h3 className="text-base font-bold leading-snug">{a.title}</h3>
              <p className="mt-auto pt-2 text-sm font-bold text-primary">Đọc bài →</p>
            </div>
          </button>
        ))}
      </div>
      {open && <ArticleModal article={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
