import { CarbitLogo } from "@/components/brand/CarbitLogo";

type LogoIconProps = {
  size?: number;
  light?: boolean;
};

/** @deprecated Use CarbitLogo directly */
export function LogoIcon({ size = 22, light = false }: LogoIconProps) {
  return <CarbitLogo variant="full" height={size} light={light} />;
}
