import type { ButtonHTMLAttributes } from "react";
import { color, space } from "../tokens/tokens";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" };

export function Button({ variant = "primary", style, ...rest }: Props) {
  const primary = variant === "primary";
  return (
    <button
      {...rest}
      style={{
        padding: `${space[2]} ${space[3]}`,
        borderRadius: "var(--radius)",
        border: `1px solid ${primary ? color.primary : color.border}`,
        background: primary ? color.primary : color.surface,
        color: primary ? color.surface : color.text,
        ...style,
      }}
    />
  );
}
