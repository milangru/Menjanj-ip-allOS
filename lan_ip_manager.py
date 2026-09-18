#!/usr/bin/env python3
"""
LAN IP Manager - cross-platform (Windows / macOS / Linux)

Graficka alatka za prebacivanje zicne (Ethernet) mrezne konekcije izmedju
automatske DHCP adrese i fiksne IP adrese, sa prikazom stvarnog trenutnog
stanja i restartom mreznog interfejsa posle svake izmene.

NAPOMENA: menjanje mreznih podesavanja zahteva administratorske
privilegije na sva tri sistema:
    - Windows: pokrenuti "Run as Administrator"
    - macOS / Linux: pokrenuti sa "sudo python3 lan_ip_manager.py"
"""

import os
import re
import sys
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

OS_NAME = platform.system()  # "Windows", "Darwin" (macOS), "Linux"

# Podrazumevane (default) vrednosti za fiksnu IP
DEFAULT_IP = "192.168.100.101"
DEFAULT_PREFIX = "24"
DEFAULT_GATEWAY = "192.168.100.100"
DEFAULT_DNS = "8.8.8.8, 1.1.1.1"


# ---------------------------------------------------------------------------
# Pomocne funkcije
# ---------------------------------------------------------------------------

def run(cmd):
    """Pokrece komandu (lista argumenata) i vraca (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if OS_NAME == "Windows" else 0,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def is_admin():
    try:
        if OS_NAME == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return os.geteuid() == 0
    except Exception:
        return False


def cidr_to_netmask(prefix):
    prefix = int(prefix)
    bits = ("1" * prefix) + ("0" * (32 - prefix))
    return ".".join(str(int(bits[i:i + 8], 2)) for i in range(0, 32, 8))


def netmask_to_prefix(mask):
    try:
        return str(sum(bin(int(x)).count("1") for x in mask.split(".")))
    except Exception:
        return "24"


def parse_dns(dns_text):
    return [d.strip() for d in dns_text.split(",") if d.strip()]


# ---------------------------------------------------------------------------
# LINUX (nmcli / ip)
# ---------------------------------------------------------------------------

def linux_list_interfaces():
    rc, out, _ = run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"])
    ifaces = []
    if rc == 0:
        for line in out.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == "ethernet":
                ifaces.append(parts[0])
    if not ifaces:
        rc, out, _ = run(["ip", "-o", "link", "show"])
        for line in out.splitlines():
            m = re.match(r"\d+:\s+([^:@]+)[:@]", line)
            if m and m.group(1) != "lo":
                ifaces.append(m.group(1))
    return ifaces


def linux_conn_name_for_device(dev):
    for args in (["connection", "show", "--active"], ["connection", "show"]):
        rc, out, _ = run(["nmcli", "-t", "-f", "NAME,DEVICE"] + args)
        for line in out.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == dev:
                return parts[0]
    return dev


def linux_get_current(dev):
    ip_addr, gw = "", ""
    rc, out, _ = run(["nmcli", "-g", "IP4.ADDRESS", "device", "show", dev])
    if rc == 0 and out.strip():
        ip_addr = out.strip().splitlines()[0]
    rc, out, _ = run(["nmcli", "-g", "IP4.GATEWAY", "device", "show", dev])
    if rc == 0 and out.strip():
        gw = out.strip().splitlines()[0]
    return ip_addr, gw


def linux_restart(dev):
    run(["nmcli", "device", "disconnect", dev])
    run(["ip", "link", "set", dev, "down"])
    run(["ip", "link", "set", dev, "up"])
    run(["nmcli", "device", "connect", dev])


def linux_apply(dev, mode, ip_cidr, gateway, dns_csv):
    conn = linux_conn_name_for_device(dev)
    if mode == "dhcp":
        run(["nmcli", "connection", "modify", conn, "ipv4.method", "auto",
             "ipv4.addresses", "", "ipv4.gateway", "", "ipv4.dns", ""])
    else:
        run(["nmcli", "connection", "modify", conn, "ipv4.method", "manual",
             "ipv4.addresses", ip_cidr])
        run(["nmcli", "connection", "modify", conn, "ipv4.gateway", gateway or ""])
        run(["nmcli", "connection", "modify", conn, "ipv4.dns", dns_csv or ""])
    linux_restart(dev)
    return run(["nmcli", "connection", "up", conn])


# ---------------------------------------------------------------------------
# WINDOWS (netsh)
# ---------------------------------------------------------------------------

def windows_list_interfaces():
    rc, out, _ = run(["netsh", "interface", "show", "interface"])
    ifaces = []
    if rc == 0:
        lines = out.strip().splitlines()
        for line in lines[3:]:
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[2].lower() == "dedicated":
                ifaces.append(parts[3])
    return ifaces


def windows_get_current(iface):
    ip_addr, gw = "", ""
    rc, out, _ = run(["netsh", "interface", "ip", "show", "config", f"name={iface}"])
    if rc == 0:
        m = re.search(r"IP Address:\s*([\d.]+)", out)
        if m:
            ip_addr = m.group(1)
        m2 = re.search(r"Default Gateway:\s*([\d.]+)", out)
        if m2:
            gw = m2.group(1)
    return ip_addr, gw


def windows_restart(iface):
    run(["netsh", "interface", "set", "interface", f"name={iface}", "admin=disable"])
    run(["netsh", "interface", "set", "interface", f"name={iface}", "admin=enable"])


def windows_apply(iface, mode, ip_cidr, gateway, dns_list):
    if mode == "dhcp":
        run(["netsh", "interface", "ip", "set", "address", f"name={iface}", "dhcp"])
        run(["netsh", "interface", "ip", "set", "dns", f"name={iface}", "dhcp"])
    else:
        ip_only, prefix = ip_cidr.split("/")
        mask = cidr_to_netmask(prefix)
        run(["netsh", "interface", "ip", "set", "address", f"name={iface}",
             "static", ip_only, mask, gateway or "none"])
        if dns_list:
            run(["netsh", "interface", "ip", "set", "dns", f"name={iface}",
                 "static", dns_list[0]])
            for i, d in enumerate(dns_list[1:], start=2):
                run(["netsh", "interface", "ip", "add", "dns", f"name={iface}",
                     d, f"index={i}"])
    windows_restart(iface)
    return 0, "", ""


# ---------------------------------------------------------------------------
# macOS (networksetup)
# ---------------------------------------------------------------------------

def macos_list_interfaces():
    rc, out, _ = run(["networksetup", "-listallnetworkservices"])
    services = []
    if rc == 0:
        for line in out.strip().splitlines()[1:]:
            if not line.startswith("*"):
                services.append(line.strip())
    return services


def macos_device_for_service(service):
    rc, out, _ = run(["networksetup", "-listallhardwareports"])
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Hardware Port:") and service in line:
            for j in range(i, min(i + 3, len(lines))):
                if lines[j].startswith("Device:"):
                    return lines[j].split(":", 1)[1].strip()
    return ""


def macos_get_current(service):
    ip_addr, gw = "", ""
    dev = macos_device_for_service(service)
    if dev:
        rc, out, _ = run(["ipconfig", "getifaddr", dev])
        if rc == 0:
            ip_addr = out.strip()
    rc, out, _ = run(["netstat", "-nr", "-f", "inet"])
    for line in out.splitlines():
        if line.startswith("default"):
            parts = line.split()
            if len(parts) > 1:
                gw = parts[1]
            break
    return ip_addr, gw


def macos_restart(service):
    run(["networksetup", "-setnetworkserviceenabled", service, "off"])
    run(["networksetup", "-setnetworkserviceenabled", service, "on"])


def macos_apply(service, mode, ip_cidr, gateway, dns_list):
    if mode == "dhcp":
        run(["networksetup", "-setdhcp", service])
        run(["networksetup", "-setdnsservers", service, "empty"])
    else:
        ip_only, prefix = ip_cidr.split("/")
        mask = cidr_to_netmask(prefix)
        run(["networksetup", "-setmanual", service, ip_only, mask, gateway or ""])
        if dns_list:
            run(["networksetup", "-setdnsservers", service] + dns_list)
    macos_restart(service)
    return 0, "", ""


# ---------------------------------------------------------------------------
# Dispatcher - bira pravu funkciju prema OS-u
# ---------------------------------------------------------------------------

def list_interfaces():
    if OS_NAME == "Windows":
        return windows_list_interfaces()
    if OS_NAME == "Darwin":
        return macos_list_interfaces()
    return linux_list_interfaces()


def get_current(iface):
    if OS_NAME == "Windows":
        return windows_get_current(iface)
    if OS_NAME == "Darwin":
        return macos_get_current(iface)
    return linux_get_current(iface)


def apply_settings(iface, mode, ip_cidr, gateway, dns_text):
    dns_list = parse_dns(dns_text)
    if OS_NAME == "Windows":
        return windows_apply(iface, mode, ip_cidr, gateway, dns_list)
    if OS_NAME == "Darwin":
        return macos_apply(iface, mode, ip_cidr, gateway, dns_list)
    return linux_apply(iface, mode, ip_cidr, gateway, ", ".join(dns_list))


# ---------------------------------------------------------------------------
# Graficki interfejs (Tkinter)
# ---------------------------------------------------------------------------

class LanIpManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Upravljanje LAN IP adresom")
        self.resizable(False, False)
        self.configure(padx=16, pady=14)

        self.interfaces = list_interfaces()
        if not self.interfaces:
            messagebox.showerror(
                "Greška",
                "Nije pronađen nijedan mrežni interfejs.\n"
                "Proverite da li je kabl priključen i da li imate\n"
                "administratorske privilegije."
            )
            self.destroy()
            sys.exit(1)

        if not is_admin():
            messagebox.showwarning(
                "Potrebne su administratorske privilegije",
                "Aplikacija verovatno neće moći da primeni izmene.\n\n"
                + ("Pokrenite je kao Administrator." if OS_NAME == "Windows"
                   else "Pokrenite je sa: sudo python3 " + os.path.basename(__file__))
            )

        self._build_widgets()
        self._refresh_current(initial=True)

    # -- UI izgradnja -----------------------------------------------------

    def _build_widgets(self):
        header = ttk.Label(
            self, text=f"Mrežni interfejs ({OS_NAME}):", font=("Segoe UI", 10, "bold")
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.iface_var = tk.StringVar(value=self.interfaces[0])
        iface_combo = ttk.Combobox(
            self, textvariable=self.iface_var, values=self.interfaces,
            state="readonly", width=32
        )
        iface_combo.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        iface_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_current())

        ttk.Label(self, text="Režim rada:").grid(row=2, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="Fiksna IP")
        mode_combo = ttk.Combobox(
            self, textvariable=self.mode_var,
            values=["Fiksna IP", "Automatski (DHCP)"],
            state="readonly", width=28
        )
        mode_combo.grid(row=2, column=1, sticky="we", pady=4)

        ttk.Label(self, text="IP adresa i prefiks (npr. 192.168.1.50/24):").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.ip_var = tk.StringVar(value=f"{DEFAULT_IP}/{DEFAULT_PREFIX}")
        ttk.Entry(self, textvariable=self.ip_var, width=34).grid(
            row=4, column=0, columnspan=2, sticky="we", pady=(0, 6)
        )

        ttk.Label(self, text="Gateway (Podrazumevani prolaz):").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )
        self.gw_var = tk.StringVar(value=DEFAULT_GATEWAY)
        ttk.Entry(self, textvariable=self.gw_var, width=34).grid(
            row=6, column=0, columnspan=2, sticky="we", pady=(0, 6)
        )

        ttk.Label(self, text="DNS serveri (odvojeni zarezom):").grid(
            row=7, column=0, columnspan=2, sticky="w"
        )
        self.dns_var = tk.StringVar(value=DEFAULT_DNS)
        ttk.Entry(self, textvariable=self.dns_var, width=34).grid(
            row=8, column=0, columnspan=2, sticky="we", pady=(0, 10)
        )

        ttk.Separator(self).grid(row=9, column=0, columnspan=2, sticky="we", pady=6)

        self.current_ip_lbl = ttk.Label(self, text="🔌 Trenutna IP: ...", foreground="#2e86de")
        self.current_ip_lbl.grid(row=10, column=0, columnspan=2, sticky="w")
        self.current_gw_lbl = ttk.Label(self, text="🌐 Gateway: ...", foreground="#2e86de")
        self.current_gw_lbl.grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.status_lbl = ttk.Label(self, text="", foreground="#888888")
        self.status_lbl.grid(row=12, column=0, columnspan=2, sticky="w")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=13, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(btn_frame, text="Osveži", command=self._refresh_current).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Primeni", command=self._on_apply).pack(side="left")

    # -- Logika -------------------------------------------------------------

    def _refresh_current(self, initial=False):
        iface = self.iface_var.get()
        ip_addr, gw = get_current(iface)
        self.current_ip_lbl.config(text=f"🔌 Trenutna IP: {ip_addr or 'nepoznato'}")
        self.current_gw_lbl.config(text=f"🌐 Gateway: {gw or 'nepoznato'}")

    def _on_apply(self):
        iface = self.iface_var.get()
        mode = "dhcp" if self.mode_var.get() == "Automatski (DHCP)" else "fixed"
        ip_cidr = self.ip_var.get().strip() or f"{DEFAULT_IP}/{DEFAULT_PREFIX}"
        gateway = self.gw_var.get().strip() or DEFAULT_GATEWAY
        dns_text = self.dns_var.get().strip() or DEFAULT_DNS

        if mode == "fixed" and "/" not in ip_cidr:
            messagebox.showerror("Greška", "Unesite IP adresu sa prefiksom, npr. 192.168.1.50/24")
            return

        self.status_lbl.config(text="Primena podešavanja u toku, restart porta...")
        self.update_idletasks()

        def worker():
            apply_settings(iface, mode, ip_cidr, gateway, dns_text)
            self.after(0, self._after_apply, mode)

        threading.Thread(target=worker, daemon=True).start()

    def _after_apply(self, mode):
        self.status_lbl.config(text="")
        self._refresh_current()
        if mode == "dhcp":
            messagebox.showinfo(
                "Gotovo",
                f"Interfejs prebačen na automatsku (DHCP) IP adresu.\n"
                f"Dobijena IP: {self.current_ip_lbl.cget('text').replace('🔌 Trenutna IP: ', '')}"
            )
        else:
            messagebox.showinfo("Gotovo", f"Fiksna IP primenjena:\n{self.ip_var.get()}")


if __name__ == "__main__":
    app = LanIpManagerApp()
    app.mainloop()
