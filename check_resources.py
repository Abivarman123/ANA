"""Resource monitoring utility for ANA.

This script checks for running ANA processes and their resource usage.
"""

import sys

import psutil


def format_bytes(bytes_value):
    """Format bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def check_ana_processes():
    """Check for running ANA processes and their resource usage."""
    print("=" * 70)
    print("ANA Resource Monitor")
    print("=" * 70)

    ana_processes = []
    total_memory = 0
    total_cpu = 0

    # Find all ANA-related processes
    for proc in psutil.process_iter(
        ["pid", "name", "cmdline", "memory_info", "cpu_percent"]
    ):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline:
                cmdline_str = " ".join(cmdline)
                # Check for ANA-related processes
                if any(
                    keyword in cmdline_str
                    for keyword in ["main.py", "wake_service.py", "ANA"]
                ):
                    if (
                        "python" in proc.info["name"].lower()
                        or "uv" in proc.info["name"].lower()
                    ):
                        memory_mb = proc.info["memory_info"].rss / (1024 * 1024)
                        cpu = proc.cpu_percent(interval=0.1)

                        ana_processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cmdline": cmdline_str[:80] + "..."
                                if len(cmdline_str) > 80
                                else cmdline_str,
                                "memory_mb": memory_mb,
                                "cpu": cpu,
                            }
                        )

                        total_memory += memory_mb
                        total_cpu += cpu
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not ana_processes:
        print("\n✅ No ANA processes currently running")
        print("\nThis is good - no resources are being used!")
    else:
        print(f"\n⚠️  Found {len(ana_processes)} ANA-related process(es):\n")

        for proc in ana_processes:
            print(f"PID: {proc['pid']}")
            print(f"  Name: {proc['name']}")
            print(f"  Memory: {proc['memory_mb']:.2f} MB")
            print(f"  CPU: {proc['cpu']:.1f}%")
            print(f"  Command: {proc['cmdline']}")
            print()

        print("-" * 70)
        print(f"TOTAL MEMORY USAGE: {total_memory:.2f} MB")
        print(f"TOTAL CPU USAGE: {total_cpu:.1f}%")
        print("-" * 70)

    # Check for zombie/orphaned processes
    print("\n🔍 Checking for potential issues...")

    # Check for serial port locks
    try:
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())
        if ports:
            print(f"\n📡 Available serial ports: {len(ports)}")
            for port in ports:
                print(f"  - {port.device}: {port.description}")
    except ImportError:
        pass

    # Check for audio devices
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        print(f"\n🎤 Audio devices available: {len(devices)}")
    except Exception as e:
        print(f"\n⚠️  Could not query audio devices: {e}")

    print("\n" + "=" * 70)
    print("Resource check complete!")
    print("=" * 70)


def kill_ana_processes():
    """Kill all ANA processes (use with caution)."""
    print("\n⚠️  WARNING: This will terminate all ANA processes!")
    response = input("Are you sure? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        return

    killed = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline:
                cmdline_str = " ".join(cmdline)
                if any(
                    keyword in cmdline_str
                    for keyword in ["main.py", "wake_service.py", "ANA"]
                ):
                    if "python" in proc.info["name"].lower():
                        print(f"Terminating PID {proc.info['pid']}...")
                        proc.terminate()
                        killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"\n✓ Terminated {killed} process(es)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--kill":
        kill_ana_processes()
    else:
        check_ana_processes()
        print(
            "\nTip: Run 'python check_resources.py --kill' to terminate all ANA processes"
        )
