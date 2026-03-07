export default function Footer() {
  return (
    <footer className="bg-[#1B3A6B] mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <img
          src="/lazboy-logo.png"
          alt="La-Z-Boy"
          className="h-8 mx-auto mb-4 brightness-0 invert opacity-40"
        />
        <p className="text-center text-sm text-white/60">
          Skills Repository &mdash; Internal use only
        </p>
        <p className="text-center text-xs text-white/30 mt-1 italic">
          Live life comfortably.&reg;
        </p>
      </div>
    </footer>
  );
}
