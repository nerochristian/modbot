import React, { useState, useEffect } from "react";
import { Menu, X, Shield, Sparkles, ChevronRight, Activity, Zap, Server } from "lucide-react";
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
      <header
        id="navbar"
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled
            ? "py-3 bg-[#05070E]/85 backdrop-blur-xl border-b border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.8)]"
            : "py-6 bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            
            {/* Brand Logo */}
            <div
              className="flex items-center space-x-3 cursor-pointer group"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 via-indigo-600 to-cyan-500 p-0.5 shadow-[0_0_20px_rgba(124,58,237,0.4)] transition-all duration-300 group-hover:scale-105 group-hover:shadow-[0_0_30px_rgba(124,58,237,0.6)]">
                <div className="w-full h-full bg-[#090D1A] rounded-[10px] flex items-center justify-center relative overflow-hidden">
                  <Shield className="w-5 h-5 text-purple-400 group-hover:text-cyan-400 transition-colors" />
                  <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/20 to-cyan-500/0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border-2 border-[#05070E] flex items-center justify-center shadow-sm">
                  <span className="w-1 h-1 rounded-full bg-white animate-ping" />
                </div>
              </div>

              <div className="flex flex-col">
                <span className="font-heading font-extrabold text-xl tracking-tight text-white uppercase flex items-center gap-1.5">
                  SOUL <span className="bg-gradient-to-r from-purple-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">MODBOT</span>
                </span>
                <span className="text-[10px] font-mono text-purple-300/70 tracking-wider uppercase -mt-1 font-semibold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
                  Systems Normal
                </span>
              </div>
            </div>

            {/* Desktop Nav Pills */}
            <div className="hidden lg:flex items-center space-x-1 px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/10 backdrop-blur-md shadow-inner">
              {navLinks.map((link) => (
                <button
                  key={link.target}
                  onClick={() => scrollToSection(link.target)}
                  className="font-sans text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/10 transition-all px-4 py-2 rounded-full cursor-pointer"
                >
                  {link.label}
                </button>
              ))}
            </div>

            {/* Right CTAs */}
            <div className="hidden md:flex items-center space-x-4">
              <button
                onClick={() => scrollToSection("dashboard")}
                className="text-xs font-semibold text-slate-300 hover:text-white transition-colors px-3 py-2 cursor-pointer flex items-center space-x-1.5 group"
              >
                <Server className="w-3.5 h-3.5 text-purple-400 group-hover:rotate-12 transition-transform" />
                <span>Console Login</span>
              </button>

              <a
                href="https://discord.com"
                target="_blank"
                rel="noreferrer"
                className="btn-primary inline-flex items-center space-x-2 px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider cursor-pointer group"
              >
                <Sparkles className="w-4 h-4 text-cyan-300 group-hover:rotate-45 transition-transform duration-300" />
                <span>Add to Discord</span>
              </a>
            </div>

            {/* Mobile Menu Button */}
            <div className="flex lg:hidden">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:text-white focus:outline-none cursor-pointer"
              >
                {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Dropdown */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="lg:hidden bg-[#090D1A]/95 border-b border-white/10 backdrop-blur-2xl mt-3 px-4 pt-2 pb-6 space-y-3"
            >
              {navLinks.map((link) => (
                <button
                  key={link.target}
                  onClick={() => scrollToSection(link.target)}
                  className="block w-full text-left px-4 py-3 rounded-xl text-sm font-semibold text-slate-300 hover:bg-purple-500/10 hover:text-purple-300 transition-colors"
                >
                  {link.label}
                </button>
              ))}
              <div className="pt-4 border-t border-white/10 flex flex-col space-y-3">
                <button
                  onClick={() => scrollToSection("dashboard")}
                  className="w-full py-3 rounded-xl text-sm font-semibold text-slate-300 hover:bg-white/5 transition-colors"
                >
                  Dashboard Console
                </button>
                <a
                  href="https://discord.com"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary w-full py-3 rounded-xl text-sm font-bold uppercase tracking-wider flex items-center justify-center space-x-2"
                >
                  <Sparkles className="w-4 h-4 text-cyan-300" />
                  <span>Add to Discord</span>
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>
    </>
  );
}

