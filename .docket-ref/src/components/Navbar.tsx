import React, { useState, useEffect } from "react";
import { Menu, X, Shield, ChevronRight, Activity } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setIsMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const navLinks = [
    { label: "Features", target: "features" },
    { label: "AI Moderate", target: "smart-moderation" },
    { label: "Commands", target: "commands" },
    { label: "Dashboard", target: "dashboard" },
    { label: "Pricing", target: "pricing" },
    { label: "FAQ", target: "faq" },
  ];

  return (
    <>
      <nav
        id="navbar"
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? "bg-[#05060B]/80 backdrop-blur-md border-b border-slate-800/80 py-3"
            : "bg-transparent py-5"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div
              className="flex items-center space-x-2.5 cursor-pointer group"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 transition-transform duration-300 group-hover:scale-105">
                <span className="font-bold text-sm text-white font-display">D</span>
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 border border-[#05060B] flex items-center justify-center animate-pulse" />
              </div>
              <span className="font-display font-bold text-lg tracking-tight text-white uppercase">
                DOCKET
              </span>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-8">
              {navLinks.map((link) => (
                <button
                  key={link.target}
                  onClick={() => scrollToSection(link.target)}
                  className="font-sans text-sm font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  {link.label}
                </button>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="hidden md:flex items-center space-x-5">
              <button
                onClick={() => scrollToSection("dashboard")}
                className="font-sans text-sm font-medium text-slate-400 hover:text-purple-400 transition-colors py-2 px-1 cursor-pointer"
              >
                Login
              </button>
              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center space-x-1 px-5 py-2.5 bg-white text-black rounded-full text-sm font-bold hover:bg-slate-200 transition-all shadow-[0_0_20px_rgba(255,255,255,0.15)] cursor-pointer"
              >
                <span>Add to Discord</span>
              </a>
            </div>

            {/* Mobile menu button */}
            <div className="flex md:hidden">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-800 focus:outline-none cursor-pointer"
                aria-expanded="false"
              >
                <span className="sr-only">Open main menu</span>
                {isMobileMenuOpen ? (
                  <X className="block h-6 w-6" aria-hidden="true" />
                ) : (
                  <Menu className="block h-6 w-6" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu, show/hide based on menu state. */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="md:hidden bg-[#05060B] border-b border-slate-800/80"
            >
              <div className="px-2 pt-2 pb-4 space-y-1 sm:px-3 border-t border-slate-800/50 mt-2">
                {navLinks.map((link) => (
                  <button
                    key={link.target}
                    onClick={() => scrollToSection(link.target)}
                    className="block w-full text-left px-3 py-2.5 rounded-md text-base font-medium text-slate-400 hover:text-white hover:bg-slate-900/40 transition-colors"
                  >
                    {link.label}
                  </button>
                ))}
                <div className="pt-4 pb-2 border-t border-slate-800/50 flex flex-col space-y-2 px-3">
                  <button
                    onClick={() => scrollToSection("dashboard")}
                    className="w-full text-center py-2.5 rounded-md text-base font-medium text-slate-400 hover:text-white hover:bg-slate-900/40 transition-colors"
                  >
                    Login to Dashboard
                  </button>
                  <a
                    href="https://discord.com"
                    target="_blank"
                    rel="noreferrer"
                    className="w-full text-center py-2.5 rounded-full text-base font-bold bg-white text-black transition-all shadow-[0_0_20px_rgba(255,255,255,0.15)] flex items-center justify-center"
                  >
                    <span>Add to Discord</span>
                  </a>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </>
  );
}
