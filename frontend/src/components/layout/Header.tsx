import { Link, useLocation } from 'react-router-dom';
import { Plus } from 'lucide-react';

export default function Header() {
  const location = useLocation();

  const linkClass = (path: string) =>
    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      location.pathname === path
        ? 'bg-[#1B3A6B]/10 text-[#1B3A6B]'
        : 'text-[#2C2C2C]/60 hover:text-[#2C2C2C] hover:bg-[#1B3A6B]/5'
    }`;

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3">
            <img
              src="/lazboy-logo.png"
              alt="La-Z-Boy"
              className="h-10"
            />
            <span className="text-sm font-semibold text-[#1B3A6B]/60 border-l border-[#1B3A6B]/20 pl-3">
              Skills
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <Link to="/" className={linkClass('/')}>Home</Link>
            <Link to="/browse" className={linkClass('/browse')}>Browse</Link>
            <Link
              to="/submit"
              className="ml-2 inline-flex items-center gap-1 px-4 py-2 bg-[#C0392B] text-white text-sm font-medium rounded-lg hover:opacity-85 transition-all"
            >
              <Plus className="w-4 h-4" />
              Submit Skill
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
