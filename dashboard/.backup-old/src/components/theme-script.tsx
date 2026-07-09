/**
 * Applies the persisted theme, accent, and density before first paint to avoid
 * a flash of the wrong theme. Reads from localStorage (mirrored from the user's
 * saved dashboard config). Injected in <head> as a blocking inline script.
 */
export function ThemeScript() {
  const script = `(function(){try{
    var t=localStorage.getItem('nebula-theme')||'system';
    var a=localStorage.getItem('nebula-accent')||'#6366f1';
    var d=localStorage.getItem('nebula-density')||'comfortable';
    var m=window.matchMedia('(prefers-color-scheme: dark)').matches;
    var dark=t==='dark'||(t==='system'&&m);
    var el=document.documentElement;
    el.classList.toggle('dark',dark);
    el.style.setProperty('--accent',a);
    el.setAttribute('data-density',d);
  }catch(e){}})();`
  return <script dangerouslySetInnerHTML={{ __html: script }} suppressHydrationWarning />
}
