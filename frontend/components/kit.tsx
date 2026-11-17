// App-level primitives in the comic style, built on shadcn/ui. Pages use these, so the look lives in one place.
import { AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Button as UiButton } from "./ui/button";

type Variant = "primary" | "secondary" | "ghost" | "pop";
const VARIANT = { primary: "default", secondary: "outline", ghost: "ghost", pop: "secondary" } as const;

type ButtonProps = Omit<ComponentProps<typeof UiButton>, "variant"> & { variant?: Variant };

export function Button({ variant = "primary", size = "lg", className, ...props }: ButtonProps) {
  return <UiButton variant={VARIANT[variant]} size={size} className={className} {...props} />;
}

export function ButtonLink({
  href,
  children,
  variant = "primary",
  className,
}: {
  href: string;
  children: ReactNode;
  variant?: Exclude<Variant, "ghost">;
  className?: string;
}) {
  return (
    <UiButton asChild variant={VARIANT[variant]} size="lg" className={className}>
      <Link href={href}>{children}</Link>
    </UiButton>
  );
}

type Paper = "card" | "gold" | "sky" | "pink" | "mint" | "indigo";
const PAPER: Record<Paper, string> = {
  card: "bg-card text-card-foreground",
  gold: "bg-secondary text-secondary-foreground",
  sky: "bg-sky text-ink",
  pink: "bg-pink text-ink",
  mint: "bg-mint text-ink",
  indigo: "bg-primary text-primary-foreground",
};

export type Accent = "indigo" | "gold" | "pink" | "sky" | "mint" | "orange";
const ACCENT: Record<Accent, string> = {
  indigo: "accent-indigo", gold: "accent-gold", pink: "accent-pink", sky: "accent-sky", mint: "accent-mint", orange: "accent-orange",
};
/** Tailwind classes for a small chip in the accent colour (icon holders, numbers). */
export const ACCENT_CHIP: Record<Accent, string> = {
  indigo: "bg-primary text-primary-foreground",
  gold: "bg-gold text-ink",
  pink: "bg-pink text-ink",
  sky: "bg-sky text-ink",
  mint: "bg-mint text-ink",
  orange: "bg-chart-2 text-ink",
};

/**
 * A comic panel. Paper stays light; `accent` colours the hard shadow (outlined in ink) and, with `corner`,
 * a folded page corner. It is a <section>, so each one is a landmark screen readers (and the e2e test) can scope to.
 */
export function Card({
  className,
  children,
  paper = "card",
  accent,
  corner = false,
}: {
  className?: string;
  children: ReactNode;
  paper?: Paper;
  accent?: Accent;
  corner?: boolean;
}) {
  return (
    <section
      data-slot="card"
      className={cn(
        "comic-panel rounded-xl p-5",
        PAPER[paper],
        accent && ["has-accent", ACCENT[accent]],
        corner && "comic-corner",
        className,
      )}
    >
      {children}
    </section>
  );
}

type Tone = "neutral" | "good" | "warn" | "bad" | "info" | "pop";
const TONES: Record<Tone, string> = {
  neutral: "bg-card text-foreground",
  good: "bg-success-soft text-success",
  warn: "bg-warning-soft text-warning",
  bad: "bg-destructive text-white",
  info: "bg-info-soft text-accent-foreground",
  pop: "bg-secondary text-secondary-foreground",
};

/** A sticker: inked outline, small hard shadow, optionally tilted. */
export function Badge({
  tone = "neutral",
  tilt = false,
  children,
  className,
}: {
  tone?: Tone;
  tilt?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1 rounded-full border-2 border-border px-2.5 py-0.5 text-xs font-bold whitespace-nowrap shadow-[2px_2px_0_0_var(--ink)]",
        tilt && "-rotate-2",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground">
      <Loader2 className="size-4 animate-spin text-primary" aria-hidden />
      {label ?? "Đang tải…"}
    </span>
  );
}

export function ErrorBox({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <Alert variant="destructive" className="comic-panel rounded-xl bg-card px-4 py-3 text-destructive">
      <AlertCircle aria-hidden />
      <AlertDescription className="text-foreground">
        <p className="font-medium">{message}</p>
        {action && <div className="mt-3">{action}</div>}
      </AlertDescription>
    </Alert>
  );
}

/** Small caption label above a section title, set like a comic caption box. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "inline-block -rotate-1 border-2 border-border bg-secondary px-2 py-0.5 text-[0.7rem] font-extrabold uppercase tracking-[0.12em] text-secondary-foreground",
        className,
      )}
    >
      {children}
    </p>
  );
}

/** Section heading in comic lettering. */
export function Heading({ as: Tag = "h2", children, className }: { as?: "h1" | "h2" | "h3"; children: ReactNode; className?: string }) {
  return <Tag className={cn("comic-title", className)}>{children}</Tag>;
}

/** The one big title of a page, lettered like a comic cover. Wrap a word in <span className="pop"> to colour it gold. */
export function CoverTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h1 className={cn("comic-headline", className)}>{children}</h1>;
}
