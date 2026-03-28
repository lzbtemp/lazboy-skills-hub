import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import GradientMenu from '@/components/ui/gradient-menu';
import { TextRoll } from '@/components/ui/text-roll';

export default function Header() {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`sticky top-0 z-50 transition-all duration-300 ${
      scrolled
        ? 'bg-white/70 backdrop-blur-2xl border-b border-[#1B3A6B]/[0.08] shadow-sm shadow-[#1B3A6B]/[0.04]'
        : 'bg-white/80 backdrop-blur-xl border-b border-gray-200/30'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <Link to="/" className="flex items-center gap-3 group">
            <img
              src="/lazboy-logo.png"
              alt="La-Z-Boy"
              className="h-10"
            />
            <span className="border-l border-[#1B3A6B]/15 pl-3">
              <TextRoll
                className="text-lg font-bold text-[#1B3A6B] tracking-tight"
                duration={0.6}
                getEnterDelay={(i) => i * 0.05}
                getExitDelay={(i) => i * 0.05 + 0.12}
                loop
                loopDelay={4}
              >
                AI Hub
              </TextRoll>
              <span className="block text-[10px] font-medium text-[#1B3A6B]/50 tracking-[0.12em] uppercase">
                Discover · Build · Automate with AI
              </span>
            </span>
          </Link>

          <nav className="flex items-center">
            <GradientMenu onNavigate={(href) => navigate(href)} />
          </nav>
        </div>
      </div>
    </header>
  );
}
