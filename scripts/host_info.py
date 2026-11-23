#!/usr/bin/env python3
"""
Dynamic Host System Detection Module for CLTML
Detects host CPU model, core/thread count, OS/kernel distribution,
and compiler specifications on whichever machine it runs.
"""

import os
import re
import platform
import subprocess

def get_cpu_info():
    model = "Generic x86_64 Processor"
    cores = os.cpu_count() or 1
    threads = os.cpu_count() or 1
    
    # Try /proc/cpuinfo
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    # Try lscpu for exact physical cores vs logical threads
    try:
        out = subprocess.check_output(["lscpu"], text=True)
        for line in out.splitlines():
            if line.startswith("Model name:"):
                model = line.split(":", 1)[1].strip()
            elif line.startswith("Core(s) per socket:"):
                cores = int(line.split(":", 1)[1].strip())
            elif line.startswith("CPU(s):") and "list" not in line:
                threads = int(line.split(":", 1)[1].strip())
    except Exception:
        pass

    # Clean display model: Intel(R) Core(TM) Ultra 7 255HX -> Intel Core Ultra 7 255HX
    clean_model = re.sub(r'\(R\)|\(TM\)', '', model)
    clean_model = re.sub(r'\s+', ' ', clean_model).strip()

    return {
        "raw_model": model,
        "clean_model": clean_model,
        "cores": cores,
        "threads": threads
    }

def get_os_info():
    uname = platform.uname()
    kernel_release = uname.release
    os_name = "Linux"
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
    return {
        "os_name": os_name,
        "kernel_release": kernel_release,
        "full_os": f"{os_name} (Kernel {kernel_release})"
    }

def get_compiler_info():
    compiler_line = "GCC"
    try:
        out = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
        compiler_line = out.strip()
    except Exception:
        pass
    
    m = re.search(r'(GCC|gcc|clang|LLVM)\s+([0-9\.]+)', compiler_line)
    short = m.group(0).upper() if m else "GCC"
    return {
        "full_line": compiler_line,
        "short": short
    }

def get_host_specs():
    cpu = get_cpu_info()
    os_info = get_os_info()
    comp = get_compiler_info()

    # Determine cache hierarchy via lscpu
    caches = {"l1d": "L1d: 320 KB", "l1i": "L1i: 384 KB", "l2": "L2: 7 MB", "l3": "L3: 12 MB shared"}
    try:
        out = subprocess.check_output(["lscpu"], text=True)
        l1d, l1i, l2, l3 = "", "", "", ""
        for line in out.splitlines():
            if line.startswith("L1d cache:"):
                l1d = line.split(":", 1)[1].strip()
            elif line.startswith("L1i cache:"):
                l1i = line.split(":", 1)[1].strip()
            elif line.startswith("L2 cache:"):
                l2 = line.split(":", 1)[1].strip()
            elif line.startswith("L3 cache:"):
                l3 = line.split(":", 1)[1].strip()
        parts = []
        if l1d: parts.append(f"L1d: {l1d.split('(')[0].strip()}")
        if l1i: parts.append(f"L1i: {l1i.split('(')[0].strip()}")
        if l2: parts.append(f"L2: {l2.split('(')[0].strip()}")
        if l3: parts.append(f"L3: {l3.split('(')[0].strip()} shared")
        if parts:
            caches_str = ", ".join(parts)
        else:
            caches_str = "L1d: 320 KB, L1i: 384 KB, L2: 7 MB, L3: 12 MB shared"
    except Exception:
        caches_str = "L1d: 320 KB, L1i: 384 KB, L2: 7 MB, L3: 12 MB shared"

    return {
        "cpu_raw": cpu["raw_model"],
        "cpu_clean": cpu["clean_model"],
        "cores": cpu["cores"],
        "threads": cpu["threads"],
        "os_name": os_info["os_name"],
        "kernel_release": os_info["kernel_release"],
        "full_os": os_info["full_os"],
        "compiler_short": comp["short"],
        "compiler_line": comp["full_line"],
        "caches_str": caches_str
    }

if __name__ == "__main__":
    import json
    print(json.dumps(get_host_specs(), indent=2))
