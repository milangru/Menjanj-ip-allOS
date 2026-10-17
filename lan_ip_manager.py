#!/usr/bin/env python3
"""
LAN IP Manager - cross-platform (Windows / macOS / Linux)

Prebacivanje zicne (Ethernet) konekcije izmedju DHCP-a i fiksne IP adrese,
sa prikazom stvarnog trenutnog stanja i restartom mreznog interfejsa.

Menjanje mreznih podesavanja zahteva administratorske privilegije; skripta
ih trazi sama (UAC na Windows-u, pkexec na Linux-u). Na macOS-u pokrenuti
sa: sudo python3 lan_ip_manager.py
"""

import ipaddress
import os
import re
import shutil
import platform
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

OS_NAME = platform.system()  # "Windows", "Darwin" (macOS), "Linux"

# Podrazumevane vrednosti za fiksnu IP
DEFAULT_IP = "192.168.1.10"
DEFAULT_PREFIX = "24"      # /24 = maska 255.255.255.0
DEFAULT_GATEWAY = ""       # prazno - bez podrazumevanog prolaza
DEFAULT_DNS = ""           # prazno - bez DNS servera

FIXED = "Fiksna IP"
DHCP = "Automatski (DHCP)"


def elevate_if_needed():
    """
    Ako skripta nije pokrenuta sa administratorskim/root privilegijama,
    pokusava da se sama ponovo pokrene sa povisenim ovlascenjima:
      - Linux: preko pkexec (graficki prompt za lozinku)
      - Windows: preko UAC dijaloga (ShellExecute "runas")
      - macOS: obavesti korisnika da pokrene sa sudo (osdascript prompt nije pouzdan za GUI app)
    Ako podizanje ne uspe, nastavlja normalno (kasnije funkcije ce prijaviti gresku).
    """
    try:
        if OS_NAME == "Linux":
            if os.geteuid() != 0:
                pkexec_path = shutil.which("pkexec")
                if pkexec_path:
                    # pkexec radi iz /root i ne prosledjuje graficke promenljive, pa:
                    # 1) saljemo apsolutnu putanju skripte
                    # 2) eksplicitno prosledjujemo DISPLAY/XAUTHORITY/Wayland promenljive
                    script = os.path.abspath(sys.argv[0])
                    env_args = []
                    for var in ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
                        val = os.environ.get(var)
                        if val:
                            env_args.append(f"{var}={val}")
                    if "XAUTHORITY" not in os.environ:
                        default_xauth = os.path.expanduser("~/.Xauthority")
                        if os.path.exists(default_xauth):
                            env_args.append(f"XAUTHORITY={default_xauth}")
                    os.execvp(
                        pkexec_path,
                        [pkexec_path, "env"] + env_args
                        + [sys.executable, script] + sys.argv[1:],
                    )
                # ako pkexec ne postoji, nastavi bez elevacije (korisnik ce dobiti upozorenje u GUI-ju)
        elif OS_NAME == "Windows":
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                params = " ".join(f'"{a}"' for a in sys.argv)
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, params, None, 1
                )
                sys.exit(0)
        # macOS: automatsko podizanje GUI aplikacije preko sudo nije pouzdano,
        # korisnik se i dalje upozorava unutar GUI-ja ako nije root
    except Exception:
        pass  # tiho nastavi - upozorenje u GUI-ju ce pokriti slucaj


# ---------------------------------------------------------------------------
# Pomocne funkcije
# ---------------------------------------------------------------------------

