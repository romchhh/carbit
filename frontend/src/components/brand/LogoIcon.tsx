type LogoIconProps = {
  size?: number;
  light?: boolean;
};

export function LogoIcon({ size = 22, light = false }: LogoIconProps) {
  const main = light ? "#FFFFFF" : "#0A0C0E";
  const accent = "#00C896";

  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M4 19.25H24M5.75 19.25V16.75L8 13.75H10.5L12.75 11.5H16.25L18.5 13.75H21L23.25 16.75V19.25"
        stroke={main}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M13.25 11.75H16.75L19 14H12.75L13.25 11.75Z" fill={accent} />
      <circle cx="8.75" cy="19.25" r="2" stroke={main} strokeWidth="1.6" />
      <circle cx="19.25" cy="19.25" r="2" stroke={main} strokeWidth="1.6" />
      <circle cx="8.75" cy="19.25" r="0.85" fill={accent} />
      <circle cx="19.25" cy="19.25" r="0.85" fill={accent} />
    </svg>
  );
}
