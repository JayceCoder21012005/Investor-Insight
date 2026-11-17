"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Button, Card, CoverTitle, ErrorBox, Eyebrow } from "@/components/kit";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";
import { ApiError, api } from "@/lib/api";
import { QUESTIONS } from "@/lib/questions";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(QUESTIONS.map(() => null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const question = QUESTIONS[step];
  const isLast = step === QUESTIONS.length - 1;
  const current = answers[step];

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const profile = await api.createProfile(answers as number[]);
      router.push(`/upload?id=${profile.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Không tạo được hồ sơ. Vui lòng thử lại.");
      setBusy(false);
    }
  }

  const choose = (value: number) => setAnswers((prev) => prev.map((v, idx) => (idx === step ? value : v)));

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-3">
        <Eyebrow>Bước 1 / 2 · Khẩu vị rủi ro</Eyebrow>
        <div className="flex items-end justify-between gap-4">
          <CoverTitle className="text-4xl sm:text-5xl">Bạn là kiểu nhà đầu tư nào?</CoverTitle>
          <p className="comic-title shrink-0 text-2xl text-primary">
            Câu {step + 1}/{QUESTIONS.length}
          </p>
        </div>
        {/* progress as a strip of comic panels */}
        <div className="grid grid-cols-5 gap-2" aria-hidden>
          {QUESTIONS.map((q, i) => (
            <div
              key={q.prompt}
              className={cn(
                "h-3 rounded-sm border-2 border-border transition-colors",
                i < step ? "bg-primary" : i === step ? "bg-secondary" : "bg-card",
              )}
            />
          ))}
        </div>
      </div>

      <Card accent="gold" corner className="p-6">
        <fieldset>
          <legend className="mb-5 text-xl font-extrabold">{question.prompt}</legend>
          <RadioGroup
            key={step}
            value={current === null ? "" : String(current)}
            onValueChange={(v) => choose(Number(v))}
            className="gap-3"
          >
            {question.options.map((label, i) => {
              const selected = current === i + 1;
              return (
                <div
                  key={label}
                  className={cn(
                    "relative flex cursor-pointer items-center gap-4 rounded-xl border-[2.5px] border-border px-4 py-3 text-[0.95rem] font-semibold transition",
                    selected
                      ? "translate-x-[-2px] translate-y-[-2px] bg-secondary text-secondary-foreground shadow-[4px_4px_0_0_var(--ink)]"
                      : "bg-card hover:bg-muted",
                  )}
                >
                  <span
                    className={cn(
                      "comic-title flex size-8 shrink-0 items-center justify-center rounded-md border-2 border-border text-lg",
                      selected ? "bg-primary text-primary-foreground" : "bg-muted",
                    )}
                    aria-hidden
                  >
                    {selected ? <Check className="size-4" /> : String.fromCharCode(65 + i)}
                  </span>
                  <span className="flex-1">{label}</span>
                  {/* the real radio covers the whole option, invisible, so a click or tap anywhere selects it */}
                  <RadioGroupItem value={String(i + 1)} aria-label={label} className="absolute inset-0 size-full cursor-pointer rounded-xl border-0 opacity-0 shadow-none" />
                </div>
              );
            })}
          </RadioGroup>
        </fieldset>
      </Card>

      {error && <ErrorBox message={error} />}

      <div className="flex justify-between">
        <Button variant="ghost" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || busy}>
          <ArrowLeft aria-hidden /> Quay lại
        </Button>
        {isLast ? (
          <Button onClick={submit} disabled={current === null || busy}>
            {busy ? "Đang tạo hồ sơ…" : "Hoàn tất"} <Check aria-hidden />
          </Button>
        ) : (
          <Button onClick={() => setStep((s) => s + 1)} disabled={current === null}>
            Tiếp <ArrowRight aria-hidden />
          </Button>
        )}
      </div>
    </div>
  );
}
