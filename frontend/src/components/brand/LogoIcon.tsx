import { CarbitLogo } from "@/components/brand/CarbitLogo";

type LogoIconProps = {
  size?: number;
  light?: boolean;
};

export function LogoIcon({ size = 22, light = false }: LogoIconProps) {
  return <CarbitLogo variant="icon" height={size} light={light} />;
}
