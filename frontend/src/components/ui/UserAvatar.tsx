"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/auth-storage";
import { getApiUrl } from "@/lib/api-url";
import { avatarColorClass, cn, getInitials } from "@/lib/utils";

type Props = {
  name: string;
  avatarUrl?: string | null;
  accessToken?: string | null;
  className?: string;
  textClassName?: string;
  rounded?: "full" | "xl";
};

export function UserAvatar({
  name,
  avatarUrl,
  accessToken,
  className,
  textClassName,
  rounded = "full",
}: Props) {
  const [failed, setFailed] = useState(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    setFailed(false);
    setBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    if (!avatarUrl) return;

    const path = avatarUrl.startsWith("/") ? avatarUrl : `/${avatarUrl}`;
    const token = accessToken ?? getToken();
    const controller = new AbortController();

    fetch(`${getApiUrl()}${path}`, {
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error("avatar fetch failed");
        return res.blob();
      })
      .then((blob) => {
        setBlobUrl(URL.createObjectURL(blob));
      })
      .catch(() => setFailed(true));

    return () => {
      controller.abort();
    };
  }, [avatarUrl, accessToken]);

  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  const initials = getInitials(name);
  const colorClass = avatarColorClass(name);
  const roundedClass = rounded === "xl" ? "rounded-xl" : "rounded-full";

  if (blobUrl && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={blobUrl}
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