def run(cmd, timeout=30):
    """Pokrece komandu; vraca (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if OS_NAME == "Windows" else 0,
        )
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception as e:
        return 1, "", str(e)


def powershell(script):
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout=60)


def is_admin():
    try:
        if OS_NAME == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return os.geteuid() == 0
    except Exception:
        return False


def cidr_to_netmask(prefix):
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)


def parse_dns(text):
    return [d for d in re.split(r"[,\s]+", text.strip()) if d]


# ---------------------------------------------------------------------------
# Backend-ovi: svaki ima interfaces(), current(iface), apply(...)
#   current(iface) -> (ip_cidr, gateway, mode)
#   apply(iface, mode, ip_cidr, gateway, dns_list) -> (ok, poruka)
# ---------------------------------------------------------------------------

class Linux:
    @staticmethod
    def interfaces():
        _, out, _ = run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"])
        devs = [l.rsplit(":", 1)[0] for l in out.splitlines() if l.endswith(":ethernet")]
        if not devs:
            _, out, _ = run(["ip", "-o", "link", "show"])
            for line in out.splitlines():
                m = re.match(r"\d+:\s+([^:@]+)", line)
                if m and m.group(1) != "lo":
                    devs.append(m.group(1))
        return devs

    @staticmethod
    def _conn(dev, create=False):
        """Ime NetworkManager profila za uredjaj (aktivan, bilo koji zicni, ili nov)."""
        _, out, _ = run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
        for line in out.splitlines():
            name, _, d = line.rpartition(":")
            if d == dev:
                return name
        _, out, _ = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
        for line in out.splitlines():
            name, _, t = line.rpartition(":")
            if t == "802-3-ethernet":
                return name
        if create:
            name = f"LAN {dev}"
            run(["nmcli", "connection", "add", "type", "ethernet", "ifname", dev, "con-name", name])
            return name
        return None

    @staticmethod
    def current(dev):
        _, out, _ = run(["nmcli", "-g", "IP4.ADDRESS", "device", "show", dev])
        ip = out.splitlines()[0] if out else ""
        _, out, _ = run(["nmcli", "-g", "IP4.GATEWAY", "device", "show", dev])
        gw = out.splitlines()[0] if out else ""
        mode = FIXED
        conn = Linux._conn(dev)
        if conn:
            _, method, _ = run(["nmcli", "-g", "ipv4.method", "connection", "show", conn])
            if method == "auto":
                mode = DHCP
        return ip, gw, mode

    @staticmethod
    def _wait_carrier(dev, seconds=15):
        for _ in range(seconds):
            try:
                with open(f"/sys/class/net/{dev}/carrier") as f:
                    if f.read().strip() == "1":
                        return True
            except OSError:
                pass
            time.sleep(1)
        return False

    @staticmethod
    def apply(dev, mode, ip_cidr, gateway, dns):
        conn = Linux._conn(dev, create=True)
        if mode == DHCP:
            args = ["ipv4.method", "auto", "ipv4.addresses", "", "ipv4.gateway", "", "ipv4.dns", ""]
        else:
            args = ["ipv4.method", "manual", "ipv4.addresses", ip_cidr,
                    "ipv4.gateway", gateway, "ipv4.dns", ",".join(dns)]
        rc, out, err = run(["nmcli", "connection", "modify", conn] + args)
        if rc != 0:
            return False, err or out
        # Restart porta (connection down umesto device disconnect, da se ne blokira autoconnect)
        run(["nmcli", "connection", "down", conn])
        time.sleep(1)
        run(["ip", "link", "set", dev, "down"])
        time.sleep(1)
        run(["ip", "link", "set", dev, "up"])
        if not Linux._wait_carrier(dev):
            run(["nmcli", "device", "set", dev, "autoconnect", "yes"])
            return False, ("Port nema signal. Proverite mrezni kabl.\n"
                           "Podesavanja su sacuvana i primenice se cim se pojavi signal.")
        rc, out, err = run(["nmcli", "connection", "up", conn, "ifname", dev], timeout=60)
        return rc == 0, err or out


class Windows:
    @staticmethod
    def _q(name):
        return name.replace("'", "''")

    @staticmethod
    def interfaces():
        _, out, _ = powershell(
            "Get-NetAdapter -Physical | Where-Object { $_.PhysicalMediaType -eq '802.3' } "
            "| ForEach-Object { $_.Name }")
        names = [l.strip() for l in out.splitlines() if l.strip()]
        if not names:
            _, out, _ = powershell("Get-NetAdapter -Physical | ForEach-Object { $_.Name }")
            names = [l.strip() for l in out.splitlines() if l.strip()]
        return names

    @staticmethod
    def current(iface):
        q = Windows._q(iface)
        script = (
            f"$a = Get-NetIPAddress -InterfaceAlias '{q}' -AddressFamily IPv4 "
            "-ErrorAction SilentlyContinue | Select-Object -First 1; "
            f"$g = Get-NetRoute -InterfaceAlias '{q}' -DestinationPrefix '0.0.0.0/0' "
            "-ErrorAction SilentlyContinue | Select-Object -First 1; "
            f"$d = (Get-NetIPInterface -InterfaceAlias '{q}' -AddressFamily IPv4 "
            "-ErrorAction SilentlyContinue).Dhcp; "
            "Write-Output ('{0}|{1}|{2}|{3}' -f $a.IPAddress, $a.PrefixLength, $g.NextHop, $d)"
        )
        rc, out, _ = powershell(script)
        parts = out.splitlines()[-1].split("|") if out else []
        if rc != 0 or len(parts) != 4:
            return "", "", FIXED
        ip, prefix, gw, dhcp = (p.strip() for p in parts)
        return (f"{ip}/{prefix}" if ip else ""), gw, (DHCP if dhcp.lower() == "enabled" else FIXED)

    @staticmethod
    def apply(iface, mode, ip_cidr, gateway, dns):
        name = f"name={iface}"
        if mode == DHCP:
            steps = [
                ["netsh", "interface", "ip", "set", "address", name, "source=dhcp"],
                ["netsh", "interface", "ip", "set", "dnsservers", name, "source=dhcp"],
            ]
        else:
            ip, prefix = ip_cidr.split("/")
            addr = ["netsh", "interface", "ip", "set", "address", name, "source=static",
                    f"address={ip}", f"mask={cidr_to_netmask(prefix)}"]
            if gateway:
                addr.append(f"gateway={gateway}")
            steps = [addr]
            if dns:
                steps.append(["netsh", "interface", "ip", "set", "dnsservers", name,
                              "source=static", f"address={dns[0]}", "validate=no"])
                for i, d in enumerate(dns[1:], start=2):
                    steps.append(["netsh", "interface", "ip", "add", "dnsservers", name,
                                  f"address={d}", f"index={i}", "validate=no"])
            else:
                steps.append(["netsh", "interface", "ip", "set", "dnsservers", name,
                              "source=static", "address=none"])
        for cmd in steps:
            rc, out, err = run(cmd)
            if rc != 0:
                return False, out or err or "netsh komanda nije uspela."
        rc, out, err = powershell(f"Restart-NetAdapter -Name '{Windows._q(iface)}' -Confirm:$false")
        if rc != 0:
            return False, out or err or "Restart adaptera nije uspeo."
        return True, ""


class MacOS:
    @staticmethod
    def interfaces():
        _, out, _ = run(["networksetup", "-listallnetworkservices"])
        services = [l.strip() for l in out.splitlines()[1:] if l.strip() and not l.startswith("*")]
        # zicni servisi prvi
        services.sort(key=lambda s: 0 if re.search(r"ethernet|lan|usb", s, re.I) else 1)
        return services

    @staticmethod
    def current(service):
        _, out, _ = run(["networksetup", "-getinfo", service])
        mode = DHCP if out.startswith("DHCP") else FIXED
        ip = re.search(r"^IP address:\s*([\d.]+)", out, re.M)
        mask = re.search(r"^Subnet mask:\s*([\d.]+)", out, re.M)
        gw = re.search(r"^Router:\s*([\d.]+)", out, re.M)
        ip_cidr = ""
        if ip:
            prefix = ipaddress.IPv4Network(f"0.0.0.0/{mask.group(1)}").prefixlen if mask else 24
            ip_cidr = f"{ip.group(1)}/{prefix}"
        return ip_cidr, (gw.group(1) if gw else ""), mode

    @staticmethod
    def apply(service, mode, ip_cidr, gateway, dns):
        if mode == DHCP:
            steps = [["networksetup", "-setdhcp", service],
                     ["networksetup", "-setdnsservers", service, "empty"]]
        else:
            ip, prefix = ip_cidr.split("/")
            # networksetup obavezno trazi router; ako gateway nije zadat, koristi se sopstvena IP
            steps = [["networksetup", "-setmanual", service, ip, cidr_to_netmask(prefix), gateway or ip],
                     ["networksetup", "-setdnsservers", service] + (dns or ["empty"])]
        for cmd in steps:
            rc, out, err = run(cmd)
            if rc != 0:
                return False, out or err or "networksetup komanda nije uspela."
        run(["networksetup", "-setnetworkserviceenabled", service, "off"])
        time.sleep(1)
        run(["networksetup", "-setnetworkserviceenabled", service, "on"])
        return True, ""


BACKEND = {"Windows": Windows, "Darwin": MacOS}.get(OS_NAME, Linux)


# ---------------------------------------------------------------------------
# Graficki interfejs (Tkinter)
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Upravljanje LAN IP adresom")
        self.resizable(False, False)
        self.configure(padx=16, pady=14)

        self.ifaces = BACKEND.interfaces()
        if not self.ifaces:
            messagebox.showerror("Greska", "Nije pronadjen nijedan zicni mrezni interfejs.\n"
                                 "Proverite da li je kabl prikljucen.")
            self.destroy()
            sys.exit(1)

        if not is_admin():
            messagebox.showwarning(
                "Potrebne su administratorske privilegije",
                "Aplikacija verovatno nece moci da primeni izmene.\n\n"
                + ("Pokrenite je kao Administrator." if OS_NAME == "Windows"
                   else "Pokrenite je sa: sudo python3 " + os.path.basename(__file__)))

        self._queue = queue.Queue()
        self._build()
        self._poll()
        self.refresh(reset_mode=True)

    # -- UI ----------------------------------------------------------------

    def _build(self):
        bold = tkfont.nametofont("TkDefaultFont").copy()
        bold.configure(weight="bold")
        big = bold.copy()
        big.configure(size=bold.cget("size") + 1)
        style = ttk.Style()
        style.configure("Cur.TLabel", foreground="#2e86de", font=big)

        ttk.Label(self, text="Mrezni interfejs:").grid(row=0, column=0, sticky="w")
        self.iface_var = tk.StringVar(value=self.ifaces[0])
        combo = ttk.Combobox(self, textvariable=self.iface_var, values=self.ifaces,
                             state="readonly", width=34)
        combo.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 8))
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh(reset_mode=True))

        self.mode_lbl = ttk.Label(self, text="Trenutni rezim: ...", font=bold)
        self.mode_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(self, text="Rezim rada:").grid(row=3, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=FIXED)
        ttk.Combobox(self, textvariable=self.mode_var, values=[FIXED, DHCP],
                     state="readonly", width=28).grid(row=3, column=1, sticky="we", pady=4)

        self.ip_var = tk.StringVar(value=f"{DEFAULT_IP}/{DEFAULT_PREFIX}")
        self.gw_var = tk.StringVar(value=DEFAULT_GATEWAY)
        self.dns_var = tk.StringVar(value=DEFAULT_DNS)
        for row, (text, var) in enumerate((
                ("IP adresa i prefiks (npr. 192.168.1.50/24):", self.ip_var),
                ("Gateway (Podrazumevani prolaz):", self.gw_var),
                ("DNS serveri (odvojeni zarezom):", self.dns_var)), start=4):
            ttk.Label(self, text=text).grid(row=row * 2 - 4, column=0, columnspan=2,
                                            sticky="w", pady=(8, 0))
            ttk.Entry(self, textvariable=var, width=38).grid(row=row * 2 - 3, column=0,
                                                              columnspan=2, sticky="we")

        ttk.Separator(self).grid(row=10, column=0, columnspan=2, sticky="we", pady=10)
        self.cur_ip_lbl = ttk.Label(self, text="Trenutna IP: ...", style="Cur.TLabel")
        self.cur_ip_lbl.grid(row=11, column=0, columnspan=2, sticky="w")
        self.cur_gw_lbl = ttk.Label(self, text="Gateway: ...", style="Cur.TLabel")
        self.cur_gw_lbl.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="#888888").grid(
            row=13, column=0, columnspan=2, sticky="w")

        buttons = ttk.Frame(self)
        buttons.grid(row=14, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Osvezi IP", command=self.refresh).pack(side="left", padx=4)
        self.apply_btn = ttk.Button(buttons, text="Primeni", command=self.on_apply)
        self.apply_btn.pack(side="left")

    # -- Komunikacija sa pozadinskim nitima ------------------------------------

    def _post(self, func, *args):
        """Poziva se iz pozadinske niti; func se izvrsava u glavnoj niti."""
        self._queue.put((func, args))

    def _poll(self):
        try:
            while True:
                func, args = self._queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # -- Logika ------------------------------------------------------------

    def refresh(self, reset_mode=False):
        """Ocitava stvarno stanje (u pozadini) i osvezava prikaz."""
        iface = self.iface_var.get()

        def work():
            data = BACKEND.current(iface)
            self._post(self._show_current, data, reset_mode)

        threading.Thread(target=work, daemon=True).start()

    def _show_current(self, data, reset_mode):
        ip, gw, mode = data
        self.cur_ip_lbl.config(text=f"Trenutna IP: {ip or 'nepoznato'}")
        self.cur_gw_lbl.config(text=f"Gateway: {gw or 'nepoznato'}")
        self.mode_lbl.config(text=f"Trenutni rezim: {mode}")
        if reset_mode:  # padajuca lista nudi suprotan rezim od trenutnog
            self.mode_var.set(DHCP if mode == FIXED else FIXED)

    def on_apply(self):
        iface, mode = self.iface_var.get(), self.mode_var.get()
        ip_cidr, gateway, dns = "", "", []
        if mode == FIXED:
            try:
                text = self.ip_var.get().strip() or f"{DEFAULT_IP}/{DEFAULT_PREFIX}"
                if "/" not in text:
                    text += f"/{DEFAULT_PREFIX}"
                iface_ip = ipaddress.IPv4Interface(text)
                ip_cidr = f"{iface_ip.ip}/{iface_ip.network.prefixlen}"
                gateway = self.gw_var.get().strip()
                if gateway:
                    ipaddress.IPv4Address(gateway)
                dns = parse_dns(self.dns_var.get())
                for d in dns:
                    ipaddress.IPv4Address(d)
            except ValueError as e:
                messagebox.showerror("Greska", f"Neispravan unos: {e}")
                return

        self.apply_btn.config(state="disabled")
        self.status_var.set("Primena u toku (restart porta), sacekajte...")
        threading.Thread(target=self._worker, args=(iface, mode, ip_cidr, gateway, dns),
                         daemon=True).start()

    def _worker(self, iface, mode, ip_cidr, gateway, dns):
        ok, msg = BACKEND.apply(iface, mode, ip_cidr, gateway, dns)
        expected = ip_cidr.split("/")[0] if mode == FIXED else None
        result = None
        if ok:  # sacekaj (do 12 s) da uredjaj stvarno dobije trazenu adresu
            for _ in range(12):
                ip, gw, _m = BACKEND.current(iface)
                if ip and (expected is None or ip.split("/")[0] == expected):
                    result = ip
                    break
                time.sleep(1)
        self._post(self._done, mode, ok, msg, result, expected)

    def _done(self, mode, ok, msg, result, expected):
        self.apply_btn.config(state="normal")
        self.status_var.set("")
        self.refresh(reset_mode=True)
        if not ok:
            messagebox.showerror("Greska", msg or "Primena nije uspela.")
        elif result:
            what = "Prebaceno na DHCP." if mode == DHCP else "Fiksna IP primenjena."
            messagebox.showinfo("Gotovo", f"{what}\nTrenutna IP: {result}")
        elif mode == DHCP:
            messagebox.showerror("Greska", "IP adresa nije dodeljena u roku od 12 s.\n"
                                 "Proverite kabl i DHCP server.")
        else:
            messagebox.showerror("Greska", f"IP adresa {expected} nije postavljena na interfejsu.")


if __name__ == "__main__":
    try:
        elevate_if_needed()
        App().mainloop()
    except Exception:
        import traceback
        messagebox.showerror("Neocekivana greska", traceback.format_exc())
