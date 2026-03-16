import React from 'react';
import { IoHomeOutline, IoGridOutline, IoSearchOutline, IoRocketOutline, IoStorefrontOutline } from 'react-icons/io5';

const menuItems = [
  { title: 'Home', href: '/', icon: <IoHomeOutline />, gradientFrom: '#1B3A6B', gradientTo: '#2C2C2C' },
  { title: 'Browse', href: '/browse', icon: <IoGridOutline />, gradientFrom: '#C0392B', gradientTo: '#1B3A6B' },
  { title: 'Market', href: '/marketplace', icon: <IoStorefrontOutline />, gradientFrom: '#8FAF8A', gradientTo: '#1B3A6B' },
  { title: 'Search', href: '/browse?q=', icon: <IoSearchOutline />, gradientFrom: '#1B3A6B', gradientTo: '#8FAF8A' },
  { title: 'Latest', href: '/browse?sort=newest', icon: <IoRocketOutline />, gradientFrom: '#1B3A6B', gradientTo: '#C0392B' },
];

interface GradientMenuProps {
  onNavigate?: (href: string) => void;
}

export default function GradientMenu({ onNavigate }: GradientMenuProps) {
  return (
    <ul className="flex gap-4">
      {menuItems.map(({ title, href, icon, gradientFrom, gradientTo }, idx) => (
        <li
          key={idx}
          onClick={() => onNavigate?.(href)}
          style={{ '--gradient-from': gradientFrom, '--gradient-to': gradientTo } as React.CSSProperties}
          className="relative w-[50px] h-[50px] bg-white shadow-lg rounded-full flex items-center justify-center transition-all duration-500 hover:w-[150px] hover:shadow-none group cursor-pointer"
        >
          {/* Gradient background on hover */}
          <span className="absolute inset-0 rounded-full bg-[linear-gradient(45deg,var(--gradient-from),var(--gradient-to))] opacity-0 transition-all duration-500 group-hover:opacity-100"></span>
          {/* Blur glow */}
          <span className="absolute top-[10px] inset-x-0 h-full rounded-full bg-[linear-gradient(45deg,var(--gradient-from),var(--gradient-to))] blur-[15px] opacity-0 -z-10 transition-all duration-500 group-hover:opacity-50"></span>

          {/* Icon */}
          <span className="relative z-10 transition-all duration-500 group-hover:scale-0 delay-0">
            <span className="text-xl text-[#1B3A6B]/60">{icon}</span>
          </span>

          {/* Title */}
          <span className="absolute text-white uppercase tracking-wide text-xs font-semibold transition-all duration-500 scale-0 group-hover:scale-100 delay-150">
            {title}
          </span>
        </li>
      ))}
    </ul>
  );
}
