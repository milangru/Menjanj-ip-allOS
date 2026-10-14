LAN IP MANAGER (WINDOWS, MACOS, LINUX)
=======================================

Graficka alatka u Pythonu (Tkinter) koja prebacuje zicnu (Ethernet)
konekciju izmedju automatske DHCP adrese i fiksne IP adrese. Radi na
Windows-u, macOS-u i Linuxu, a sistem prepoznaje sama.

Za korisnike koji koriste samo Linux postoji i laksa bash verzija:
https://github.com/milangru/ip_change


FUNKCIONALNOSTI
---------------
- Podrzava Windows (netsh), macOS (networksetup) i Linux (nmcli/ip)
- Tkinter interfejs, bez dodatnih GUI biblioteka
- Prebacivanje izmedju DHCP i fiksne IP adrese
- Podrazumevane vrednosti unapred popunjene u poljima za fiksnu IP
- Prikaz stvarne trenutne IP adrese i gateway-a, sa dugmetom "Osvezi"
- Restart mreznog interfejsa posle izmene
- Primena u pozadinskoj niti, pa se prozor ne zamrzava
- Izbor interfejsa iz liste ako ih ima vise
- Automatsko trazenje administratorskih prava: UAC prozor na
  Windows-u, pkexec na Linuxu


ZAHTEVI
-------
- Python 3. Na Windows-u preuzmite sa python.org i tokom instalacije
  cekirajte "Add python.exe to PATH".
- Tkinter. Na Windows-u i macOS-u dolazi uz Python. Na Linuxu:
    Debian/Ubuntu/Mint: sudo apt install python3-tk
    Fedora: sudo dnf install python3-tkinter
    Arch/Manjaro: sudo pacman -S tk
- Administratorske privilegije (skripta ih trazi sama, osim na macOS-u)


INSTALACIJA
-----------
    git clone https://github.com/milangru/Menjanj-ip-allOS.git
    cd Menjanj-ip-allOS


UPOTREBA
--------
Windows:
    python lan_ip_manager.py
Ako python nije prepoznat, probajte: py lan_ip_manager.py

Linux:
    python3 lan_ip_manager.py
Pokrenite je kao obican korisnik, bez sudo. Skripta sama trazi lozinku
preko pkexec.

macOS:
    sudo python3 lan_ip_manager.py


POKRETANJE DUPLIM KLIKOM
------------------------
- Windows: preimenujte fajl u lan_ip_manager.pyw (pokrece se bez crnog
  konzolnog prozora). Dupli klik otvara UAC prozor, potvrdite sa "Da".
  Ikonicu mozete promeniti preko precice: Properties, Change Icon.
- Linux: napravite .desktop precicu koja pokrece
  python3 /putanja/do/lan_ip_manager.py. Ako se posle unosa lozinke
  prozor ne otvori, pkexec ne prosledjuje graficki ekran; u tom slucaju
  pogledajte pomocnu skriptu opisanu u
  https://github.com/milangru/ip_change


PODESAVANJE PODRAZUMEVANIH VREDNOSTI
------------------------------------
Na vrhu lan_ip_manager.py:

    DEFAULT_IP = "192.168.1.10"
    DEFAULT_PREFIX = "24"      # /24 = maska 255.255.255.0
    DEFAULT_GATEWAY = ""       # prazno - bez gateway-a
    DEFAULT_DNS = ""           # prazno - bez DNS servera


POZNATA OGRANICENJA
-------------------
- Na Windows-u sa jezikom koji nije engleski, ocitavanje trenutne IP i
  gateway-a mozda nece raditi jer su netsh labele lokalizovane. Sama
  primena podesavanja radi.
- Na macOS-u networksetup -setmanual trazi gateway, pa fiksna IP sa
  praznim gateway-om verovatno nece proci.
- Podrzane su samo zicne konekcije, ne Wi-Fi.
- macOS verzija nije testirana na stvarnom sistemu.


LICENCA
-------
Slobodno za koriscenje i izmenu. Dodajte licencu po zelji (npr. MIT).
