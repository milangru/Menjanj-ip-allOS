# LAN IP Manager (Windows, macOS, Linux)

Grafička alatka u Pythonu (Tkinter) koja prebacuje žičnu (Ethernet) konekciju između **automatske DHCP** adrese i **fiksne IP** adrese. Radi na **Windows-u, macOS-u i Linuxu**, a sistem prepoznaje sama.

> Za korisnike koji koriste samo Linux postoji i lakša bash verzija: [ip_change](https://github.com/milangru/ip_change).

## Funkcionalnosti

- Podržava **Windows** (`netsh`), **macOS** (`networksetup`) i **Linux** (`nmcli`/`ip`)
- Tkinter interfejs, bez dodatnih GUI biblioteka
- Prebacivanje između **DHCP** i **fiksne IP** adrese
- Podrazumevane vrednosti unapred popunjene u poljima za fiksnu IP
- Prikaz **stvarne trenutne IP adrese i gateway-a**, sa dugmetom "Osveži"
- Restart mrežnog interfejsa posle izmene
- Primena u pozadinskoj niti, pa se prozor ne zamrzava
- Izbor interfejsa iz liste ako ih ima više
- **Automatsko traženje administratorskih prava**: UAC prozor na Windows-u, `pkexec` na Linuxu

## Zahtevi

- **Python 3**. Na Windows-u preuzmite sa [python.org](https://www.python.org/downloads/) i tokom instalacije čekirajte "Add python.exe to PATH".
- **Tkinter**. Na Windows-u i macOS-u dolazi uz Python. Na Linuxu:
  - Debian/Ubuntu/Mint: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - Arch/Manjaro: `sudo pacman -S tk`
- Administratorske privilegije (skripta ih traži sama, osim na macOS-u)

## Instalacija

```bash
git clone https://github.com/milangru/Menjanj-ip-allOS.git
cd Menjanj-ip-allOS
```

## Upotreba

**Windows:**
```
python lan_ip_manager.py
```
Ako `python` nije prepoznat, probajte `py lan_ip_manager.py`.

**Linux:**
```bash
python3 lan_ip_manager.py
```
Pokrenite je kao običan korisnik, bez `sudo`. Skripta sama traži lozinku preko `pkexec`.

**macOS:**
```bash
sudo python3 lan_ip_manager.py
```

### Pokretanje duplim klikom

- **Windows:** preimenujte fajl u `lan_ip_manager.pyw` (pokreće se bez crnog konzolnog prozora). Dupli klik otvara UAC prozor, potvrdite sa "Da". Ikonicu možete promeniti preko prečice: Properties, zatim Change Icon.
- **Linux:** napravite `.desktop` prečicu koja pokreće `python3 /putanja/do/lan_ip_manager.py`. Ako se posle unosa lozinke prozor ne otvori, `pkexec` ne prosleđuje grafički ekran; u tom slučaju pogledajte pomoćnu skriptu opisanu u [ip_change](https://github.com/milangru/ip_change).

## Podešavanje podrazumevanih vrednosti

Na vrhu `lan_ip_manager.py`:

```python
DEFAULT_IP = "192.168.1.10"
DEFAULT_PREFIX = "24"      # /24 = maska 255.255.255.0
DEFAULT_GATEWAY = ""       # prazno - bez gateway-a
DEFAULT_DNS = ""           # prazno - bez DNS servera
```

## Poznata ograničenja

- Na Windows-u sa jezikom koji nije engleski, očitavanje trenutne IP i gateway-a možda neće raditi jer su `netsh` labele lokalizovane. Sama primena podešavanja radi.
- Na macOS-u `networksetup -setmanual` traži gateway, pa fiksna IP sa praznim gateway-om verovatno neće proći.
- Podržane su samo žične konekcije, ne Wi-Fi.
- macOS verzija nije testirana na stvarnom sistemu.

## Licenca

Slobodno za korišćenje i izmenu. Dodajte licencu po želji (npr. MIT).
