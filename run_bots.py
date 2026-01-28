import subprocess
import sys
import time
import os
import signal

# FORCE UTF-8 FOR WINDOWS CONSOLE
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# List of bot scripts to run
BOT_SCRIPTS = ["bot.py", "bot_ai.py", "bot_support.py"]

def run_bots():
    processes = []
    
    print(f"🚀 Starting {len(BOT_SCRIPTS)} bots...")
    
    # Start each bot as a subprocess
    for script in BOT_SCRIPTS:
        if not os.path.exists(script):
            print(f"❌ Error: Script not found: {script}")
            continue
            
        print(f"📄 Launching {script}...")
        # Use sys.executable to ensure we use the same Python interpreter
        # connect stdin/out/err to the parent process
        p = subprocess.Popen([sys.executable, script])
        processes.append((script, p))

    print("✅ All bots launched. Press Ctrl+C to stop.")

    try:
        # Keep the main process alive to monitor children
        while True:
            time.sleep(1)
            
            # Optional: Check if any processes have died and restart them?
            # For now, we'll just check if they are still running
            for script, p in processes:
                if p.poll() is not None:
                    print(f"⚠️ {script} has stopped with code {p.returncode}")
                    # Remove from list so we don't check it again, or maybe restart?
                    # simple runner: just notify
                    processes.remove((script, p))
                    
            if not processes:
                print("❌ All bots have stopped. Exiting.")
                break
                
    except KeyboardInterrupt:
        print("\n👋 Stopping all bots...")
        for script, p in processes:
            if p.poll() is None: # If still running
                print(f"Killing {script}...")
                p.terminate() # Try graceful termination first
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill() # Force kill if necessary
        print("✅ Shutdown complete.")

if __name__ == "__main__":
    run_bots()
