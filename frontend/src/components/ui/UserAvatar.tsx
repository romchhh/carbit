"use client";

import { useEffect, useMemo, useState } from "react";
import { getToken } from "@/lib/auth-storage";
import { avatarColorClass, cn, getInitials } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Props = {
  name: string;
  avatarUrl?: string | null;
  className?: string;
  textClassName?: string;
  rounded?: "full" | "xl";
};

export function UserAvatar({
  name,
  avatarUrl,
  className,
  textClassName,
  rounded = "full",
}: Props) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [avatarUrl]);
  const initials = getInitials(name);
  const colorClass = avatarColorClass(name);
  const roundedClass = rounded === "xl" ? "rounded-xl" : "rounded-full";

  const src = useMemo(() => {
    if (!avatarUrl || failed) return null;
    const token = getToken();
    if (!token) return null;
    const path = avatarUrl.startsWith("/") ? avatarUrl : `/${avatarUrl}`;
    return `${API_URL}${path}?access_token=${encodeURIComponent(token)}`;
  }, [avatarUrl, failed]);

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={name}
        className={cn(roundedClass, "object-cover", className)}
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <span
      className={cn(
        roundedClass,
        colorClass,
        "flex items-center justify-center font-bold",
        className,
        textClassName,
      )}
    >
      {initials}
    </span>
  );
}
