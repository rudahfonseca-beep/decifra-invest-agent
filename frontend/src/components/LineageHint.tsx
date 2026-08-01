type Props = {
  text?: string | null;
};

export function LineageHint({ text }: Props) {
  if (!text) return null;
  return <div className="mt-0.5 text-[10px] leading-tight text-slate-500">{text}</div>;
}
