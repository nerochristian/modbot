/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import SmartModeration from "./components/SmartModeration";
import CommandDemo from "./components/CommandDemo";
import DashboardPreview from "./components/DashboardPreview";
import FeatureGrid from "./components/FeatureGrid";
import HowItWorks from "./components/HowItWorks";
import Stats from "./components/Stats";
import Testimonials from "./components/Testimonials";
import Pricing from "./components/Pricing";
import FAQ from "./components/FAQ";
import Footer from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-[#0b0c0e] text-white overflow-x-hidden font-sans antialiased selection:bg-purple-500/30 selection:text-white">
      {/* Interactive Sticky Navigation */}
      <Navbar />

      {/* Main Content Layout */}
      <main>
        {/* Full-Screen Hero Visual Showcase & Active servers count strip */}
        <Hero />

        {/* Smart Moderation (Context-Aware violation & toxicity threshold slider) */}
        <SmartModeration />

        {/* Command Demonstration (Interactive mock console & chat sequence typing) */}
        <CommandDemo />

        {/* Interactive Dashboard Preview (Overview, cases, rules, analytics charts, appeals) */}
        <DashboardPreview />

        {/* Features Grid Bento-Style layout */}
        <FeatureGrid />

        {/* How It Works Timelines */}
        <HowItWorks />

        {/* Performance Statistics and Live analyzing tickers */}
        <Stats />

        {/* Server Owner and Moderator Testimonials */}
        <Testimonials />

        {/* Flexible Pricing Plans Monthly/Yearly compare toggle */}
        <Pricing />

        {/* Responsive Accordion FAQs */}
        <FAQ />
      </main>

      {/* Final Call-to-action & Rich Footer */}
      <Footer />
    </div>
  );
}
